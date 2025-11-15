"""
Unit tests для core.viewport - управление viewport (scrolling, zooming).

Тестируемый модуль: core/viewport.py

Покрытие:
- Инициализация viewport с дефолтными и кастомными значениями
- Scrolling операции (scroll_to, scroll_by, center_on)
- Zooming операции (set_zoom, zoom_in, zoom_out)
- Reset функциональность
- Получение видимой области (get_visible_region)
- Ограничение границами канваса (constrain_to_canvas)
- Проверка видимости точки и прямоугольника
- Edge cases и граничные условия
"""

import pytest
from core.viewport import Viewport


# =============================================================================
# Тесты инициализации
# =============================================================================

def test_viewport_init_default_values() -> None:
    """
    Тест инициализации с дефолтными значениями.

    Проверяет стандартный размер 128x40 с offset (0,0) и zoom 1.0.
    """
    vp = Viewport()

    assert vp.width == 128
    assert vp.height == 40
    assert vp.offset_x == 0
    assert vp.offset_y == 0
    assert vp.zoom == 1.0


def test_viewport_init_custom_values() -> None:
    """
    Тест инициализации с кастомными значениями.

    Проверяет что все параметры корректно устанавливаются.
    """
    vp = Viewport(width=256, height=64, offset_x=100, offset_y=50, zoom=2.0)

    assert vp.width == 256
    assert vp.height == 64
    assert vp.offset_x == 100
    assert vp.offset_y == 50
    assert vp.zoom == 2.0


def test_viewport_init_zero_size() -> None:
    """
    Edge case: Инициализация с нулевым размером.

    Viewport может иметь нулевой размер (хотя это не имеет практического смысла).
    """
    vp = Viewport(width=0, height=0)

    assert vp.width == 0
    assert vp.height == 0


# =============================================================================
# Тесты scroll_to
# =============================================================================

def test_viewport_scroll_to_positive_coords() -> None:
    """
    Тест scroll_to с положительными координатами.

    Viewport должен переместиться в указанную позицию.
    """
    vp = Viewport()
    vp.scroll_to(100, 200)

    assert vp.offset_x == 100
    assert vp.offset_y == 200


def test_viewport_scroll_to_zero() -> None:
    """
    Тест scroll_to к началу координат.

    Проверяет установку offset в (0, 0).
    """
    vp = Viewport(offset_x=100, offset_y=200)
    vp.scroll_to(0, 0)

    assert vp.offset_x == 0
    assert vp.offset_y == 0


def test_viewport_scroll_to_negative_coords() -> None:
    """
    Edge case: scroll_to с отрицательными координатами.

    Viewport может иметь отрицательный offset (скроллинг "за пределы").
    """
    vp = Viewport()
    vp.scroll_to(-50, -100)

    assert vp.offset_x == -50
    assert vp.offset_y == -100


# =============================================================================
# Тесты scroll_by
# =============================================================================

def test_viewport_scroll_by_positive_delta() -> None:
    """
    Тест scroll_by с положительным смещением (вправо и вниз).

    Offset должен увеличиться на delta.
    """
    vp = Viewport(offset_x=10, offset_y=20)
    vp.scroll_by(5, 10)

    assert vp.offset_x == 15
    assert vp.offset_y == 30


def test_viewport_scroll_by_negative_delta() -> None:
    """
    Тест scroll_by с отрицательным смещением (влево и вверх).

    Offset должен уменьшиться на delta.
    """
    vp = Viewport(offset_x=100, offset_y=200)
    vp.scroll_by(-20, -50)

    assert vp.offset_x == 80
    assert vp.offset_y == 150


def test_viewport_scroll_by_zero() -> None:
    """
    Edge case: scroll_by с нулевым смещением.

    Offset не должен измениться.
    """
    vp = Viewport(offset_x=50, offset_y=100)
    vp.scroll_by(0, 0)

    assert vp.offset_x == 50
    assert vp.offset_y == 100


