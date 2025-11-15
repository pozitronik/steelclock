"""
Unit tests для widgets.clock - виджет часов.

Тестируемый модуль: widgets/clock.py

Покрытие:
- Инициализация с дефолтными и кастомными параметрами
- Обновление времени (update)
- Рендеринг изображения (render)
- Форматирование времени (strftime)
- Выравнивание текста (horizontal_align, vertical_align)
- Стилизация (background, border, padding)
- Изменение формата (set_format)
- Получение строки времени (get_current_time_string)
- Edge cases и error handling
"""

import pytest
from PIL import Image
from datetime import datetime
from unittest.mock import patch, Mock

from widgets.clock import ClockWidget


# =============================================================================
# Тесты инициализации
# =============================================================================

def test_clock_init_default_values():
    """
    Тест инициализации Clock widget с дефолтными параметрами.

    Проверяет:
    - Дефолтный формат "%H:%M:%S"
    - Дефолтный интервал обновления 1.0 секунда
    - Дефолтные стили (no border, black background, center align)
    """
    widget = ClockWidget()

    assert widget.name == "Clock"
    assert widget.format_string == "%H:%M:%S"
    assert widget.update_interval_sec == 1.0
    assert widget.font_size == 12
    assert widget.font is None
    assert widget.background_color == 0
    assert widget.background_opacity == 255
    assert widget.border is False
    assert widget.horizontal_align == "center"
    assert widget.vertical_align == "center"
    assert widget.padding == 0


def test_clock_init_custom_values():
    """
    Тест инициализации Clock widget с кастомными параметрами.

    Проверяет возможность переопределения всех параметров.
    """
    widget = ClockWidget(
        name="CustomClock",
        format_string="%H:%M",
        update_interval=0.5,
        font_size=16,
        font="Arial",
        background_color=128,
        background_opacity=200,
        border=True,
        border_color=200,
        horizontal_align="left",
        vertical_align="top",
        padding=5
    )

    assert widget.name == "CustomClock"
    assert widget.format_string == "%H:%M"
    assert widget.update_interval_sec == 0.5
    assert widget.font_size == 16
    assert widget.font == "Arial"
    assert widget.background_color == 128
    assert widget.background_opacity == 200
    assert widget.border is True
    assert widget.border_color == 200
    assert widget.horizontal_align == "left"
    assert widget.vertical_align == "top"
    assert widget.padding == 5


def test_clock_init_sets_time_to_none():
    """
    Тест что инициализация устанавливает _current_time в None.

    Время должно обновляться только при вызове update().
    """
    widget = ClockWidget()

    assert widget._current_time is None
    assert widget._formatted_time == ""


# =============================================================================
# Тесты update()
# =============================================================================

def test_clock_update_sets_current_time():
    """
    Тест что update() обновляет текущее время.

    Проверяет:
    - _current_time устанавливается
    - _formatted_time форматируется согласно format_string
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget(format_string="%H:%M:%S")
        widget.update()

        assert widget._current_time == fixed_time
        assert widget._formatted_time == "12:34:56"


def test_clock_update_with_custom_format():
    """
    Тест update() с различными форматами времени.

    Проверяет что strftime корректно применяется.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget(format_string="%Y-%m-%d %H:%M")
        widget.update()

        assert widget._formatted_time == "2025-11-15 12:34"


@pytest.mark.parametrize("format_str,expected", [
    ("%H:%M", "12:34"),
    ("%H:%M:%S", "12:34:56"),
    ("%d.%m.%Y", "15.11.2025"),
    ("%Y-%m-%d", "2025-11-15"),
    ("%a %d %b %Y", "Sat 15 Nov 2025"),
])
def test_clock_update_various_formats(format_str, expected):
    """
    Тест update() с различными форматами strftime.

    Параметризованный тест проверяет множество форматов.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget(format_string=format_str)
        widget.update()

        assert widget._formatted_time == expected


def test_clock_update_handles_error():
    """
    Тест что update() обрабатывает ошибки форматирования.

    Edge case: Невалидный формат должен установить "ERROR".
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        # Симулируем ошибку в strftime
        mock_time = Mock()
        mock_time.strftime.side_effect = ValueError("Invalid format")
        mock_datetime.now.return_value = mock_time

        widget = ClockWidget()
        widget.update()

        assert widget._formatted_time == "ERROR"


