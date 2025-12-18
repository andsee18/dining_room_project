import cv2
import pickle
import argparse
import numpy as np

rois = []
current_polygon_points = []
frame_copy = None


def select_points(event, x, y, flags, param):
    global current_polygon_points, rois, frame

    if event == cv2.EVENT_LBUTTONDOWN:
        current_polygon_points.append((x, y))
        cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

        if len(current_polygon_points) > 1:
            cv2.line(frame, current_polygon_points[-2], (x, y), (0, 255, 0), 2)

        if len(current_polygon_points) == 4:
            polygon = np.array(current_polygon_points, dtype=np.int32)
            rois.append(polygon)
            print(f"[OK] Добавлен стол #{len(rois)}")

            cv2.polylines(frame, [polygon], True, (0, 0, 255), 2)
            current_polygon_points = []


parser = argparse.ArgumentParser(description="Выбор столов (ROI)")
parser.add_argument("video_path", type=str)
args = parser.parse_args()

cap = cv2.VideoCapture(args.video_path)
if not cap.isOpened():
    exit("Ошибка: не удалось открыть видео")

ret, frame = cap.read()
cap.release()
if not ret:
    exit("Ошибка: не удалось получить кадр")

frame_copy = frame.copy()

window = "Выбор столов: S - сохранить, R - сброс"
cv2.namedWindow(window)
cv2.setMouseCallback(window, select_points)

print("Кликни 4 точки — стол. Потом следующий... Нажми S чтобы сохранить.")

while True:
    cv2.imshow(window, frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    elif key == ord("r"):
        print("Сброс.")
        frame = frame_copy.copy()
        rois = []
        current_polygon_points = []

    elif key == ord("s"):
        with open("tables.pkl", "wb") as f:
            pickle.dump(rois, f)
        print("[OK] СТОЛЫ СОХРАНЕНЫ → tables.pkl")
        break

cv2.destroyAllWindows()