def test_viewport_scroll_by_multiple_times() -> None:
    """
    Тест множественных последовательных scroll_by.

    Проверяет аккумуляцию смещений.
    """
    vp = Viewport()
    vp.scroll_by(10, 20)
    vp.scroll_by(5, 10)
    vp.scroll_by(-3, -5)

    assert vp.offset_x == 12
    assert vp.offset_y == 25


# =============================================================================
# Тесты center_on
# =============================================================================

def test_viewport_center_on_point() -> None:
    """
    Тест center_on для центрирования на точке.

    Viewport должен сдвинуться так, чтобы точка оказалась в центре.
    """
    vp = Viewport(width=128, height=40)
    vp.center_on(200, 100)

    # offset_x = 200 - 128/2 = 200 - 64 = 136
    # offset_y = 100 - 40/2 = 100 - 20 = 80
    assert vp.offset_x == 136
    assert vp.offset_y == 80


def test_viewport_center_on_origin() -> None:
    """
    Тест center_on в начале координат.

    Проверяет центрирование на точке (0, 0).
    """
    vp = Viewport(width=128, height=40)
    vp.center_on(0, 0)

    # offset_x = 0 - 64 = -64
    # offset_y = 0 - 20 = -20
    assert vp.offset_x == -64
    assert vp.offset_y == -20


def test_viewport_center_on_odd_dimensions() -> None:
    """
    Edge case: center_on с нечётными размерами viewport.

    Проверяет корректность целочисленного деления.
    """
    vp = Viewport(width=127, height=39)
    vp.center_on(100, 50)

    # offset_x = 100 - 127//2 = 100 - 63 = 37
    # offset_y = 50 - 39//2 = 50 - 19 = 31
    assert vp.offset_x == 37
    assert vp.offset_y == 31


# =============================================================================
# Тесты set_zoom
# =============================================================================

def test_viewport_set_zoom_normal_value() -> None:
    """
    Тест set_zoom с нормальным значением.

    Zoom должен установиться в указанное значение.
    """
    vp = Viewport()
    vp.set_zoom(2.0)

    assert vp.zoom == 2.0


def test_viewport_set_zoom_below_minimum() -> None:
    """
    Edge case: set_zoom со значением < 0.1.

    Zoom должен быть ограничен минимумом 0.1.
    """
    vp = Viewport()
    vp.set_zoom(0.05)

    assert vp.zoom == 0.1


def test_viewport_set_zoom_above_maximum() -> None:
    """
    Edge case: set_zoom со значением > 10.0.

    Zoom должен быть ограничен максимумом 10.0.
    """
    vp = Viewport()
    vp.set_zoom(15.0)

    assert vp.zoom == 10.0


def test_viewport_set_zoom_exactly_minimum() -> None:
    """
    Тест set_zoom с точным минимумом.

    Zoom = 0.1 должен быть разрешён.
    """
    vp = Viewport()
    vp.set_zoom(0.1)

    assert vp.zoom == 0.1


def test_viewport_set_zoom_exactly_maximum() -> None:
    """
    Тест set_zoom с точным максимумом.

    Zoom = 10.0 должен быть разрешён.
    """
    vp = Viewport()
    vp.set_zoom(10.0)

    assert vp.zoom == 10.0


def test_viewport_set_zoom_negative() -> None:
    """
    Edge case: set_zoom с отрицательным значением.

    Zoom должен быть ограничен минимумом 0.1.
    """
    vp = Viewport()
    vp.set_zoom(-1.0)

    assert vp.zoom == 0.1


# =============================================================================
# Тесты zoom_in
# =============================================================================

def test_viewport_zoom_in_default_step() -> None:
    """
    Тест zoom_in с дефолтным шагом (0.1).

    Zoom должен увеличиться на 0.1.
    """
    vp = Viewport(zoom=1.0)
    vp.zoom_in()

    assert vp.zoom == pytest.approx(1.1)


def test_viewport_zoom_in_custom_step() -> None:
    """
    Тест zoom_in с кастомным шагом.

    Zoom должен увеличиться на указанный шаг.
    """
    vp = Viewport(zoom=1.0)
    vp.zoom_in(step=0.5)

    assert vp.zoom == pytest.approx(1.5)