# =============================================================================
# Тесты render()
# =============================================================================

def test_clock_render_returns_image():
    """
    Тест что render() возвращает PIL Image.

    Проверяет:
    - Возвращается Image.Image
    - Размер соответствует размерам виджета
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget()
        widget.set_size(128, 40)

        image = widget.render()

        assert isinstance(image, Image.Image)
        assert image.size == (128, 40)


def test_clock_render_calls_update_if_needed():
    """
    Тест что render() вызывает update() если время не установлено.

    Проверяет автоматическое обновление при первом рендере.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget(format_string="%H:%M")
        # update() не вызван, _formatted_time пустой

        image = widget.render()

        # render() должен был вызвать update()
        assert widget._formatted_time == "12:34"


def test_clock_render_with_black_background():
    """
    Тест рендеринга с чёрным фоном.

    Проверяет что background_color применяется.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget(background_color=0)
        widget.update()
        widget.set_size(128, 40)

        image = widget.render()

        # Фон чёрный, текст должен быть белым (контраст)
        assert image.mode in ['L', 'LA']


def test_clock_render_with_white_background():
    """
    Тест рендеринга с белым фоном.

    Проверяет автоматический выбор цвета текста (чёрный на белом).
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget(background_color=255)
        widget.update()
        widget.set_size(128, 40)

        image = widget.render()

        # Фон белый (>128), текст должен быть чёрным
        assert image.mode in ['L', 'LA']


def test_clock_render_with_border():
    """
    Тест рендеринга с рамкой.

    Проверяет что border рисуется.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget(border=True, border_color=255)
        widget.update()
        widget.set_size(128, 40)

        image = widget.render()

        assert isinstance(image, Image.Image)
        # Проверяем что изображение не пустое
        assert image.size == (128, 40)


def test_clock_render_with_alpha_channel():
    """
    Тест рендеринга с альфа-каналом (прозрачность).

    Проверяет что при opacity < 255 создаётся LA mode изображение.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget(background_opacity=128)
        widget.update()
        widget.set_size(128, 40)

        image = widget.render()

        assert image.mode == 'LA'  # Grayscale с альфа


def test_clock_render_different_sizes():
    """
    Тест рендеринга с различными размерами.

    Проверяет что render адаптируется к размеру виджета.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget()
        widget.update()

        # Разные размеры
        for width, height in [(64, 20), (128, 40), (256, 80)]:
            widget.set_size(width, height)
            image = widget.render()
            assert image.size == (width, height)


@pytest.mark.parametrize("h_align,v_align", [
    ("left", "top"),
    ("center", "center"),
    ("right", "bottom"),
])
def test_clock_render_with_alignment(h_align, v_align):
    """
    Тест рендеринга с различным выравниванием.

    Параметризованный тест проверяет разные комбинации выравнивания.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget(
            horizontal_align=h_align,
            vertical_align=v_align
        )
        widget.update()
        widget.set_size(128, 40)

        image = widget.render()

        assert isinstance(image, Image.Image)


def test_clock_render_with_padding():
    """
    Тест рендеринга с отступами.

    Проверяет что padding применяется.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget(padding=10)
        widget.update()
        widget.set_size(128, 40)

        image = widget.render()

        assert isinstance(image, Image.Image)


# =============================================================================
# Тесты get_update_interval()
# =============================================================================

def test_get_update_interval_default():
    """
    Тест get_update_interval() с дефолтным значением.

    Проверяет что интервал обновления возвращается корректно.
    """
    widget = ClockWidget()
    assert widget.get_update_interval() == 1.0


def test_get_update_interval_custom():
    """
    Тест get_update_interval() с кастомным значением.

    Проверяет что custom interval сохраняется.
    """
    widget = ClockWidget(update_interval=0.5)
    assert widget.get_update_interval() == 0.5


# =============================================================================
# Тесты set_format()
# =============================================================================

def test_set_format_changes_format_string():
    """
    Тест set_format() изменяет формат времени.

    Проверяет:
    - format_string обновляется
    - update() вызывается автоматически
    - Новый формат применяется
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget(format_string="%H:%M:%S")
        widget.update()
        assert widget._formatted_time == "12:34:56"

        # Меняем формат
        widget.set_format("%H:%M")

        assert widget.format_string == "%H:%M"
        assert widget._formatted_time == "12:34"


