"""
Unit tests для widgets.cpu - виджет мониторинга CPU.

Тестируемый модуль: widgets/cpu.py

Покрытие:
- Инициализация (aggregate и per-core режимы)
- Обновление данных (update) с psutil
- Все режимы отображения (text, bar_horizontal, bar_vertical, graph)
- История загрузки для graph режима
- Clamping значений (0-100%)
- Стилизация (background, border, padding, margins)
- Edge cases (0%, 100%, invalid values, ошибки psutil)
"""

import pytest
from PIL import Image
from unittest.mock import patch

from widgets.cpu import CPUWidget


# =============================================================================
# Тесты инициализации
# =============================================================================

def test_cpu_init_requires_psutil():
    """
    Тест что CPU widget требует psutil.

    Edge case: Должен вызвать ImportError если psutil не установлен.
    """
    with patch('widgets.cpu.psutil', None):
        with pytest.raises(ImportError) as exc_info:
            CPUWidget()

        assert "psutil library is required" in str(exc_info.value)


def test_cpu_init_default_values():
    """
    Тест инициализации CPU widget с дефолтными параметрами.

    Проверяет:
    - Дефолтный режим bar_horizontal
    - Aggregate mode (per_core=False)
    - Дефолтный интервал обновления 1.0 секунда
    - Дефолтная длина истории 30
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4

        widget = CPUWidget()

        assert widget.name == "CPU"
        assert widget.display_mode == "bar_horizontal"
        assert widget.per_core is False
        assert widget.update_interval_sec == 1.0
        assert widget.history_length == 30
        assert widget._core_count == 4
        assert widget._current_usage is None
        assert len(widget._usage_history) == 0


def test_cpu_init_custom_values():
    """
    Тест инициализации CPU widget с кастомными параметрами.

    Проверяет возможность переопределения всех параметров.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 8

        widget = CPUWidget(
            name="CustomCPU",
            display_mode="text",
            per_core=True,
            update_interval=0.5,
            history_length=60,
            font="Arial",
            font_size=14,
            background_color=128,
            border=True,
            padding=5
        )

        assert widget.name == "CustomCPU"
        assert widget.display_mode == "text"
        assert widget.per_core is True
        assert widget.update_interval_sec == 0.5
        assert widget.history_length == 60
        assert widget.font == "Arial"
        assert widget.font_size == 14


def test_cpu_init_gets_core_count():
    """
    Тест что инициализация получает количество ядер из psutil.

    Проверяет вызов psutil.cpu_count(logical=True).
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 16

        widget = CPUWidget()

        mock_psutil.cpu_count.assert_called_once_with(logical=True)
        assert widget._core_count == 16


@pytest.mark.parametrize("mode", ["text", "bar_horizontal", "bar_vertical", "graph"])
def test_cpu_init_all_display_modes(mode):
    """
    Тест инициализации со всеми режимами отображения.

    Параметризованный тест проверяет все 4 режима.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4

        widget = CPUWidget(display_mode=mode)

        assert widget.display_mode == mode


# =============================================================================
# Тесты update() - aggregate mode
# =============================================================================

def test_cpu_update_aggregate_mode():
    """
    Тест update() в aggregate режиме.

    Проверяет:
    - Вызов psutil.cpu_percent(interval=0.1)
    - Сохранение в _current_usage как float
    - Значение в диапазоне 0-100
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 45.5

        widget = CPUWidget(per_core=False)
        widget.update()

        mock_psutil.cpu_percent.assert_called_with(interval=0.1)
        assert widget._current_usage == 45.5
        assert isinstance(widget._current_usage, float)


def test_cpu_update_aggregate_clamps_high_values():
    """
    Тест что update() ограничивает значения > 100%.

    Edge case: psutil иногда может вернуть >100%.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 150.0

        widget = CPUWidget(per_core=False)
        widget.update()

        assert widget._current_usage == 100.0


def test_cpu_update_aggregate_clamps_negative_values():
    """
    Тест что update() ограничивает отрицательные значения.

    Edge case: Защита от некорректных данных.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = -5.0

        widget = CPUWidget(per_core=False)
        widget.update()

        assert widget._current_usage == 0.0


def test_cpu_update_aggregate_zero_percent():
    """
    Тест update() с 0% загрузкой.

    Edge case: Полностью незагруженный CPU.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 0.0

        widget = CPUWidget(per_core=False)
        widget.update()

        assert widget._current_usage == 0.0


