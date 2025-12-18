import cv2
import pickle
import argparse
import numpy as np

points = []
frame_copy = None
inside_point = None

def select_logic(event, x, y, flags, param):
    global points, frame, inside_point

    if event == cv2.EVENT_LBUTTONDOWN:

        if len(points) < 2:
            points.append((x, y))
            cv2.circle(frame, (x, y), 5, (0, 255, 255), -1)
            
            if len(points) == 2:
                cv2.line(frame, points[0], points[1], (0, 255, 255), 3)
                print("[INFO] Линия входа задана. Теперь кликни ВНУТРИ помещения.")

        elif len(points) == 2 and inside_point is None:
            inside_point = (x, y)
            cv2.circle(frame, (x, y), 8, (0, 255, 0), -1)
            cv2.putText(frame, "INSIDE", (x + 10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            mid_x = int((points[0][0] + points[1][0]) / 2)
            mid_y = int((points[0][1] + points[1][1]) / 2)
            cv2.arrowedLine(frame, (mid_x, mid_y), (x, y), (0, 255, 0), 2)
            print("[INFO] Направление задано. Нажми S для сохранения.")

parser = argparse.ArgumentParser()
parser.add_argument("video_path")
args = parser.parse_args()

cap = cv2.VideoCapture(args.video_path)
ret, frame = cap.read()
cap.release()

if not ret:
    exit("Не удалось прочитать видео")

frame_copy = frame.copy()
window = "Setup Entry"
cv2.namedWindow(window)
cv2.setMouseCallback(window, select_logic)

print("1. Кликни 2 точки (линия входа).")
print("2. Кликни 1 точку ВНУТРИ помещения.")
print("3. Нажми S для сохранения.")

while True:
    cv2.imshow(window, frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    elif key == ord("r"):
        points = []
        inside_point = None
        frame = frame_copy.copy()
        print("Сброс.")

    elif key == ord("s"):
        if len(points) == 2 and inside_point is not None:
            data = {
                "line": points,
                "inside_ref": inside_point
            }
            with open("entry_lines.pkl", "wb") as f:
                pickle.dump(data, f)
            print("[OK] Сохранено в entry_lines.pkl")
            break
        else:
            print("Сначала закончи настройку (2 точки линии + 1 точка внутри)!")

cv2.destroyAllWindows()