def test_viewport_zoom_in_respects_maximum() -> None:
    """
    Edge case: zoom_in не должен превысить максимум.

    Zoom должен остаться на 10.0.
    """
    vp = Viewport(zoom=9.9)
    vp.zoom_in(step=0.5)

    assert vp.zoom == 10.0


def test_viewport_zoom_in_multiple_times() -> None:
    """
    Тест множественных zoom_in.

    Zoom должен аккумулироваться.
    """
    vp = Viewport(zoom=1.0)
    vp.zoom_in()
    vp.zoom_in()
    vp.zoom_in()

    assert vp.zoom == pytest.approx(1.3)


# =============================================================================
# Тесты zoom_out
# =============================================================================

def test_viewport_zoom_out_default_step() -> None:
    """
    Тест zoom_out с дефолтным шагом (0.1).

    Zoom должен уменьшиться на 0.1.
    """
    vp = Viewport(zoom=1.0)
    vp.zoom_out()

    assert vp.zoom == pytest.approx(0.9)


def test_viewport_zoom_out_custom_step() -> None:
    """
    Тест zoom_out с кастомным шагом.

    Zoom должен уменьшиться на указанный шаг.
    """
    vp = Viewport(zoom=2.0)
    vp.zoom_out(step=0.5)

    assert vp.zoom == pytest.approx(1.5)


def test_viewport_zoom_out_respects_minimum() -> None:
    """
    Edge case: zoom_out не должен уйти ниже минимума.

    Zoom должен остаться на 0.1.
    """
    vp = Viewport(zoom=0.2)
    vp.zoom_out(step=0.5)

    assert vp.zoom == 0.1


def test_viewport_zoom_out_multiple_times() -> None:
    """
    Тест множественных zoom_out.

    Zoom должен уменьшаться с каждым вызовом.
    """
    vp = Viewport(zoom=2.0)
    vp.zoom_out()
    vp.zoom_out()
    vp.zoom_out()

    assert vp.zoom == pytest.approx(1.7)


# =============================================================================
# Тесты reset
# =============================================================================

def test_viewport_reset_from_custom_state() -> None:
    """
    Тест reset после изменения состояния.

    Все значения должны вернуться к начальным.
    """
    vp = Viewport(offset_x=100, offset_y=200, zoom=2.5)
    vp.reset()

    assert vp.offset_x == 0
    assert vp.offset_y == 0
    assert vp.zoom == 1.0


def test_viewport_reset_preserves_size() -> None:
    """
    Тест что reset не меняет размер viewport.

    Width и height должны остаться прежними.
    """
    vp = Viewport(width=256, height=64, offset_x=100, offset_y=200, zoom=2.0)
    vp.reset()

    assert vp.width == 256
    assert vp.height == 64
    assert vp.offset_x == 0
    assert vp.offset_y == 0
    assert vp.zoom == 1.0


def test_viewport_reset_on_default_state() -> None:
    """
    Edge case: reset на уже сброшенном viewport.

    Ничего не должно измениться.
    """
    vp = Viewport()
    vp.reset()

    assert vp.offset_x == 0
    assert vp.offset_y == 0
    assert vp.zoom == 1.0


# =============================================================================
# Тесты get_visible_region
# =============================================================================

def test_viewport_get_visible_region_default() -> None:
    """
    Тест get_visible_region с дефолтным viewport.

    Видимая область должна быть (0, 0, 128, 40).
    """
    vp = Viewport()
    region = vp.get_visible_region()

    assert region == (0, 0, 128, 40)


def test_viewport_get_visible_region_with_offset() -> None:
    """
    Тест get_visible_region с offset.

    Видимая область должна сдвинуться на offset.
    """
    vp = Viewport(offset_x=100, offset_y=50)
    region = vp.get_visible_region()

    assert region == (100, 50, 228, 90)


