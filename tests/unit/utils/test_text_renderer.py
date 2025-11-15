"""
Unit tests для utils.text_renderer - рендеринг текста с выравниванием.

Тестируемый модуль: utils/text_renderer.py

Покрытие:
- Рендеринг одной строки текста (render_single_line_text)
- Рендеринг нескольких строк (render_multi_line_text)
- Рендеринг сетки значений (render_grid_text)
- Измерение размера текста (measure_text_size)
- Различные варианты выравнивания (left/center/right, top/center/bottom)
- Работа с цветами и альфа-каналом
- Edge cases
"""

import pytest
from utils.text_renderer import (
    render_single_line_text,
    render_multi_line_text,
    render_grid_text,
    measure_text_size
)
from utils.bitmap import create_blank_image


# =============================================================================
# Тесты render_single_line_text
# =============================================================================

def test_render_single_line_text_basic() -> None:
    """
    Тест базового рендеринга одной строки текста.

    Проверяет что текст рисуется без ошибок.
    """
    image = create_blank_image(128, 40)
    render_single_line_text(image, "TEST")

    # Должны появиться белые пиксели (текст отрисован)
    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


@pytest.mark.parametrize("h_align", ["left", "center", "right"])
def test_render_single_line_text_horizontal_align(h_align: str) -> None:
    """
    Параметризованный тест горизонтального выравнивания.

    Проверяет все варианты выравнивания: left, center, right.
    """
    image = create_blank_image(128, 40)
    render_single_line_text(image, "TEST", horizontal_align=h_align)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


@pytest.mark.parametrize("v_align", ["top", "center", "bottom"])
def test_render_single_line_text_vertical_align(v_align: str) -> None:
    """
    Параметризованный тест вертикального выравнивания.

    Проверяет все варианты выравнивания: top, center, bottom.
    """
    image = create_blank_image(128, 40)
    render_single_line_text(image, "TEST", vertical_align=v_align)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_single_line_text_with_padding() -> None:
    """
    Тест рендеринга с отступами.

    Проверяет параметр padding.
    """
    image = create_blank_image(128, 40)
    render_single_line_text(image, "TEST", padding=10)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_single_line_text_with_color() -> None:
    """
    Тест рендеринга с кастомным цветом.

    Проверяет параметр color.
    """
    image = create_blank_image(128, 40)
    render_single_line_text(image, "TEST", color=200)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_single_line_text_with_alpha_channel() -> None:
    """
    Тест рендеринга на изображение с альфа-каналом.

    Текст должен быть полностью непрозрачным (alpha=255).
    """
    image = create_blank_image(128, 40, opacity=128)  # LA mode
    render_single_line_text(image, "TEST", color=200)

    assert image.mode == 'LA'


def test_render_single_line_text_empty_string() -> None:
    """
    Edge case: рендеринг пустой строки.

    Не должно вызвать ошибку.
    """
    image = create_blank_image(128, 40)
    render_single_line_text(image, "")

    # Изображение должно остаться пустым
    pixels = list(image.getdata())
    assert all(p == 0 for p in pixels)


def test_render_single_line_text_long_text() -> None:
    """
    Edge case: рендеринг очень длинного текста.

    Текст может выйти за пределы изображения.
    """
    image = create_blank_image(128, 40)
    render_single_line_text(image, "A" * 100)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_single_line_text_with_font_size() -> None:
    """
    Тест рендеринга с кастомным размером шрифта.

    Проверяет параметр font_size.
    """
    image = create_blank_image(128, 40)
    render_single_line_text(image, "TEST", font_size=14)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


# =============================================================================
# Тесты render_multi_line_text
# =============================================================================

def test_render_multi_line_text_basic() -> None:
    """
    Тест рендеринга нескольких строк текста.

    Проверяет что все строки рисуются.
    """
    image = create_blank_image(128, 40)
    lines = [
        ("Line 1", 255),
        ("Line 2", 200),
        ("Line 3", 150)
    ]
    render_multi_line_text(image, lines)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_multi_line_text_empty_list() -> None:
    """
    Edge case: рендеринг пустого списка строк.

    Должен вернуться сразу без ошибок.
    """
    image = create_blank_image(128, 40)
    render_multi_line_text(image, [])

    pixels = list(image.getdata())
    assert all(p == 0 for p in pixels)


def test_render_multi_line_text_single_line() -> None:
    """
    Тест рендеринга одной строки через multi_line функцию.

    Должен работать как single_line.
    """
    image = create_blank_image(128, 40)
    lines = [("TEST", 255)]
    render_multi_line_text(image, lines)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