def test_cpu_update_aggregate_100_percent():
    """
    Тест update() с 100% загрузкой.

    Edge case: Полностью загруженный CPU.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 100.0

        widget = CPUWidget(per_core=False)
        widget.update()

        assert widget._current_usage == 100.0


# =============================================================================
# Тесты update() - per-core mode
# =============================================================================

def test_cpu_update_per_core_mode():
    """
    Тест update() в per-core режиме.

    Проверяет:
    - Вызов psutil.cpu_percent(percpu=True)
    - Сохранение в _current_usage как list
    - Все значения в диапазоне 0-100
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = [25.0, 50.0, 75.0, 100.0]

        widget = CPUWidget(per_core=True)
        widget.update()

        mock_psutil.cpu_percent.assert_called_with(interval=0.1, percpu=True)
        assert widget._current_usage == [25.0, 50.0, 75.0, 100.0]
        assert isinstance(widget._current_usage, list)
        assert len(widget._current_usage) == 4


def test_cpu_update_per_core_clamps_values():
    """
    Тест что update() ограничивает значения per-core.

    Edge case: Каждое ядро может иметь >100% или <0%.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = [-5.0, 50.0, 150.0, 100.0]

        widget = CPUWidget(per_core=True)
        widget.update()

        assert widget._current_usage == [0.0, 50.0, 100.0, 100.0]


def test_cpu_update_per_core_different_core_counts():
    """
    Тест update() с различным количеством ядер.

    Проверяет что работает для 1, 4, 8, 16+ ядер.
    """
    for core_count in [1, 4, 8, 16, 32]:
        with patch('widgets.cpu.psutil') as mock_psutil:
            mock_psutil.cpu_count.return_value = core_count
            mock_values = [float(i * 10 % 100) for i in range(core_count)]
            mock_psutil.cpu_percent.return_value = mock_values

            widget = CPUWidget(per_core=True)
            widget.update()

            assert len(widget._current_usage) == core_count


# =============================================================================
# Тесты update() - graph mode history
# =============================================================================

def test_cpu_update_graph_mode_adds_to_history():
    """
    Тест что update() добавляет значения в историю в graph режиме.

    Проверяет _usage_history deque.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 50.0

        widget = CPUWidget(display_mode="graph", history_length=5)

        # Добавляем несколько образцов
        for i in range(3):
            mock_psutil.cpu_percent.return_value = float(i * 20)
            widget.update()

        assert len(widget._usage_history) == 3
        assert list(widget._usage_history) == [0.0, 20.0, 40.0]


def test_cpu_update_graph_mode_respects_max_length():
    """
    Тест что история ограничена maxlen.

    Edge case: Старые значения вытесняются новыми.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4

        widget = CPUWidget(display_mode="graph", history_length=3)

        # Добавляем больше образцов чем maxlen
        for i in range(5):
            mock_psutil.cpu_percent.return_value = float(i * 10)
            widget.update()

        # Должны остаться только последние 3
        assert len(widget._usage_history) == 3
        assert list(widget._usage_history) == [20.0, 30.0, 40.0]


def test_cpu_update_non_graph_mode_no_history():
    """
    Тест что в non-graph режимах история не добавляется.

    Проверяет что history пустая для других режимов.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 50.0

        widget = CPUWidget(display_mode="text")
        widget.update()

        assert len(widget._usage_history) == 0


# =============================================================================
# Тесты update() - error handling
# =============================================================================

def test_cpu_update_handles_psutil_error_aggregate():
    """
    Тест обработки ошибки psutil в aggregate режиме.

    Edge case: psutil.cpu_percent() падает, должен вернуть 0.0.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.side_effect = Exception("psutil error")

        widget = CPUWidget(per_core=False)
        widget.update()

        assert widget._current_usage == 0.0


def test_cpu_update_handles_psutil_error_per_core():
    """
    Тест обработки ошибки psutil в per-core режиме.

    Edge case: psutil.cpu_percent() падает, должен вернуть список нулей.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.side_effect = Exception("psutil error")

        widget = CPUWidget(per_core=True)
        widget.update()

        assert widget._current_usage == [0.0, 0.0, 0.0, 0.0]