def test_viewport_get_visible_region_negative_offset() -> None:
    """
    Edge case: get_visible_region с отрицательным offset.

    Видимая область может иметь отрицательные координаты.
    """
    vp = Viewport(offset_x=-50, offset_y=-25)
    region = vp.get_visible_region()

    assert region == (-50, -25, 78, 15)


# =============================================================================
# Тесты constrain_to_canvas
# =============================================================================

def test_viewport_constrain_to_canvas_no_change() -> None:
    """
    Тест constrain_to_canvas когда viewport уже в пределах.

    Offset не должен измениться.
    """
    vp = Viewport(width=128, height=40, offset_x=50, offset_y=50)
    vp.constrain_to_canvas(canvas_width=500, canvas_height=300)

    assert vp.offset_x == 50
    assert vp.offset_y == 50


def test_viewport_constrain_to_canvas_clamp_right() -> None:
    """
    Тест constrain_to_canvas когда viewport выходит за правый край.

    Offset должен быть ограничен.
    """
    vp = Viewport(width=128, height=40, offset_x=400, offset_y=50)
    vp.constrain_to_canvas(canvas_width=500, canvas_height=300)

    # max_offset_x = 500 - 128 = 372
    assert vp.offset_x == 372
    assert vp.offset_y == 50


def test_viewport_constrain_to_canvas_clamp_bottom() -> None:
    """
    Тест constrain_to_canvas когда viewport выходит за нижний край.

    Offset должен быть ограничен.
    """
    vp = Viewport(width=128, height=40, offset_x=50, offset_y=300)
    vp.constrain_to_canvas(canvas_width=500, canvas_height=300)

    # max_offset_y = 300 - 40 = 260
    assert vp.offset_x == 50
    assert vp.offset_y == 260


def test_viewport_constrain_to_canvas_clamp_left() -> None:
    """
    Тест constrain_to_canvas когда viewport выходит за левый край.

    Offset должен быть ограничен нулём.
    """
    vp = Viewport(width=128, height=40, offset_x=-50, offset_y=50)
    vp.constrain_to_canvas(canvas_width=500, canvas_height=300)

    assert vp.offset_x == 0
    assert vp.offset_y == 50


def test_viewport_constrain_to_canvas_clamp_top() -> None:
    """
    Тест constrain_to_canvas когда viewport выходит за верхний край.

    Offset должен быть ограничен нулём.
    """
    vp = Viewport(width=128, height=40, offset_x=50, offset_y=-25)
    vp.constrain_to_canvas(canvas_width=500, canvas_height=300)

    assert vp.offset_x == 50
    assert vp.offset_y == 0


def test_viewport_constrain_to_canvas_larger_than_canvas() -> None:
    """
    Edge case: viewport больше чем canvas.

    Offset должен быть установлен в 0.
    """
    vp = Viewport(width=1000, height=500, offset_x=100, offset_y=100)
    vp.constrain_to_canvas(canvas_width=500, canvas_height=200)

    # max_offset = max(0, canvas - viewport) = 0
    assert vp.offset_x == 0
    assert vp.offset_y == 0


def test_viewport_constrain_to_canvas_equal_size() -> None:
    """
    Edge case: viewport равен размеру canvas.

    Offset должен быть 0 (viewport точно покрывает весь canvas).
    """
    vp = Viewport(width=128, height=40, offset_x=50, offset_y=50)
    vp.constrain_to_canvas(canvas_width=128, canvas_height=40)

    assert vp.offset_x == 0
    assert vp.offset_y == 0


# =============================================================================
# Тесты is_point_visible
# =============================================================================

def test_viewport_is_point_visible_inside() -> None:
    """
    Тест is_point_visible когда точка внутри viewport.

    Должен вернуть True.
    """
    vp = Viewport(offset_x=100, offset_y=50)

    assert vp.is_point_visible(150, 70) is True


def test_viewport_is_point_visible_outside_left() -> None:
    """
    Тест is_point_visible когда точка левее viewport.

    Должен вернуть False.
    """
    vp = Viewport(offset_x=100, offset_y=50)

    assert vp.is_point_visible(50, 70) is False