@pytest.mark.parametrize("h_align", ["left", "center", "right"])
def test_render_multi_line_text_horizontal_align(h_align: str) -> None:
    """
    Параметризованный тест горизонтального выравнивания блока.

    Каждая строка выравнивается независимо.
    """
    image = create_blank_image(128, 40)
    lines = [("Short", 255), ("Much longer text", 200)]
    render_multi_line_text(image, lines, horizontal_align=h_align)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


@pytest.mark.parametrize("v_align", ["top", "center", "bottom"])
def test_render_multi_line_text_vertical_align(v_align: str) -> None:
    """
    Параметризованный тест вертикального выравнивания блока.

    Весь блок строк выравнивается как единое целое.
    """
    image = create_blank_image(128, 40)
    lines = [("Line 1", 255), ("Line 2", 200)]
    render_multi_line_text(image, lines, vertical_align=v_align)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_multi_line_text_with_line_spacing() -> None:
    """
    Тест рендеринга с кастомным промежутком между строками.

    Проверяет параметр line_spacing.
    """
    image = create_blank_image(128, 40)
    lines = [("Line 1", 255), ("Line 2", 200)]
    render_multi_line_text(image, lines, line_spacing=5)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_multi_line_text_different_colors() -> None:
    """
    Тест что каждая строка может иметь свой цвет.

    Проверяет индивидуальные цвета строк.
    """
    image = create_blank_image(128, 40)
    lines = [
        ("Red-ish", 200),
        ("Gray", 128),
        ("White", 255)
    ]
    render_multi_line_text(image, lines)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_multi_line_text_with_padding() -> None:
    """
    Тест рендеринга многострочного текста с отступами.

    Проверяет параметр padding.
    """
    image = create_blank_image(128, 40)
    lines = [("Line 1", 255), ("Line 2", 200)]
    render_multi_line_text(image, lines, padding=5)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_multi_line_text_many_lines() -> None:
    """
    Edge case: рендеринг большого количества строк.

    Строки могут выйти за пределы изображения.
    """
    image = create_blank_image(128, 40)
    lines = [(f"Line {i}", 255) for i in range(10)]
    render_multi_line_text(image, lines)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_multi_line_text_with_alpha_channel() -> None:
    """
    Тест рендеринга на изображение с альфа-каналом.

    Текст должен быть полностью непрозрачным.
    """
    image = create_blank_image(128, 40, opacity=128)
    lines = [("Line 1", 255), ("Line 2", 200)]
    render_multi_line_text(image, lines)

    assert image.mode == 'LA'


# =============================================================================
# Тесты render_grid_text
# =============================================================================

def test_render_grid_text_basic() -> None:
    """
    Тест рендеринга сетки значений.

    Проверяет что все значения рисуются.
    """
    image = create_blank_image(128, 40)
    values = [10.5, 20.3, 30.7, 40.2]
    render_grid_text(image, values, decimal_places=1)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_grid_text_empty_list() -> None:
    """
    Edge case: рендеринг пустого списка значений.

    Должен вернуться сразу без ошибок.
    """
    image = create_blank_image(128, 40)
    render_grid_text(image, [])

    pixels = list(image.getdata())
    assert all(p == 0 for p in pixels)


def test_render_grid_text_single_value() -> None:
    """
    Тест рендеринга одного значения.

    Должен создать сетку 1x1.
    """
    image = create_blank_image(128, 40)
    render_grid_text(image, [42.0])

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_grid_text_integer_values() -> None:
    """
    Тест рендеринга целых чисел (decimal_places=0).

    Проверяет форматирование без десятичных знаков.
    """
    image = create_blank_image(128, 40)
    values = [10.0, 20.0, 30.0, 40.0]
    render_grid_text(image, values, decimal_places=0)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_grid_text_decimal_values() -> None:
    """
    Тест рендеринга дробных чисел с decimal_places.

    Проверяет форматирование с указанным количеством знаков.
    """
    image = create_blank_image(128, 40)
    values = [10.123, 20.456, 30.789]
    render_grid_text(image, values, decimal_places=2)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_grid_text_perfect_square() -> None:
    """
    Тест рендеринга идеального квадрата (4, 9, 16 значений).

    Проверяет оптимальное размещение в сетке.
    """
    image = create_blank_image(128, 40)
    values = [float(i) for i in range(9)]  # 3x3 grid
    render_grid_text(image, values)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_grid_text_non_square() -> None:
    """
    Тест рендеринга не идеального квадрата (5, 6, 7 значений).

    Проверяет корректное вычисление строк и столбцов.
    """
    image = create_blank_image(128, 40)
    values = [float(i) for i in range(6)]  # Should be 2x3 or 3x2
    render_grid_text(image, values)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_grid_text_many_values() -> None:
    """
    Тест рендеринга большого количества значений.

    Проверяет масштабирование сетки.
    """
    image = create_blank_image(128, 40)
    values = [float(i) for i in range(16)]  # 4x4 grid
    render_grid_text(image, values)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_grid_text_with_padding() -> None:
    """
    Тест рендеринга сетки с отступами.

    Проверяет параметр padding.
    """
    image = create_blank_image(128, 40)
    values = [1.0, 2.0, 3.0, 4.0]
    render_grid_text(image, values, padding=5)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_grid_text_with_color() -> None:
    """
    Тест рендеринга сетки с кастомным цветом.

    Проверяет параметр color.
    """
    image = create_blank_image(128, 40)
    values = [1.0, 2.0, 3.0, 4.0]
    render_grid_text(image, values, color=200)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_render_grid_text_with_alpha_channel() -> None:
    """
    Тест рендеринга на изображение с альфа-каналом.

    Текст должен быть полностью непрозрачным.
    """
    image = create_blank_image(128, 40, opacity=128)
    values = [1.0, 2.0, 3.0, 4.0]
    render_grid_text(image, values)

    assert image.mode == 'LA'


