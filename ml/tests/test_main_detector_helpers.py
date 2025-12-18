import numpy as np


def test_bbox_center():
    # центр bbox
    from detector_utils import bbox_center

    assert bbox_center((0, 0, 10, 10)) == (5, 5)


def test_calculate_side_sign():
    # сторона точки относительно линии
    from detector_utils import calculate_side

    line = ((0, 0), (10, 0))
    assert calculate_side(line, (5, 1)) < 0  # точка ниже линии тут
    assert calculate_side(line, (5, -1)) > 0  # точка выше линии тут


def test_is_point_in_roi_square():
    # попадание точки в roi
    from detector_utils import is_point_in_roi

    roi = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=np.int32)
    assert is_point_in_roi(roi, (5, 5), roi_margin_px=0) is True
    assert is_point_in_roi(roi, (50, 50), roi_margin_px=0) is False


def test_bbox_iou():
    # iou между bbox
    from detector_utils import bbox_iou

    a = (0, 0, 10, 10)
    b = (0, 0, 10, 10)
    c = (10, 10, 20, 20)
    assert bbox_iou(a, b) == 1.0
    assert bbox_iou(a, c) == 0.0


def test_dedup_boxes_by_iou_prefers_higher_score():
    # удаление дубликатов bbox по iou
    from detector_utils import dedup_boxes_by_iou

    boxes = [
        (0, 0, 10, 10),
        (1, 1, 9, 9),  # сильное перекрытие с боксом
        (20, 20, 30, 30),
    ]
    scores = [0.9, 0.2, 0.5]
    keep = dedup_boxes_by_iou(boxes, scores=scores, iou_threshold=0.6)
    # оставляем лучший и дальний
    assert 0 in keep
    assert 2 in keep
    assert 1 not in keep


def test_table_count_smoother_confirms_changes_and_holds_after_drop_to_zero():
    # сглаживание количества столов
    from smoothing import TableCountSmoother

    smoother = TableCountSmoother(
        n_tables=1,
        smooth_window=1,
        change_confirm_frames=2,
        hold_seconds=2.0,
    )

    # нужно два кадра подряд
    smoother.update([2], now_ts=0.0)
    assert smoother.current(now_ts=0.0) == [0]
    smoother.update([2], now_ts=0.1)
    assert smoother.current(now_ts=0.1) == [2]

    # снова нужно два кадра
    smoother.update([0], now_ts=0.2)
    assert smoother.current(now_ts=0.2) == [2]
    smoother.update([0], now_ts=0.3)

    # держим прошлое значение секунды
    assert smoother.current(now_ts=0.3) == [2]
    assert smoother.current(now_ts=3.5) == [0]