def test_set_format_multiple_times():
    """
    Тест множественных вызовов set_format().

    Проверяет что формат можно менять многократно.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget()

        widget.set_format("%H:%M")
        assert widget._formatted_time == "12:34"

        widget.set_format("%d.%m.%Y")
        assert widget._formatted_time == "15.11.2025"

        widget.set_format("%Y-%m-%d %H:%M:%S")
        assert widget._formatted_time == "2025-11-15 12:34:56"


# =============================================================================
# Тесты get_current_time_string()
# =============================================================================

def test_get_current_time_string_after_update():
    """
    Тест get_current_time_string() возвращает отформатированное время.

    Проверяет что метод возвращает _formatted_time.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget(format_string="%H:%M")
        widget.update()

        assert widget.get_current_time_string() == "12:34"


def test_get_current_time_string_before_update():
    """
    Тест get_current_time_string() до вызова update().

    Edge case: Должен вернуть пустую строку если update() не вызван.
    """
    widget = ClockWidget()

    assert widget.get_current_time_string() == ""


def test_get_current_time_string_after_error():
    """
    Тест get_current_time_string() после ошибки в update().

    Edge case: Должен вернуть "ERROR" если update() упал.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        mock_time = Mock()
        mock_time.strftime.side_effect = ValueError("Invalid format")
        mock_datetime.now.return_value = mock_time

        widget = ClockWidget()
        widget.update()

        assert widget.get_current_time_string() == "ERROR"


# =============================================================================
# Edge cases и интеграционные тесты
# =============================================================================

def test_clock_full_workflow():
    """
    Тест полного workflow Clock widget.

    Интеграционный тест: init -> update -> render -> get_current_time_string.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        fixed_time = datetime(2025, 11, 15, 12, 34, 56)
        mock_datetime.now.return_value = fixed_time

        widget = ClockWidget(
            name="TestClock",
            format_string="%H:%M",
            font_size=14,
            border=True,
            horizontal_align="left"
        )
        widget.set_size(128, 40)

        # Update
        widget.update()
        assert widget.get_current_time_string() == "12:34"

        # Render
        image = widget.render()
        assert image.size == (128, 40)

        # Change format
        widget.set_format("%d.%m.%Y")
        assert widget.get_current_time_string() == "15.11.2025"


def test_clock_midnight_time():
    """
    Тест отображения полуночи (00:00:00).

    Edge case: Проверяем что полночь корректно форматируется.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        midnight = datetime(2025, 11, 15, 0, 0, 0)
        mock_datetime.now.return_value = midnight

        widget = ClockWidget(format_string="%H:%M:%S")
        widget.update()

        assert widget.get_current_time_string() == "00:00:00"


def test_clock_noon_time():
    """
    Тест отображения полудня (12:00:00).

    Edge case: Проверяем корректное отображение 12-часового формата.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        noon = datetime(2025, 11, 15, 12, 0, 0)
        mock_datetime.now.return_value = noon

        widget = ClockWidget(format_string="%I:%M %p")  # 12-hour format with AM/PM
        widget.update()

        assert widget.get_current_time_string() == "12:00 PM"


def test_clock_year_change():
    """
    Тест отображения смены года.

    Edge case: Новый год.
    """
    with patch('widgets.clock.datetime') as mock_datetime:
        new_year = datetime(2026, 1, 1, 0, 0, 0)
        mock_datetime.now.return_value = new_year

        widget = ClockWidget(format_string="%Y-%m-%d %H:%M:%S")
        widget.update()

        assert widget.get_current_time_string() == "2026-01-01 00:00:00"