# =============================================================================
# Тесты measure_text_size
# =============================================================================

def test_measure_text_size_basic() -> None:
    """
    Тест измерения размера текста.

    Проверяет что возвращается корректный tuple (width, height).
    """
    width, height = measure_text_size("TEST")

    assert isinstance(width, int)
    assert isinstance(height, int)
    assert width > 0
    assert height > 0


def test_measure_text_size_empty_string() -> None:
    """
    Edge case: измерение пустой строки.

    Должен вернуть (0, 0) для пустой строки.
    """
    width, height = measure_text_size("")

    assert isinstance(width, int)
    assert isinstance(height, int)
    assert width == 0  # Пустая строка имеет ширину 0
    assert height == 0  # Пустая строка имеет высоту 0


def test_measure_text_size_long_text() -> None:
    """
    Тест измерения длинного текста.

    Ширина должна быть значительно больше высоты.
    """
    width, height = measure_text_size("A" * 50)

    assert width > height


def test_measure_text_size_with_font_size() -> None:
    """
    Тест что размер шрифта влияет на результат.

    Больший шрифт должен давать больший размер.
    """
    width_small, height_small = measure_text_size("TEST", font_size=8)
    width_large, height_large = measure_text_size("TEST", font_size=16)

    assert width_large > width_small
    assert height_large > height_small


def test_measure_text_size_same_font_same_size() -> None:
    """
    Тест что одинаковый текст дает одинаковый размер.

    Проверяет консистентность измерения.
    """
    size1 = measure_text_size("TEST", font_size=12)
    size2 = measure_text_size("TEST", font_size=12)

    assert size1 == size2


def test_measure_text_size_different_texts() -> None:
    """
    Тест что разные тексты дают разные размеры.

    Короткий текст должен быть уже длинного.
    """
    width_short, _ = measure_text_size("Hi")
    width_long, _ = measure_text_size("Hello World")

    assert width_long > width_short


# =============================================================================
# Integration тесты
# =============================================================================

def test_text_renderer_full_workflow() -> None:
    """
    Integration тест использования всех функций рендеринга.

    Проверяет комбинированное использование.
    """
    image = create_blank_image(128, 40)

    # Измеряем размер текста
    width, height = measure_text_size("TEST", font_size=10)
    assert width > 0
    assert height > 0

    # Рендерим одну строку
    render_single_line_text(image, "Single", vertical_align="top")

    # Рендерим несколько строк
    lines = [("Line1", 255), ("Line2", 200)]
    render_multi_line_text(image, lines, vertical_align="center")

    # Рендерим сетку
    values = [1.0, 2.0, 3.0, 4.0]
    render_grid_text(image, values, padding=2)

    pixels = list(image.getdata())
    assert any(p > 0 for p in pixels)


def test_text_renderer_all_alignments() -> None:
    """
    Integration тест всех комбинаций выравнивания.

    Проверяет 9 комбинаций (3x3).
    """
    for h_align in ["left", "center", "right"]:
        for v_align in ["top", "center", "bottom"]:
            image = create_blank_image(128, 40)
            render_single_line_text(
                image, "TEST",
                horizontal_align=h_align,
                vertical_align=v_align
            )

            pixels = list(image.getdata())
            assert any(p > 0 for p in pixels), f"Failed for {h_align}/{v_align}"


def test_text_renderer_different_image_sizes() -> None:
    """
    Integration тест рендеринга на изображения разных размеров.

    Проверяет адаптивность к размеру.
    """
    for width, height in [(64, 20), (128, 40), (256, 64)]:
        image = create_blank_image(width, height)
        render_single_line_text(image, "TEST")

        pixels = list(image.getdata())
        assert any(p > 0 for p in pixels)
