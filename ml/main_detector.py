import cv2
import pickle
import numpy as np
import argparse
import time
import os
from datetime import datetime

from detector_utils import (
    best_roi_for_bbox as _best_roi_for_bbox,
    bbox_anchor_points,
    bbox_center,
    bbox_iou,
    calculate_side,
    dedup_boxes_by_iou,
    is_point_in_roi as _is_point_in_roi,
)

from backend_client import create_session, post_table_occupancy
from smoothing import TableCountSmoother


# СВЯЗЬ ML И БЕКЕНДА: URL ДЛЯ ОТПРАВКИ ДАННЫХ
"""главный модуль мл детектора"""

TABLE_CAPACITY = 3
LOG_INTERVAL = 2.0
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
BACKEND_UPDATE_URL = os.getenv("BACKEND_UPDATE_URL", f"{BACKEND_BASE_URL}/api/tables/update")

# настройки йоло из окружения
YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")
YOLO_CONF = float(os.getenv("YOLO_CONF", "0.25"))
YOLO_IMGSZ = int(os.getenv("YOLO_IMGSZ", "960"))

# фильтры ошибок внутри рои
ROI_MIN_CONF = float(os.getenv("ROI_MIN_CONF", "0.35"))
DEDUP_IOU_THRESHOLD = float(os.getenv("DEDUP_IOU_THRESHOLD", "0.60"))
MIN_BBOX_AREA_RATIO = float(os.getenv("MIN_BBOX_AREA_RATIO", "0.0008"))

# сглаживание счетчика по кадрам
SMOOTH_WINDOW = max(1, int(os.getenv("SMOOTH_WINDOW", "5")))
CHANGE_CONFIRM_FRAMES = max(1, int(os.getenv("CHANGE_CONFIRM_FRAMES", "2")))

# пропуск кадров для скорости
PROCESS_EVERY_N_FRAMES = max(1, int(os.getenv("PROCESS_EVERY_N_FRAMES", "1")))

# очистка консоли при выводе
CLEAR_CONSOLE = os.getenv("CLEAR_CONSOLE", "1") in ("1", "true", "True", "yes", "YES")

# удержание статуса при пропусках
OCCUPANCY_HOLD_SECONDS = float(os.getenv("OCCUPANCY_HOLD_SECONDS", "6.0"))

# запас для попадания рои
ROI_MARGIN_PX = float(os.getenv("ROI_MARGIN_PX", "6"))

# удержание трек привязки стола
TRACK_TABLE_TTL_SECONDS = float(os.getenv("TRACK_TABLE_TTL_SECONDS", "2.0"))

_session = create_session()

def is_point_in_roi(roi, point):
    return _is_point_in_roi(roi, point, ROI_MARGIN_PX)

def is_bbox_in_roi(roi, box):
    for p in bbox_anchor_points(box):
        if is_point_in_roi(roi, p):
            return True
    return False


def best_roi_for_bbox(rois, box):
    return _best_roi_for_bbox(rois, box, ROI_MARGIN_PX)


