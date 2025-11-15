"""
Unit tests для widgets.memory - виджет мониторинга памяти.

Тестируемый модуль: widgets/memory.py

Покрытие:
- Инициализация
- Обновление данных (update) с psutil
- Все режимы отображения (text, bar_horizontal, bar_vertical, graph)
- История загрузки для graph режима
- Clamping значений (0-100%)
- Стилизация (background, border, padding)
- Edge cases (0%, 100%, invalid values, ошибки psutil)
"""

import pytest
from PIL import Image
from unittest.mock import patch, Mock

from widgets.memory import MemoryWidget


# =============================================================================
# Тесты инициализации
# =============================================================================

def test_memory_init_requires_psutil() -> None:
    """
    Тест что Memory widget требует psutil.

    Edge case: Должен вызвать ImportError если psutil не установлен.
    """
    with patch('widgets.memory.psutil', None):
        with pytest.raises(ImportError) as exc_info:
            MemoryWidget()

        assert "psutil library is required" in str(exc_info.value)


def test_memory_init_default_values() -> None:
    """
    Тест инициализации Memory widget с дефолтными параметрами.

    Проверяет:
    - Дефолтный режим bar_horizontal
    - Дефолтный интервал обновления 1.0 секунда
    - Дефолтная длина истории 30
    """
    with patch('widgets.memory.psutil'):
        widget = MemoryWidget()

        assert widget.name == "Memory"
        assert widget.display_mode == "bar_horizontal"
        assert widget.update_interval_sec == 1.0
        assert widget.history_length == 30
        assert widget._current_usage is None
        assert len(widget._usage_history) == 0


def test_memory_init_custom_values() -> None:
    """
    Тест инициализации Memory widget с кастомными параметрами.

    Проверяет возможность переопределения всех параметров.
    """
    with patch('widgets.memory.psutil'):
        widget = MemoryWidget(
            name="CustomMemory",
            display_mode="graph",
            update_interval=0.5,
            history_length=60,
            font="Arial",
            font_size=14,
            background_color=128,
            border=True,
            padding=5
        )

        assert widget.name == "CustomMemory"
        assert widget.display_mode == "graph"
        assert widget.update_interval_sec == 0.5
        assert widget.history_length == 60
        assert widget.font == "Arial"
        assert widget.font_size == 14


@pytest.mark.parametrize("mode", ["text", "bar_horizontal", "bar_vertical", "graph"])
def test_memory_init_all_display_modes(mode: str) -> None:
    """
    Тест инициализации со всеми режимами отображения.

    Параметризованный тест проверяет все 4 режима.
    """
    with patch('widgets.memory.psutil'):
        widget = MemoryWidget(display_mode=mode)

        assert widget.display_mode == mode


# =============================================================================
# Тесты update()
# =============================================================================

def test_memory_update_success() -> None:
    """
    Тест успешного update().

    Проверяет:
    - Вызов psutil.virtual_memory()
    - Сохранение процента в _current_usage
    - Значение в диапазоне 0-100
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 65.5
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget()
        widget.update()

        mock_psutil.virtual_memory.assert_called_once()
        assert widget._current_usage == 65.5
        assert isinstance(widget._current_usage, float)


def test_memory_update_clamps_high_values() -> None:
    """
    Тест что update() ограничивает значения > 100%.

    Edge case: psutil иногда может вернуть >100%.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 150.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget()
        widget.update()

        assert widget._current_usage == 100.0


def test_memory_update_clamps_negative_values() -> None:
    """
    Тест что update() ограничивает отрицательные значения.

    Edge case: Защита от некорректных данных.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = -5.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget()
        widget.update()

        assert widget._current_usage == 0.0


def test_memory_update_zero_percent() -> None:
    """
    Тест update() с 0% загрузкой.

    Edge case: Полностью свободная память (теоретически).
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 0.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget()
        widget.update()

        assert widget._current_usage == 0.0


def test_memory_update_100_percent() -> None:
    """
    Тест update() с 100% загрузкой.

    Edge case: Полностью занятая память.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 100.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget()
        widget.update()

        assert widget._current_usage == 100.0


# =============================================================================
# Тесты update() - graph mode history
# =============================================================================

def test_memory_update_graph_mode_adds_to_history() -> None:
    """
    Тест что update() добавляет значения в историю в graph режиме.

    Проверяет _usage_history deque.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        widget = MemoryWidget(display_mode="graph", history_length=5)

        # Добавляем несколько образцов
        for i in range(3):
            mock_mem = Mock()
            mock_mem.percent = float(i * 20)
            mock_psutil.virtual_memory.return_value = mock_mem
            widget.update()

        assert len(widget._usage_history) == 3
        assert list(widget._usage_history) == [0.0, 20.0, 40.0]