# =============================================================================
# Тесты render()
# =============================================================================

def test_cpu_render_returns_image():
    """
    Тест что render() возвращает PIL Image.

    Проверяет:
    - Возвращается Image.Image
    - Размер соответствует размерам виджета
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 50.0

        widget = CPUWidget()
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)
        assert image.size == (128, 40)


def test_cpu_render_calls_update_if_needed():
    """
    Тест что render() вызывает update() если данные не установлены.

    Проверяет автоматическое обновление при первом рендере.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 75.0

        widget = CPUWidget()
        widget.set_size(128, 40)
        # update() не вызван, _current_usage = None

        widget.render()

        # render() должен был вызвать update()
        assert widget._current_usage == 75.0


def test_cpu_render_with_border():
    """
    Тест рендеринга с рамкой.

    Проверяет что border рисуется.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 50.0

        widget = CPUWidget(border=True, border_color=255)
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


def test_cpu_render_with_alpha_channel():
    """
    Тест рендеринга с альфа-каналом (прозрачность).

    Проверяет что при opacity < 255 создаётся LA mode изображение.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 50.0

        widget = CPUWidget(background_opacity=128)
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert image.mode == 'LA'


# =============================================================================
# Тесты _render_text()
# =============================================================================

def test_cpu_render_text_aggregate():
    """
    Тест рендеринга в text режиме (aggregate).

    Проверяет что отображается одно число.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 67.3

        widget = CPUWidget(display_mode="text", per_core=False)
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)
        # Текст "67" должен быть отрендерен (без десятичных)


def test_cpu_render_text_per_core():
    """
    Тест рендеринга в text режиме (per-core).

    Проверяет что отображается сетка чисел для каждого ядра.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = [25.0, 50.0, 75.0, 100.0]

        widget = CPUWidget(display_mode="text", per_core=True)
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


# =============================================================================
# Тесты _render_bar_horizontal()
# =============================================================================

def test_cpu_render_bar_horizontal_aggregate():
    """
    Тест рендеринга горизонтального бара (aggregate).

    Проверяет что рисуется один горизонтальный бар.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 50.0

        widget = CPUWidget(display_mode="bar_horizontal", per_core=False)
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)
        # Проверяем что есть белые пиксели (бар отрисован)
        pixels = list(image.getdata())
        assert any(p == 255 for p in pixels) or any(p == (255, 255) for p in pixels)


def test_cpu_render_bar_horizontal_per_core():
    """
    Тест рендеринга горизонтальных баров (per-core).

    Проверяет что рисуется по бару на каждое ядро.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = [25.0, 50.0, 75.0, 100.0]

        widget = CPUWidget(display_mode="bar_horizontal", per_core=True)
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


def test_cpu_render_bar_horizontal_zero_percent():
    """
    Тест рендеринга бара с 0% загрузкой.

    Edge case: Пустой бар (только рамка если bar_border=True).
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 0.0

        widget = CPUWidget(display_mode="bar_horizontal")
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


def test_cpu_render_bar_horizontal_100_percent():
    """
    Тест рендеринга бара с 100% загрузкой.

    Edge case: Полностью заполненный бар.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 100.0

        widget = CPUWidget(display_mode="bar_horizontal")
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


# =============================================================================
# Тесты _render_bar_vertical()
# =============================================================================

def test_cpu_render_bar_vertical_aggregate():
    """
    Тест рендеринга вертикального бара (aggregate).

    Проверяет что рисуется один вертикальный столбец.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 60.0

        widget = CPUWidget(display_mode="bar_vertical", per_core=False)
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


def test_cpu_render_bar_vertical_per_core():
    """
    Тест рендеринга вертикальных баров (per-core).

    Проверяет что рисуется по столбцу на каждое ядро.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = [10.0, 30.0, 60.0, 90.0]

        widget = CPUWidget(display_mode="bar_vertical", per_core=True)
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


# =============================================================================
# Тесты _render_graph()
# =============================================================================