def test_viewport_is_point_visible_outside_right() -> None:
    """
    Тест is_point_visible когда точка правее viewport.

    Должен вернуть False.
    """
    vp = Viewport(offset_x=100, offset_y=50)

    # right edge = 100 + 128 = 228
    assert vp.is_point_visible(230, 70) is False


def test_viewport_is_point_visible_outside_top() -> None:
    """
    Тест is_point_visible когда точка выше viewport.

    Должен вернуть False.
    """
    vp = Viewport(offset_x=100, offset_y=50)

    assert vp.is_point_visible(150, 20) is False


def test_viewport_is_point_visible_outside_bottom() -> None:
    """
    Тест is_point_visible когда точка ниже viewport.

    Должен вернуть False.
    """
    vp = Viewport(offset_x=100, offset_y=50)

    # bottom edge = 50 + 40 = 90
    assert vp.is_point_visible(150, 95) is False


def test_viewport_is_point_visible_on_left_edge() -> None:
    """
    Edge case: точка на левом краю viewport.

    Должен вернуть True (включён в диапазон).
    """
    vp = Viewport(offset_x=100, offset_y=50)

    assert vp.is_point_visible(100, 70) is True


def test_viewport_is_point_visible_on_right_edge() -> None:
    """
    Edge case: точка на правом краю viewport.

    Должен вернуть False (right < right, не <=).
    """
    vp = Viewport(offset_x=100, offset_y=50)

    # right edge = 100 + 128 = 228
    assert vp.is_point_visible(228, 70) is False


# =============================================================================
# Тесты is_rect_visible
# =============================================================================

def test_viewport_is_rect_visible_fully_inside() -> None:
    """
    Тест is_rect_visible когда прямоугольник полностью внутри.

    Должен вернуть True.
    """
    vp = Viewport(offset_x=100, offset_y=50)

    assert vp.is_rect_visible(110, 60, 20, 10) is True


def test_viewport_is_rect_visible_partially_left() -> None:
    """
    Тест is_rect_visible когда прямоугольник частично слева.

    Должен вернуть True (есть пересечение).
    """
    vp = Viewport(offset_x=100, offset_y=50)

    # rect от 80 до 120 пересекается с viewport от 100 до 228
    assert vp.is_rect_visible(80, 60, 40, 10) is True


def test_viewport_is_rect_visible_partially_right() -> None:
    """
    Тест is_rect_visible когда прямоугольник частично справа.

    Должен вернуть True (есть пересечение).
    """
    vp = Viewport(offset_x=100, offset_y=50)

    # rect от 220 до 240 пересекается с viewport до 228
    assert vp.is_rect_visible(220, 60, 20, 10) is True


def test_viewport_is_rect_visible_fully_outside_left() -> None:
    """
    Тест is_rect_visible когда прямоугольник полностью слева.

    Должен вернуть False (нет пересечения).
    """
    vp = Viewport(offset_x=100, offset_y=50)

    # rect от 50 до 90, viewport начинается с 100
    assert vp.is_rect_visible(50, 60, 40, 10) is False


def test_viewport_is_rect_visible_fully_outside_right() -> None:
    """
    Тест is_rect_visible когда прямоугольник полностью справа.

    Должен вернуть False (нет пересечения).
    """
    vp = Viewport(offset_x=100, offset_y=50)

    # rect от 230 до 250, viewport заканчивается на 228
    assert vp.is_rect_visible(230, 60, 20, 10) is False


def test_viewport_is_rect_visible_fully_outside_top() -> None:
    """
    Тест is_rect_visible когда прямоугольник полностью сверху.

    Должен вернуть False (нет пересечения).
    """
    vp = Viewport(offset_x=100, offset_y=50)

    # rect от 20 до 40, viewport начинается с 50
    assert vp.is_rect_visible(150, 20, 20, 20) is False