def main(video_path: str):
    # ленивая загрузка для тестов
    from ultralytics import YOLO

    video_source = int(video_path) if video_path.isdigit() else video_path

    try:
        with open("tables.pkl", "rb") as f:
            rois = pickle.load(f)
        with open("entry_lines.pkl", "rb") as f:
            entry_data = pickle.load(f)
            entry_line = entry_data["line"]
            inside_ref_point = entry_data["inside_ref"]
    except FileNotFoundError:
        print("ОШИБКА: файлы pkl не найдены сначала конфигураторы!")
        return 1

    ref_value = calculate_side(entry_line, inside_ref_point)
    INSIDE_SIGN = 1 if ref_value > 0 else -1

    model = YOLO(YOLO_MODEL)
    cap = cv2.VideoCapture(video_source)

    tracks = {}
    track_table = {}
    smoother = None
    inside_total = 0
    last_log_time = time.time()
    frame_idx = 0

    print("Запуск системы...")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Поток завершен.")
                break

            output = frame.copy()

            do_infer = (frame_idx % PROCESS_EVERY_N_FRAMES) == 0
            frame_idx += 1

            results = None
            if do_infer:
                results = model.track(
                    frame,
                    conf=YOLO_CONF,
                    imgsz=YOLO_IMGSZ,
                    persist=True,
                    classes=[0],
                    verbose=False,
                )

            if smoother is None:
                smoother = TableCountSmoother(
                    n_tables=len(rois),
                    smooth_window=SMOOTH_WINDOW,
                    change_confirm_frames=CHANGE_CONFIRM_FRAMES,
                    hold_seconds=OCCUPANCY_HOLD_SECONDS,
                )

            detected_tables_status = [0] * len(rois)

            # боксы и скор по рои
            per_table_boxes = [[] for _ in range(len(rois))]
            per_table_scores = [[] for _ in range(len(rois))]

            # иды могут отсутствовать иногда
            # считаем занятость без идов
            ids = None
            boxes = None
            confs = None
            if results and getattr(results[0], "boxes", None) is not None:
                if results[0].boxes.xyxy is not None:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                if results[0].boxes.id is not None:
                    ids = results[0].boxes.id.cpu().numpy()
                if getattr(results[0].boxes, "conf", None) is not None:
                    confs = results[0].boxes.conf.cpu().numpy()

            frame_area = float(frame.shape[0] * frame.shape[1]) if frame is not None else 0.0

            if boxes is not None:
                for i, box in enumerate(boxes):
                    score = float(confs[i]) if confs is not None else 1.0
                    # фильтруем ложные боксы тут
                    if score < ROI_MIN_CONF:
                        continue
                    x1, y1, x2, y2 = [float(v) for v in box]
                    area = max(0.0, x2 - x1) * max(0.0, y2 - y1)
                    if frame_area > 0 and area < (MIN_BBOX_AREA_RATIO * frame_area):
                        continue

                    cx, cy = bbox_center(box)

                    now_ts = time.time()

                    pid = None
                    if ids is not None:
                        pid = int(ids[i])

                    # счетчик входа по идам
                    if pid is not None:
                        current_side_val = calculate_side(entry_line, (cx, cy))
                        current_sign = 1 if (current_side_val * INSIDE_SIGN) > 0 else -1

                        if pid not in tracks:
                            tracks[pid] = {
                                "last_sign": current_sign,
                                "counted": False,
                            }

                        last_sign = tracks[pid]["last_sign"]
                        if current_sign != last_sign:
                            if current_sign == 1:
                                inside_total += 1
                            else:
                                inside_total -= 1
                            tracks[pid]["last_sign"] = current_sign

                        if inside_total < 0:
                            inside_total = 0

                    # назначаем бокс в рои
                    is_sitting = False
                    matched_table = best_roi_for_bbox(rois, box)

                    if matched_table is None and pid is not None:
                        # удерживаем рои для трека
                        prev = track_table.get(pid)
                        if prev is not None and (now_ts - prev["ts"]) <= TRACK_TABLE_TTL_SECONDS:
                            matched_table = int(prev["table_idx"])

                    if matched_table is not None:
                        # дедуп внутри одного стола
                        per_table_boxes[int(matched_table)].append(box)
                        per_table_scores[int(matched_table)].append(score)
                        is_sitting = True
                        if pid is not None:
                            track_table[pid] = {"table_idx": int(matched_table), "ts": now_ts}

                        cv2.rectangle(
                            output,
                            (int(box[0]), int(box[1])),
                            (int(box[2]), int(box[3])),
                            (0, 0, 255),
                            2,
                        )
                        cv2.circle(output, (cx, cy), 4, (0, 0, 255), -1)

                    if not is_sitting:
                        cv2.rectangle(
                            output,
                            (int(box[0]), int(box[1])),
                            (int(box[2]), int(box[3])),
                            (0, 255, 0),
                            2,
                        )

            # считаем людей после дедупа
            inferred_counts = None
            if do_infer:
                inferred_counts = [0] * len(rois)
                for t_idx in range(len(rois)):
                    if not per_table_boxes[t_idx]:
                        continue
                    keep = dedup_boxes_by_iou(
                        per_table_boxes[t_idx],
                        per_table_scores[t_idx],
                        iou_threshold=DEDUP_IOU_THRESHOLD,
                    )
                    inferred_counts[t_idx] = int(len(keep))

            cv2.line(output, entry_line[0], entry_line[1], (255, 0, 0), 3)
            mid_x = int((entry_line[0][0] + entry_line[1][0]) / 2)
            mid_y = int((entry_line[0][1] + entry_line[1][1]) / 2)
            cv2.putText(
                output,
                "ENTRY LINE",
                (entry_line[0][0], entry_line[0][1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 0, 0),
                2,
            )

            # сглаживаем счетчики по кадрам
            now_ts = time.time()
            if smoother is not None:
                smoother.update(inferred_counts, now_ts)
                tables_status = smoother.current(now_ts)
            else:
                tables_status = [0] * len(rois)

            for idx, roi in enumerate(rois):
                count = tables_status[idx]
                color = (0, 255, 0) if count < TABLE_CAPACITY else (0, 0, 255)

                cv2.polylines(output, [roi], True, color, 2)

                M = cv2.moments(roi)
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    label = f"T{idx+1}: {count}/{TABLE_CAPACITY}"
                    cv2.putText(
                        output,
                        label,
                        (cX - 30, cY),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2,
                    )

            total_seated = int(sum(tables_status))
            total_free = max(0, (len(rois) * TABLE_CAPACITY) - total_seated)

            # счетчик линии может ошибаться
            # итог берем по столам
            cv2.rectangle(output, (0, 0), (360, 90), (0, 0, 0), -1)
            cv2.putText(
                output,
                f"TOTAL INSIDE (tables): {total_seated}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                output,
                f"CROSSINGS (debug): {inside_total}",
                (10, 58),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 200, 200),
                1,
            )
            cv2.putText(
                output,
                f"FREE: {total_free}",
                (10, 82),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (200, 200, 200),
                1,
            )


            if time.time() - last_log_time > LOG_INTERVAL:
                # СВЯЗЬ ML И БЕКЕНДА: HTTP POST
                post_table_occupancy(_session, BACKEND_UPDATE_URL, tables_status, timeout_seconds=0.5, debug=True)

                if CLEAR_CONSOLE:
                    os.system('cls' if os.name == 'nt' else 'clear')

                t_now = datetime.now().strftime("%H:%M:%S")
                print(f"--- ОТЧЕТ {t_now} ---")
                print(f"Посетителей (по столам): {total_seated}")
                print(f"Посетителей (по линии входа, debug): {inside_total}")
                print("-" * 35)
                print(f"{'Стол':<6} | {'Занято':<8} | {'Свободно':<8}")
                print("-" * 35)

                for idx, count in enumerate(tables_status):
                    free = max(0, TABLE_CAPACITY - count)
                    status_str = f"{count}" if count <= TABLE_CAPACITY else f"{count} (!)"
                    print(f"#{idx+1:<5} | {status_str:<8} | {free:<8}")

                print("-" * 35)
                last_log_time = time.time()

            cv2.imshow("Monitor", output)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        print("\nStopping ML (Ctrl+C).")

    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("video_path")
    args = parser.parse_args()
    raise SystemExit(main(args.video_path))