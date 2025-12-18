from __future__ import annotations

import math
from typing import Iterable, List, Optional, Sequence, Tuple

BoxXYXY = Tuple[float, float, float, float]
PointXY = Tuple[int, int]


def _roi_points(roi) -> List[PointXY]:
    if hasattr(roi, "tolist"):
        pts = roi.tolist()
    else:
        pts = list(roi)
    return [(int(x), int(y)) for x, y in pts]


def _point_in_polygon(poly: Sequence[PointXY], point: PointXY) -> bool:
    x, y = point
    inside = False

    n = len(poly)
    if n < 3:
        return False

    x1, y1 = poly[-1]
    for x2, y2 in poly:
        intersects = ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / (y2 - y1 + 0.0) + x1
        )
        if intersects:
            inside = not inside
        x1, y1 = x2, y2

    return inside


def _point_to_segment_distance(p: PointXY, a: PointXY, b: PointXY) -> float:
    px, py = float(p[0]), float(p[1])
    ax, ay = float(a[0]), float(a[1])
    bx, by = float(b[0]), float(b[1])

    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay

    ab_len2 = abx * abx + aby * aby
    if ab_len2 <= 0.0:
        return math.hypot(px - ax, py - ay)

    t = (apx * abx + apy * aby) / ab_len2
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)

    cx = ax + t * abx
    cy = ay + t * aby
    return math.hypot(px - cx, py - cy)


def _signed_distance_to_polygon(poly: Sequence[PointXY], point: PointXY) -> float:
    if len(poly) < 2:
        return float("-inf")

    min_dist = float("inf")
    prev = poly[-1]
    for cur in poly:
        min_dist = min(min_dist, _point_to_segment_distance(point, prev, cur))
        prev = cur

    inside = _point_in_polygon(poly, point)
    return min_dist if inside else -min_dist


def calculate_side(line: Tuple[PointXY, PointXY], point: PointXY) -> int:
    (x1, y1), (x2, y2) = line
    px, py = point
    return int((px - x1) * (y2 - y1) - (py - y1) * (x2 - x1))


def bbox_center(box: Sequence[float]) -> PointXY:
    x1, y1, x2, y2 = [int(v) for v in box]
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


def bbox_anchor_points(box: Sequence[float]) -> List[PointXY]:
    """точки привязки бокса к рои"""

    x1, y1, x2, y2 = [int(v) for v in box]
    cx = int((x1 + x2) / 2)
    cy = int((y1 + y2) / 2)
    w = max(1, x2 - x1)
    h = max(1, y2 - y1)

    # точки ближе к низу бокса
    y80 = y1 + int(0.80 * h)
    y90 = y1 + int(0.90 * h)
    x25 = x1 + int(0.25 * w)
    x75 = x1 + int(0.75 * w)

    points: List[PointXY] = [
        (cx, cy),
        (cx, y80),
        (cx, y90),
        (x25, y80),
        (x75, y80),
        (x25, y90),
        (x75, y90),
        (cx, y2),
    ]

    # удаляем повторы точек бокса
    uniq: List[PointXY] = []
    seen = set()
    for p in points:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def bbox_iou(box_a: Sequence[float], box_b: Sequence[float]) -> float:
    """айоу пересечение для бокса"""

    ax1, ay1, ax2, ay2 = [float(v) for v in box_a]
    bx1, by1, bx2, by2 = [float(v) for v in box_b]

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0.0, inter_x2 - inter_x1)
    inter_h = max(0.0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    denom = area_a + area_b - inter_area
    if denom <= 0:
        return 0.0
    return inter_area / denom


def dedup_boxes_by_iou(
    boxes: Optional[Sequence[Sequence[float]]],
    scores: Optional[Sequence[float]] = None,
    iou_threshold: float = 0.6,
) -> List[int]:
    """удаляем дубли боксов по айоу"""

    if boxes is None or len(boxes) == 0:
        return []
    if scores is None:
        scores = [1.0] * len(boxes)

    order = sorted(range(len(boxes)), key=lambda i: float(scores[i]), reverse=True)
    keep: List[int] = []
    for i in order:
        should_keep = True
        for j in keep:
            if bbox_iou(boxes[i], boxes[j]) >= iou_threshold:
                should_keep = False
                break
        if should_keep:
            keep.append(i)
    return keep


def is_point_in_roi(roi, point: PointXY, roi_margin_px: float) -> bool:
    # проверяем точку внутри рои
    # допускаем небольшой запас пикселей
    poly = _roi_points(roi)
    dist = _signed_distance_to_polygon(poly, point)
    return dist >= -float(roi_margin_px)


def best_roi_for_bbox(rois: Iterable, box: Sequence[float], roi_margin_px: float) -> Optional[int]:
    """выбор лучшей рои для бокса"""

    points = bbox_anchor_points(box)
    best_idx: Optional[int] = None
    best_in_count = -1
    best_dist_sum = float("-inf")

    for idx, roi in enumerate(rois):
        poly = _roi_points(roi)
        in_count = 0
        dist_sum = 0.0
        for p in points:
            dist = _signed_distance_to_polygon(poly, p)
            if dist >= -roi_margin_px:
                in_count += 1
                dist_sum += dist
        if in_count <= 0:
            continue
        if (in_count > best_in_count) or (in_count == best_in_count and dist_sum > best_dist_sum):
            best_in_count = in_count
            best_dist_sum = dist_sum
            best_idx = idx

    return best_idx