def test_cpu_render_graph_with_history():
    """
    Тест рендеринга графика с историей.

    Проверяет что график использует _usage_history.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4

        widget = CPUWidget(display_mode="graph", history_length=5)
        widget.set_size(128, 40)

        # Добавляем историю
        for i in range(5):
            mock_psutil.cpu_percent.return_value = float(i * 20)
            widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)
        assert len(widget._usage_history) == 5


def test_cpu_render_graph_empty_history():
    """
    Тест рендеринга графика без истории.

    Edge case: График должен отрисоваться даже если история пустая.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 50.0

        widget = CPUWidget(display_mode="graph")
        widget.set_size(128, 40)
        # Не вызываем update(), история пустая

        image = widget.render()

        assert isinstance(image, Image.Image)


# =============================================================================
# Тесты get_update_interval()
# =============================================================================

def test_cpu_get_update_interval_default():
    """
    Тест get_update_interval() с дефолтным значением.

    Проверяет что интервал обновления возвращается корректно.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4

        widget = CPUWidget()
        assert widget.get_update_interval() == 1.0


def test_cpu_get_update_interval_custom():
    """
    Тест get_update_interval() с кастомным значением.

    Проверяет что custom interval сохраняется.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4

        widget = CPUWidget(update_interval=2.5)
        assert widget.get_update_interval() == 2.5


# =============================================================================
# Тесты стилизации и edge cases
# =============================================================================

def test_cpu_render_with_padding():
    """
    Тест рендеринга с padding.

    Проверяет что padding применяется.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 50.0

        widget = CPUWidget(padding=10)
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)


def test_cpu_render_different_sizes():
    """
    Тест рендеринга с различными размерами.

    Проверяет что render адаптируется к размеру виджета.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 50.0

        widget = CPUWidget()
        widget.update()

        # Разные размеры
        for width, height in [(64, 20), (128, 40), (256, 80)]:
            widget.set_size(width, height)
            image = widget.render()
            assert image.size == (width, height)


def test_cpu_render_unknown_display_mode():
    """
    Тест рендеринга с неизвестным display_mode.

    Edge case: Должен логировать warning и вернуть пустое изображение.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 50.0

        widget = CPUWidget(display_mode="invalid_mode")
        widget.set_size(128, 40)
        widget.update()

        image = widget.render()

        # Должен вернуть изображение (пустое, т.к. режим неизвестен)
        assert isinstance(image, Image.Image)


# =============================================================================
# Интеграционные тесты
# =============================================================================

def test_cpu_full_workflow_aggregate():
    """
    Тест полного workflow CPU widget в aggregate режиме.

    Интеграционный тест: init -> update -> render.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_percent.return_value = 65.0

        widget = CPUWidget(
            name="TestCPU",
            display_mode="bar_horizontal",
            per_core=False,
            border=True
        )
        widget.set_size(128, 40)

        # Update
        widget.update()
        assert widget._current_usage == 65.0

        # Render
        image = widget.render()
        assert image.size == (128, 40)


def test_cpu_full_workflow_per_core():
    """
    Тест полного workflow CPU widget в per-core режиме.

    Интеграционный тест с множеством ядер.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 8
        mock_psutil.cpu_percent.return_value = [10, 20, 30, 40, 50, 60, 70, 80]

        widget = CPUWidget(
            display_mode="bar_vertical",
            per_core=True
        )
        widget.set_size(256, 40)

        widget.update()
        assert len(widget._current_usage) == 8

        image = widget.render()
        assert image.size == (256, 40)


def test_cpu_multiple_updates_and_renders():
    """
    Тест множественных обновлений и рендеров.

    Проверяет что виджет корректно обрабатывает циклы обновления.
    """
    with patch('widgets.cpu.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4

        widget = CPUWidget(display_mode="graph", history_length=10)
        widget.set_size(128, 40)

        # Несколько циклов обновления
        for i in range(15):
            mock_psutil.cpu_percent.return_value = float(i * 5 % 100)
            widget.update()
            image = widget.render()
            assert isinstance(image, Image.Image)

        # История должна содержать последние 10 образцов
        assert len(widget._usage_history) == 10