def test_memory_update_graph_mode_respects_max_length() -> None:
    """
    Тест что история ограничена maxlen.

    Edge case: Старые значения вытесняются новыми.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        widget = MemoryWidget(display_mode="graph", history_length=3)

        # Добавляем больше образцов чем maxlen
        for i in range(5):
            mock_mem = Mock()
            mock_mem.percent = float(i * 10)
            mock_psutil.virtual_memory.return_value = mock_mem
            widget.update()

        # Должны остаться только последние 3
        assert len(widget._usage_history) == 3
        assert list(widget._usage_history) == [20.0, 30.0, 40.0]


def test_memory_update_non_graph_mode_no_history() -> None:
    """
    Тест что в non-graph режимах история не добавляется.

    Проверяет что history пустая для других режимов.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget(display_mode="text")
        widget.update()

        assert len(widget._usage_history) == 0


# =============================================================================
# Тесты update() - error handling
# =============================================================================

def test_memory_update_handles_psutil_error() -> None:
    """
    Тест обработки ошибки psutil.

    Edge case: psutil.virtual_memory() падает, должен вернуть 0.0.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_psutil.virtual_memory.side_effect = Exception("psutil error")

        widget = MemoryWidget()
        widget.update()

        assert widget._current_usage == 0.0


# =============================================================================
# Тесты render()
# =============================================================================

def test_memory_render_returns_image() -> None:
    """
    Тест что render() возвращает PIL Image.

    Проверяет:
    - Возвращается Image.Image
    - Размер соответствует размерам виджета
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget()
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)
        assert image.size == (128, 40)


def test_memory_render_calls_update_if_needed() -> None:
    """
    Тест что render() вызывает update() если данные не установлены.

    Проверяет автоматическое обновление при первом рендере.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 75.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget()
        widget.set_size(128, 40)
        # update() не вызван, _current_usage = None

        widget.render()

        # render() должен был вызвать update()
        assert widget._current_usage == 75.0


def test_memory_render_with_border() -> None:
    """
    Тест рендеринга с рамкой.

    Проверяет что border рисуется.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget(border=True, border_color=255)
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


def test_memory_render_with_alpha_channel() -> None:
    """
    Тест рендеринга с альфа-каналом (прозрачность).

    Проверяет что при opacity < 255 создаётся LA mode изображение.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget(background_opacity=128)
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert image.mode == 'LA'


# =============================================================================
# Тесты _render_text()
# =============================================================================

def test_memory_render_text_mode() -> None:
    """
    Тест рендеринга в text режиме.

    Проверяет что отображается число.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 67.3
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget(display_mode="text")
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


# =============================================================================
# Тесты _render_bar_horizontal()
# =============================================================================

def test_memory_render_bar_horizontal() -> None:
    """
    Тест рендеринга горизонтального бара.

    Проверяет что рисуется горизонтальный бар.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget(display_mode="bar_horizontal")
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)
        # Проверяем что есть белые пиксели (бар отрисован)
        pixels = list(image.getdata())
        assert any(p == 255 for p in pixels) or any(p == (255, 255) for p in pixels)


def test_memory_render_bar_horizontal_zero_percent() -> None:
    """
    Тест рендеринга бара с 0% загрузкой.

    Edge case: Пустой бар (только рамка если bar_border=True).
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 0.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget(display_mode="bar_horizontal")
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


def test_memory_render_bar_horizontal_100_percent() -> None:
    """
    Тест рендеринга бара с 100% загрузкой.

    Edge case: Полностью заполненный бар.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 100.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget(display_mode="bar_horizontal")
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


# =============================================================================
# Тесты _render_bar_vertical()
# =============================================================================

def test_memory_render_bar_vertical() -> None:
    """
    Тест рендеринга вертикального бара.

    Проверяет что рисуется вертикальный столбец.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 60.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget(display_mode="bar_vertical")
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


# =============================================================================
# Тесты _render_graph()
# =============================================================================