def test_viewport_is_rect_visible_fully_outside_bottom() -> None:
    """
    Тест is_rect_visible когда прямоугольник полностью снизу.

    Должен вернуть False (нет пересечения).
    """
    vp = Viewport(offset_x=100, offset_y=50)

    # rect от 100 до 120, viewport заканчивается на 90
    assert vp.is_rect_visible(150, 100, 20, 20) is False


def test_viewport_is_rect_visible_larger_than_viewport() -> None:
    """
    Edge case: прямоугольник больше viewport.

    Должен вернуть True если есть пересечение.
    """
    vp = Viewport(offset_x=100, offset_y=50)

    # Огромный rect полностью покрывает viewport
    assert vp.is_rect_visible(0, 0, 1000, 1000) is True


def test_viewport_is_rect_visible_zero_size() -> None:
    """
    Edge case: прямоугольник нулевого размера (точка).

    Нулевой прямоугольник внутри viewport считается видимым.
    """
    vp = Viewport(offset_x=100, offset_y=50)

    # Точка (150, 70) внутри viewport [(100,50) to (228,90)]
    assert vp.is_rect_visible(150, 70, 0, 0) is True

    # Точка снаружи - не видна
    assert vp.is_rect_visible(50, 70, 0, 0) is False


# =============================================================================
# Тесты __repr__
# =============================================================================

def test_viewport_repr_default() -> None:
    """
    Тест строкового представления viewport.

    Проверяет формат __repr__.
    """
    vp = Viewport()
    repr_str = repr(vp)

    assert "Viewport" in repr_str
    assert "128x40" in repr_str
    assert "(0,0)" in repr_str
    assert "1.00" in repr_str


def test_viewport_repr_custom() -> None:
    """
    Тест __repr__ с кастомными значениями.

    Проверяет что все значения отображаются.
    """
    vp = Viewport(width=256, height=64, offset_x=100, offset_y=200, zoom=2.5)
    repr_str = repr(vp)

    assert "256x64" in repr_str
    assert "(100,200)" in repr_str
    assert "2.50" in repr_str


# =============================================================================
# Integration тесты
# =============================================================================

def test_viewport_full_workflow() -> None:
    """
    Integration тест полного жизненного цикла viewport.

    Проверяет комбинацию операций scrolling и zooming.
    """
    vp = Viewport(width=128, height=40)

    # Scroll to position
    vp.scroll_to(100, 50)
    assert vp.offset_x == 100
    assert vp.offset_y == 50

    # Scroll by delta
    vp.scroll_by(20, 30)
    assert vp.offset_x == 120
    assert vp.offset_y == 80

    # Zoom in
    vp.zoom_in()
    assert vp.zoom == pytest.approx(1.1)

    # Center on point
    vp.center_on(200, 100)
    assert vp.offset_x == 136
    assert vp.offset_y == 80

    # Constrain to canvas
    vp.constrain_to_canvas(300, 200)
    assert vp.offset_x == 136
    assert vp.offset_y == 80

    # Reset
    vp.reset()
    assert vp.offset_x == 0
    assert vp.offset_y == 0
    assert vp.zoom == 1.0


def test_viewport_scrolling_and_visibility() -> None:
    """
    Integration тест scrolling и проверки видимости.

    Проверяет что видимость точек меняется при scrolling.
    """
    vp = Viewport()

    # Точка видна в начале
    assert vp.is_point_visible(64, 20) is True

    # Scroll вправо
    vp.scroll_by(100, 0)
    # Точка больше не видна
    assert vp.is_point_visible(64, 20) is False
    # Новая точка видна
    assert vp.is_point_visible(164, 20) is True


def test_viewport_zoom_bounds() -> None:
    """
    Integration тест границ zoom.

    Проверяет что zoom корректно ограничивается при множественных операциях.
    """
    vp = Viewport()

    # Zoom in много раз
    for _ in range(100):
        vp.zoom_in(step=1.0)

    # Должен остаться на максимуме
    assert vp.zoom == 10.0

    # Zoom out много раз
    for _ in range(100):
        vp.zoom_out(step=1.0)

    # Должен остаться на минимуме
    assert vp.zoom == 0.1
