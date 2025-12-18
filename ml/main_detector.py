import cv2
import pickle
import numpy as np
from ultralytics import YOLO
import argparse
import time
import os
from datetime import datetime

TABLE_CAPACITY = 3      
LOG_INTERVAL = 2.0       

def calculate_side(line, point):
    """
    Вычисляет положение точки относительно линии.
    Результат > 0 с одной стороны, < 0 с другой.
    """
    (x1, y1), (x2, y2) = line
    px, py = point
    return (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)

def bbox_center(box):
    x1, y1, x2, y2 = map(int, box)
    return int((x1 + x2) / 2), int((y1 + y2) / 2)

def is_point_in_roi(roi, point):
    return cv2.pointPolygonTest(roi, point, False) >= 0

parser = argparse.ArgumentParser()
parser.add_argument("video_path")
args = parser.parse_args()

video_source = int(args.video_path) if args.video_path.isdigit() else args.video_path

try:
    with open("tables.pkl", "rb") as f:
        rois = pickle.load(f)
    with open("entry_lines.pkl", "rb") as f:
        entry_data = pickle.load(f)
        entry_line = entry_data["line"]       # [(x1,y1), (x2,y2)]
        inside_ref_point = entry_data["inside_ref"]
except FileNotFoundError:
    print("ОШИБКА: Файлы pkl не найдены. Сначала запусти конфигураторы!")
    exit()

ref_value = calculate_side(entry_line, inside_ref_point)
INSIDE_SIGN = 1 if ref_value > 0 else -1

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(video_source)

tracks = {}     # {id: {"last_side": int, "inside_room": bool}}
inside_total = 0
last_log_time = time.time()

print("Запуск системы...")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Поток завершен.")
        break

    output = frame.copy()

    results = model.track(frame, conf=0.5, persist=True, classes=[0], verbose=False)

    tables_status = [0] * len(rois) 
    
    if results and results[0].boxes.id is not None:
        ids = results[0].boxes.id.cpu().numpy()
        boxes = results[0].boxes.xyxy.cpu().numpy()

        for i, pid in enumerate(ids):
            box = boxes[i]
            cx, cy = bbox_center(box)

            current_side_val = calculate_side(entry_line, (cx, cy))
            current_sign = 1 if (current_side_val * INSIDE_SIGN) > 0 else -1
            
            if pid not in tracks:
                tracks[pid] = {
                    "last_sign": current_sign,
                    "counted": False 
                }
            
            last_sign = tracks[pid]["last_sign"]

            if current_sign != last_sign:
                if current_sign == 1: 
                    inside_total += 1
                else:                 
                    inside_total -= 1
                
                tracks[pid]["last_sign"] = current_sign

            if inside_total < 0: inside_total = 0

            is_sitting = False
            for t_idx, roi in enumerate(rois):
                if is_point_in_roi(roi, (cx, cy)):
                    tables_status[t_idx] += 1
                    is_sitting = True

                    cv2.rectangle(output, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 0, 255), 2)
                    cv2.circle(output, (cx, cy), 4, (0, 0, 255), -1)
                    break
            
            if not is_sitting:
                # Визуал: Зеленый бокс (ходит)
                cv2.rectangle(output, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), (0, 255, 0), 2)

    cv2.line(output, entry_line[0], entry_line[1], (255, 0, 0), 3) # Синяя
    mid_x = int((entry_line[0][0] + entry_line[1][0]) / 2)
    mid_y = int((entry_line[0][1] + entry_line[1][1]) / 2)
    cv2.putText(output, "ENTRY LINE", (entry_line[0][0], entry_line[0][1] - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    for idx, roi in enumerate(rois):
        count = tables_status[idx]
        # Зеленый полигон, если есть места, Красный если нет
        color = (0, 255, 0) if count < TABLE_CAPACITY else (0, 0, 255)
        
        cv2.polylines(output, [roi], True, color, 2)

        M = cv2.moments(roi)
        if M["m00"] != 0:
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            # Текст: T1 (2/3)
            label = f"T{idx+1}: {count}/{TABLE_CAPACITY}"
            cv2.putText(output, label, (cX - 30, cY), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    cv2.rectangle(output, (0, 0), (300, 80), (0, 0, 0), -1)
    cv2.putText(output, f"TOTAL INSIDE: {inside_total}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    total_seated = sum(tables_status)
    cv2.putText(output, f"SEATED: {total_seated} | FREE: {max(0, (len(rois)*TABLE_CAPACITY) - total_seated)}", (10, 60), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)


    if time.time() - last_log_time > LOG_INTERVAL:
        os.system('cls' if os.name == 'nt' else 'clear')
        
        t_now = datetime.now().strftime("%H:%M:%S")
        print(f"--- ОТЧЕТ {t_now} ---")
        print(f"Посетителей всего: {inside_total}")
        print("-" * 35)
        print(f"{'Стол':<6} | {'Занято':<8} | {'Свободно':<8}")
        print("-" * 35)
        
        for idx, count in enumerate(tables_status):
            free = max(0, TABLE_CAPACITY - count)
            # Визуальный маркер переполнения
            status_str = f"{count}" if count <= TABLE_CAPACITY else f"{count} (!)"
            print(f"#{idx+1:<5} | {status_str:<8} | {free:<8}")
            
        print("-" * 35)
        last_log_time = time.time()

    cv2.imshow("Monitor", output)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()