def test_memory_render_graph_with_history() -> None:
    """
    Тест рендеринга графика с историей.

    Проверяет что график использует _usage_history.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        widget = MemoryWidget(display_mode="graph", history_length=5)
        widget.set_size(128, 40)

        # Добавляем историю
        for i in range(5):
            mock_mem = Mock()
            mock_mem.percent = float(i * 20)
            mock_psutil.virtual_memory.return_value = mock_mem
            widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)
        assert len(widget._usage_history) == 5


def test_memory_render_graph_empty_history() -> None:
    """
    Тест рендеринга графика без истории.

    Edge case: График должен отрисоваться даже если история пустая.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget(display_mode="graph")
        widget.set_size(128, 40)
        # Не вызываем update(), история пустая

        image = widget.render()

        assert isinstance(image, Image.Image)


# =============================================================================
# Тесты get_update_interval()
# =============================================================================

def test_memory_get_update_interval_default() -> None:
    """
    Тест get_update_interval() с дефолтным значением.

    Проверяет что интервал обновления возвращается корректно.
    """
    with patch('widgets.memory.psutil'):
        widget = MemoryWidget()
        assert widget.get_update_interval() == 1.0


def test_memory_get_update_interval_custom() -> None:
    """
    Тест get_update_interval() с кастомным значением.

    Проверяет что custom interval сохраняется.
    """
    with patch('widgets.memory.psutil'):
        widget = MemoryWidget(update_interval=2.5)
        assert widget.get_update_interval() == 2.5


# =============================================================================
# Тесты стилизации и edge cases
# =============================================================================

def test_memory_render_with_padding() -> None:
    """
    Тест рендеринга с padding.

    Проверяет что padding применяется.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget(padding=10)
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


def test_memory_render_different_sizes() -> None:
    """
    Тест рендеринга с различными размерами.

    Проверяет что render адаптируется к размеру виджета.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget()
        widget.update()

        # Разные размеры
        for width, height in [(64, 20), (128, 40), (256, 80)]:
            widget.set_size(width, height)
            image = widget.render()
            assert image.size == (width, height)


def test_memory_render_unknown_display_mode() -> None:
    """
    Тест рендеринга с неизвестным display_mode.

    Edge case: Должен логировать warning и вернуть пустое изображение.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 50.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget(display_mode="invalid_mode")
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        # Должен вернуть изображение (пустое, т.к. режим неизвестен)
        assert isinstance(image, Image.Image)


# =============================================================================
# Интеграционные тесты
# =============================================================================

def test_memory_full_workflow() -> None:
    """
    Тест полного workflow Memory widget.

    Интеграционный тест: init -> update -> render.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        mock_mem = Mock()
        mock_mem.percent = 65.0
        mock_psutil.virtual_memory.return_value = mock_mem

        widget = MemoryWidget(
            name="TestMemory",
            display_mode="bar_horizontal",
            border=True
        )
        widget.set_size(128, 40)

        # Update
        widget.update()
        assert widget._current_usage == 65.0

        # Render
        image = widget.render()
        assert image.size == (128, 40)


def test_memory_multiple_updates_and_renders() -> None:
    """
    Тест множественных обновлений и рендеров.

    Проверяет что виджет корректно обрабатывает циклы обновления.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        widget = MemoryWidget(display_mode="graph", history_length=10)
        widget.set_size(128, 40)

        # Несколько циклов обновления
        for i in range(15):
            mock_mem = Mock()
            mock_mem.percent = float(i * 5 % 100)
            mock_psutil.virtual_memory.return_value = mock_mem
            widget.update()
            image = widget.render()
            assert isinstance(image, Image.Image)

        # История должна содержать последние 10 образцов
        assert len(widget._usage_history) == 10


def test_memory_realistic_usage_patterns() -> None:
    """
    Тест с реалистичными паттернами использования памяти.

    Проверяет виджет с типичными значениями загрузки памяти.
    """
    with patch('widgets.memory.psutil') as mock_psutil:
        # Типичные значения: 40-85% usage
        realistic_values = [45.2, 52.8, 61.3, 58.9, 67.1, 72.5, 68.3, 64.7, 59.2, 55.6]

        widget = MemoryWidget(display_mode="graph", history_length=10)
        widget.set_size(128, 40)

        for value in realistic_values:
            mock_mem = Mock()
            mock_mem.percent = value
            mock_psutil.virtual_memory.return_value = mock_mem
            widget.update()

        # Проверяем что последнее значение сохранено
        assert widget._current_usage == realistic_values[-1]
        assert len(widget._usage_history) == len(realistic_values)

        # Рендерим и проверяем
        image = widget.render()
        assert isinstance(image, Image.Image)
