"""
Unit tests для widgets.network - виджет мониторинга сети.

Тестируемый модуль: widgets/network.py

Покрытие:
- Инициализация и проверка наличия psutil
- Обновление данных (update) с расчётом скорости
- Проверка интерфейсов и обработка отсутствующих
- История для graph режима (RX и TX отдельно)
- Рендеринг в разных режимах (text, bar_horizontal, bar_vertical, graph)
- Форматирование скорости (bps, kbps, mbps, gbps)
- Динамическое и фиксированное масштабирование
- Edge cases и error handling
"""

import pytest
from unittest.mock import patch, Mock
from PIL import Image
from widgets.network import NetworkWidget


# =============================================================================
# Тесты инициализации
# =============================================================================

def test_network_init_requires_psutil():
    """
    Тест инициализации требует psutil.

    Edge case: Должен вызвать ImportError если psutil не установлен.
    """
    with patch('widgets.network.psutil', None):
        with pytest.raises(ImportError) as exc_info:
            NetworkWidget()

        assert "psutil library is required" in str(exc_info.value)


def test_network_init_default_values():
    """
    Тест инициализации с дефолтными значениями.

    Проверяет:
    - Имя виджета по умолчанию
    - Режим отображения по умолчанию (bar_horizontal)
    - Интерфейс по умолчанию (eth0)
    - Интервал обновления
    - История пустая
    """
    with patch('widgets.network.psutil') as mock_psutil:
        mock_psutil.cpu_count.return_value = 4

        widget = NetworkWidget()

        assert widget.name == "Network"
        assert widget.display_mode == "bar_horizontal"
        assert widget.interface == "eth0"
        assert widget.update_interval_sec == 1.0
        assert widget.history_length == 30
        assert widget._current_rx_speed is None
        assert widget._current_tx_speed is None
        assert len(widget._rx_history) == 0
        assert len(widget._tx_history) == 0


def test_network_init_custom_values():
    """
    Тест инициализации с кастомными значениями.

    Проверяет корректную установку всех параметров.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(
            name="CustomNet",
            interface="wlan0",
            display_mode="graph",
            update_interval=0.5,
            history_length=60,
            max_speed_mbps=50.0,
            speed_unit="mbps",
            rx_color=200,
            tx_color=100
        )

        assert widget.name == "CustomNet"
        assert widget.interface == "wlan0"
        assert widget.display_mode == "graph"
        assert widget.update_interval_sec == 0.5
        assert widget.history_length == 60
        assert widget.max_speed_mbps == 50.0
        assert widget.speed_unit == "mbps"
        assert widget.rx_color == 200
        assert widget.tx_color == 100


@pytest.mark.parametrize("mode", ["text", "bar_horizontal", "bar_vertical", "graph"])
def test_network_init_all_display_modes(mode):
    """
    Параметризованный тест проверяет все 4 режима отображения.

    Проверяет:
    - text: Текстовое отображение RX/TX
    - bar_horizontal: Две горизонтальные полосы
    - bar_vertical: Два вертикальных столбца
    - graph: Два наложенных графика
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(display_mode=mode)
        assert widget.display_mode == mode


def test_network_init_dynamic_scaling():
    """
    Тест инициализации с динамическим масштабированием.

    При max_speed_mbps < 0 должен включаться dynamic_scaling.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(max_speed_mbps=-1.0)

        assert widget.dynamic_scaling is True
        assert widget.max_speed_mbps == -1.0


def test_network_init_fixed_scaling():
    """
    Тест инициализации с фиксированным масштабированием.

    При max_speed_mbps > 0 должен использоваться фиксированный масштаб.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(max_speed_mbps=100.0)

        assert widget.dynamic_scaling is False
        # 100 Mbps = 100 * 1024 * 1024 / 8 bytes/sec = 13107200 bytes/sec
        assert widget.max_speed_bytes == 100.0 * 1024 * 1024 / 8


# =============================================================================
# Тесты update()
# =============================================================================

def test_network_update_first_call_returns_zero():
    """
    Тест первого вызова update() возвращает нулевую скорость.

    Edge case: При первом вызове нет предыдущих данных, поэтому скорость = 0.
    """
    with patch('widgets.network.psutil') as mock_psutil:
        mock_stats = Mock()
        mock_stats.bytes_recv = 1000000
        mock_stats.bytes_sent = 500000
        mock_psutil.net_io_counters.return_value = {"eth0": mock_stats}

        widget = NetworkWidget(interface="eth0")
        widget.update()

        # Первый вызов должен дать 0, т.к. нет предыдущих значений
        assert widget._current_rx_speed == 0.0
        assert widget._current_tx_speed == 0.0
        # Но значения должны быть сохранены
        assert widget._prev_rx_bytes == 1000000
        assert widget._prev_tx_bytes == 500000
        assert widget._prev_time is not None


def test_network_update_calculates_speed():
    """
    Тест расчёта скорости на основе дельты байтов.

    Проверяет формулу: speed = (bytes_delta) / (time_delta)
    """
    with patch('widgets.network.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        # Первый вызов
        mock_stats1 = Mock()
        mock_stats1.bytes_recv = 1000000
        mock_stats1.bytes_sent = 500000
        mock_psutil.net_io_counters.return_value = {"eth0": mock_stats1}
        mock_time.return_value = 100.0

        widget = NetworkWidget(interface="eth0")
        widget.update()

        # Второй вызов через 1 секунду
        mock_stats2 = Mock()
        mock_stats2.bytes_recv = 1128000  # +128000 байт (128 KB)
        mock_stats2.bytes_sent = 564000   # +64000 байт (64 KB)
        mock_psutil.net_io_counters.return_value = {"eth0": mock_stats2}
        mock_time.return_value = 101.0

        widget.update()

        # Скорость = байты / секунды = 128000 / 1.0 = 128000 bytes/sec
        assert widget._current_rx_speed == 128000.0
        assert widget._current_tx_speed == 64000.0


def test_network_update_missing_interface():
    """
    Тест update() когда интерфейс не существует.

    Edge case: Должен установить скорость в 0 и залогировать ошибку один раз.
    """
    with patch('widgets.network.psutil') as mock_psutil:
        # Интерфейс eth0 не найден, доступны только wlan0
        mock_psutil.net_io_counters.return_value = {"wlan0": Mock()}

        widget = NetworkWidget(interface="eth0")
        widget.update()

        assert widget._current_rx_speed == 0.0
        assert widget._current_tx_speed == 0.0
        assert widget._warned_interface is True


def test_network_update_negative_delta_clamped():
    """
    Тест что отрицательная дельта (сброс счётчика) обрабатывается.

    Edge case: Если bytes_recv уменьшился (счётчик обнулён), скорость = 0.
    """
    with patch('widgets.network.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        # Первый вызов
        mock_stats1 = Mock()
        mock_stats1.bytes_recv = 1000000
        mock_stats1.bytes_sent = 500000
        mock_psutil.net_io_counters.return_value = {"eth0": mock_stats1}
        mock_time.return_value = 100.0

        widget = NetworkWidget(interface="eth0")
        widget.update()

        # Второй вызов - счётчик обнулён
        mock_stats2 = Mock()
        mock_stats2.bytes_recv = 100  # Меньше чем было
        mock_stats2.bytes_sent = 50
        mock_psutil.net_io_counters.return_value = {"eth0": mock_stats2}
        mock_time.return_value = 101.0

        widget.update()

        # Отрицательная дельта должна быть зажата в 0
        assert widget._current_rx_speed == 0.0
        assert widget._current_tx_speed == 0.0


def test_network_update_zero_time_delta():
    """
    Тест update() когда time_delta = 0 (мгновенный вызов).

    Edge case: Деление на 0 должно быть обработано.
    """
    with patch('widgets.network.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        # Оба вызова в одно и то же время
        mock_stats = Mock()
        mock_stats.bytes_recv = 1000000
        mock_stats.bytes_sent = 500000
        mock_psutil.net_io_counters.return_value = {"eth0": mock_stats}
        mock_time.return_value = 100.0

        widget = NetworkWidget(interface="eth0")
        widget.update()
        widget.update()  # Сразу второй раз

        # При time_delta = 0, скорость должна быть 0
        assert widget._current_rx_speed == 0.0
        assert widget._current_tx_speed == 0.0


# =============================================================================
# Тесты истории для graph режима
# =============================================================================

def test_network_update_graph_mode_adds_to_history():
    """
    Тест что в graph режиме данные добавляются в историю.

    Проверяет добавление в _rx_history и _tx_history.
    """
    with patch('widgets.network.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        widget = NetworkWidget(display_mode="graph", history_length=10, interface="eth0")

        # Первый update
        mock_stats1 = Mock()
        mock_stats1.bytes_recv = 1000000
        mock_stats1.bytes_sent = 500000
        mock_psutil.net_io_counters.return_value = {"eth0": mock_stats1}
        mock_time.return_value = 100.0
        widget.update()

        # Второй update
        mock_stats2 = Mock()
        mock_stats2.bytes_recv = 1128000
        mock_stats2.bytes_sent = 564000
        mock_psutil.net_io_counters.return_value = {"eth0": mock_stats2}
        mock_time.return_value = 101.0
        widget.update()

        assert len(widget._rx_history) == 2  # Оба update добавляют (первый = 0.0, второй = реальная скорость)
        assert len(widget._tx_history) == 2
        assert widget._rx_history[0] == 0.0  # Первый update
        assert widget._rx_history[1] == 128000.0  # Второй update
        assert widget._tx_history[0] == 0.0
        assert widget._tx_history[1] == 64000.0


def test_network_update_graph_mode_respects_max_length():
    """
    Тест что deque соблюдает maxlen.

    Edge case: Старые значения вытесняются новыми.
    """
    with patch('widgets.network.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        widget = NetworkWidget(display_mode="graph", history_length=3, interface="eth0")

        # Делаем 5 обновлений
        for i in range(5):
            mock_stats = Mock()
            mock_stats.bytes_recv = 1000000 + i * 100000
            mock_stats.bytes_sent = 500000 + i * 50000
            mock_psutil.net_io_counters.return_value = {"eth0": mock_stats}
            mock_time.return_value = 100.0 + i
            widget.update()

        # История должна содержать только последние 3 значения
        assert len(widget._rx_history) == 3
        assert len(widget._tx_history) == 3


def test_network_update_non_graph_mode_no_history():
    """
    Тест что в не-graph режимах история не сохраняется.

    В bar/text режимах _rx_history и _tx_history должны быть пустыми.
    """
    with patch('widgets.network.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        widget = NetworkWidget(display_mode="bar_horizontal", interface="eth0")

        # Несколько обновлений
        for i in range(3):
            mock_stats = Mock()
            mock_stats.bytes_recv = 1000000 + i * 100000
            mock_stats.bytes_sent = 500000 + i * 50000
            mock_psutil.net_io_counters.return_value = {"eth0": mock_stats}
            mock_time.return_value = 100.0 + i
            widget.update()

        assert len(widget._rx_history) == 0
        assert len(widget._tx_history) == 0


# =============================================================================
# Тесты обработки ошибок
# =============================================================================

def test_network_update_handles_psutil_error():
    """
    Тест обработки исключения при вызове psutil.

    Если psutil.net_io_counters() вызывает ошибку, должен установить скорость в 0.
    """
    with patch('widgets.network.psutil') as mock_psutil:
        mock_psutil.net_io_counters.side_effect = Exception("Network error")

        widget = NetworkWidget(interface="eth0")
        widget.update()

        assert widget._current_rx_speed == 0.0
        assert widget._current_tx_speed == 0.0


# =============================================================================
# Тесты форматирования скорости
# =============================================================================

@pytest.mark.parametrize("unit,bytes_per_sec,expected", [
    ("bps", 1000.0, "8000"),           # 1000 bytes = 8000 bits
    ("kbps", 128000.0, "1000"),        # 128000 bytes = 1000 kilobits
    ("mbps", 1310720.0, "10.0"),       # 1310720 bytes = 10 megabits
    ("gbps", 134217728.0, "1.00"),     # 134217728 bytes = 1 gigabit
])
def test_network_format_speed_units(unit, bytes_per_sec, expected):
    """
    Параметризованный тест форматирования скорости в разных единицах.

    Проверяет конвертацию из bytes/sec в bps, kbps, mbps, gbps.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(speed_unit=unit)
        result = widget._format_speed(bytes_per_sec)
        assert result == expected


# =============================================================================
# Тесты расчёта процента скорости
# =============================================================================

def test_network_get_speed_percentage_fixed_scaling():
    """
    Тест расчёта процента с фиксированным масштабом.

    При max_speed_mbps = 100, 50 Mbps должно дать 50%.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(max_speed_mbps=100.0)

        # 50 Mbps = 50 * 1024 * 1024 / 8 = 6553600 bytes/sec
        speed_bytes = 6553600.0
        percentage = widget._get_speed_percentage(speed_bytes)

        assert percentage == pytest.approx(50.0, abs=0.1)


def test_network_get_speed_percentage_dynamic_scaling():
    """
    Тест расчёта процента с динамическим масштабом.

    Масштаб определяется максимумом в истории.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(max_speed_mbps=-1.0, display_mode="graph")

        # Добавляем данные в историю
        widget._rx_history.append(100000.0)  # 100 KB/s
        widget._rx_history.append(200000.0)  # 200 KB/s (максимум)
        widget._tx_history.append(50000.0)   # 50 KB/s

        # При скорости 100000, максимум = 200000, процент = 50%
        percentage = widget._get_speed_percentage(100000.0)
        assert percentage == pytest.approx(50.0, abs=0.1)


def test_network_get_speed_percentage_over_100():
    """
    Тест что процент ограничен 100%.

    Edge case: Скорость выше максимума должна давать 100%.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(max_speed_mbps=100.0)

        # 200 Mbps (в 2 раза больше максимума)
        speed_bytes = 200.0 * 1024 * 1024 / 8
        percentage = widget._get_speed_percentage(speed_bytes)

        assert percentage == 100.0


# =============================================================================
# Тесты render() общие
# =============================================================================

def test_network_render_returns_image():
    """
    Тест что render() возвращает PIL Image.

    Проверяет корректный тип и размер изображения.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget()
        widget.set_size(128, 40)
        widget._current_rx_speed = 0.0
        widget._current_tx_speed = 0.0

        image = widget.render()

        assert isinstance(image, Image.Image)
        assert image.size == (128, 40)


def test_network_render_calls_update_if_needed():
    """
    Тест что render() вызывает update() если данных нет.

    При первом render() должен автоматически обновить данные.
    """
    with patch('widgets.network.psutil') as mock_psutil:
        mock_stats = Mock()
        mock_stats.bytes_recv = 1000000
        mock_stats.bytes_sent = 500000
        mock_psutil.net_io_counters.return_value = {"eth0": mock_stats}

        widget = NetworkWidget(interface="eth0")
        widget.set_size(128, 40)

        # Данных нет
        assert widget._current_rx_speed is None

        widget.render()

        # После render() данные должны быть обновлены
        assert widget._current_rx_speed is not None
        assert widget._current_tx_speed is not None


def test_network_render_with_border():
    """
    Тест рендеринга с рамкой виджета.

    Проверяет что border рисуется.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(border=True)
        widget.set_size(128, 40)
        widget._current_rx_speed = 0.0
        widget._current_tx_speed = 0.0

        image = widget.render()

        assert image is not None


def test_network_render_with_alpha_channel():
    """
    Тест рендеринга с альфа-каналом.

    При background_opacity < 255 должно создаться LA изображение.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(background_opacity=128)
        widget.set_size(128, 40)
        widget._current_rx_speed = 0.0
        widget._current_tx_speed = 0.0

        image = widget.render()

        assert image.mode == 'LA'


# =============================================================================
# Тесты render() в text режиме
# =============================================================================

def test_network_render_text_mode():
    """
    Тест рендеринга в text режиме.

    Должен отобразить "RX:xxx" и "TX:xxx".
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(display_mode="text", speed_unit="kbps")
        widget.set_size(128, 40)
        widget._current_rx_speed = 128000.0  # 128 KB/s = 1000 kbps
        widget._current_tx_speed = 64000.0   # 64 KB/s = 500 kbps

        image = widget.render()

        assert isinstance(image, Image.Image)


# =============================================================================
# Тесты render() в bar_horizontal режиме
# =============================================================================

def test_network_render_bar_horizontal():
    """
    Тест рендеринга в bar_horizontal режиме.

    Должны быть нарисованы 2 горизонтальных бара (RX сверху, TX снизу).
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(display_mode="bar_horizontal", max_speed_mbps=100.0)
        widget.set_size(128, 40)
        widget._current_rx_speed = 6553600.0  # 50 Mbps
        widget._current_tx_speed = 3276800.0  # 25 Mbps

        image = widget.render()

        assert image.size == (128, 40)
        # Должны быть белые пиксели (бары отрисованы)
        pixels = list(image.getdata())
        assert any(p > 0 for p in pixels)


def test_network_render_bar_horizontal_zero_speed():
    """
    Тест bar_horizontal при нулевой скорости.

    Edge case: При 0% не должно быть заполнения (только рамки если включены).
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(display_mode="bar_horizontal", bar_border=False)
        widget.set_size(128, 40)
        widget._current_rx_speed = 0.0
        widget._current_tx_speed = 0.0

        image = widget.render()

        # Изображение должно быть пустым (все пиксели чёрные)
        pixels = list(image.getdata())
        assert all(p == 0 for p in pixels)


def test_network_render_bar_horizontal_max_speed():
    """
    Тест bar_horizontal при максимальной скорости.

    Edge case: При 100% бары должны быть полностью заполнены.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(display_mode="bar_horizontal", max_speed_mbps=100.0)
        widget.set_size(128, 40)
        # Скорость = 100 Mbps
        widget._current_rx_speed = 100.0 * 1024 * 1024 / 8
        widget._current_tx_speed = 100.0 * 1024 * 1024 / 8

        image = widget.render()

        pixels = list(image.getdata())
        # Должно быть много белых пикселей (бары заполнены)
        white_pixels = sum(1 for p in pixels if p == 255)
        assert white_pixels > 100


def test_network_render_bar_horizontal_with_border():
    """
    Тест bar_horizontal с рамками вокруг баров.

    Проверяет параметр bar_border.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(display_mode="bar_horizontal", bar_border=True)
        widget.set_size(128, 40)
        widget._current_rx_speed = 6553600.0  # 50 Mbps
        widget._current_tx_speed = 3276800.0  # 25 Mbps

        image = widget.render()

        assert image is not None


# =============================================================================
# Тесты render() в bar_vertical режиме
# =============================================================================

def test_network_render_bar_vertical():
    """
    Тест рендеринга в bar_vertical режиме.

    Должны быть нарисованы 2 вертикальных бара (RX слева, TX справа).
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(display_mode="bar_vertical", max_speed_mbps=100.0)
        widget.set_size(128, 40)
        widget._current_rx_speed = 6553600.0  # 50 Mbps
        widget._current_tx_speed = 3276800.0  # 25 Mbps

        image = widget.render()

        assert image.size == (128, 40)
        pixels = list(image.getdata())
        assert any(p > 0 for p in pixels)


# =============================================================================
# Тесты render() в graph режиме
# =============================================================================

def test_network_render_graph_with_history():
    """
    Тест рендеринга graph режима с данными.

    Должны быть нарисованы 2 линии (RX и TX).
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(display_mode="graph", history_length=10, max_speed_mbps=100.0)
        widget.set_size(128, 40)

        # Добавляем данные в историю
        for i in range(5):
            widget._rx_history.append(float(i * 1000000))
            widget._tx_history.append(float(i * 500000))

        image = widget.render()

        assert image.size == (128, 40)


def test_network_render_graph_empty_history():
    """
    Тест graph режима с пустой историей.

    Edge case: С <2 точками график не рисуется.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(display_mode="graph")
        widget.set_size(128, 40)
        widget._current_rx_speed = 0.0
        widget._current_tx_speed = 0.0

        # История пустая
        assert len(widget._rx_history) == 0
        assert len(widget._tx_history) == 0

        image = widget.render()

        # Изображение создано, но график не нарисован
        assert image.size == (128, 40)


def test_network_render_graph_insufficient_data():
    """
    Тест graph режима с недостаточным количеством данных.

    Edge case: С 1 точкой график не рисуется (нужно минимум 2).
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(display_mode="graph")
        widget.set_size(128, 40)
        widget._current_rx_speed = 0.0
        widget._current_tx_speed = 0.0

        # Только 1 точка
        widget._rx_history.append(100000.0)
        widget._tx_history.append(50000.0)

        image = widget.render()

        assert image.size == (128, 40)


# =============================================================================
# Тесты get_update_interval
# =============================================================================

def test_network_get_update_interval_default():
    """
    Тест get_update_interval возвращает дефолтное значение.

    По умолчанию 1.0 секунда.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget()
        assert widget.get_update_interval() == 1.0


def test_network_get_update_interval_custom():
    """
    Тест get_update_interval возвращает кастомное значение.

    Проверяет установку через update_interval.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(update_interval=0.5)
        assert widget.get_update_interval() == 0.5


# =============================================================================
# Тесты edge cases и стилизации
# =============================================================================

def test_network_render_with_padding():
    """
    Тест рендеринга с отступами.

    Проверяет параметр padding.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget(padding=10)
        widget.set_size(128, 40)
        widget._current_rx_speed = 0.0
        widget._current_tx_speed = 0.0

        image = widget.render()

        assert image is not None


def test_network_render_different_sizes():
    """
    Тест рендеринга с разными размерами виджета.

    Проверяет корректную работу с нестандартными размерами.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget()
        widget._current_rx_speed = 0.0
        widget._current_tx_speed = 0.0

        for size in [(64, 20), (128, 40), (256, 64)]:
            widget.set_size(*size)
            image = widget.render()
            assert image.size == size


def test_network_render_unknown_display_mode():
    """
    Тест рендеринга с неизвестным режимом.

    Edge case: Должен залогировать предупреждение и вернуть пустое изображение.
    """
    with patch('widgets.network.psutil'):
        widget = NetworkWidget()
        widget.display_mode = "invalid_mode"
        widget.set_size(128, 40)
        widget._current_rx_speed = 0.0
        widget._current_tx_speed = 0.0

        image = widget.render()

        assert isinstance(image, Image.Image)


# =============================================================================
# Integration тесты
# =============================================================================

def test_network_full_workflow():
    """
    Integration тест полного жизненного цикла виджета.

    Проверяет init -> update -> render последовательность.
    """
    with patch('widgets.network.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        # Инициализация
        widget = NetworkWidget(
            name="TestNet",
            interface="eth0",
            display_mode="bar_horizontal",
            max_speed_mbps=100.0
        )
        widget.set_size(128, 40)

        # Первый update
        mock_stats1 = Mock()
        mock_stats1.bytes_recv = 1000000
        mock_stats1.bytes_sent = 500000
        mock_psutil.net_io_counters.return_value = {"eth0": mock_stats1}
        mock_time.return_value = 100.0
        widget.update()

        # Второй update
        mock_stats2 = Mock()
        mock_stats2.bytes_recv = 1128000
        mock_stats2.bytes_sent = 564000
        mock_psutil.net_io_counters.return_value = {"eth0": mock_stats2}
        mock_time.return_value = 101.0
        widget.update()

        # Рендеринг
        image = widget.render()

        assert isinstance(image, Image.Image)
        assert widget._current_rx_speed == 128000.0
        assert widget._current_tx_speed == 64000.0


def test_network_multiple_updates_and_renders():
    """
    Integration тест с несколькими циклами update/render.

    Проверяет стабильность при многократных вызовах.
    """
    with patch('widgets.network.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        widget = NetworkWidget(display_mode="graph", history_length=5, interface="eth0")
        widget.set_size(128, 40)

        # Делаем 5 циклов
        for i in range(5):
            mock_stats = Mock()
            mock_stats.bytes_recv = 1000000 + i * 100000
            mock_stats.bytes_sent = 500000 + i * 50000
            mock_psutil.net_io_counters.return_value = {"eth0": mock_stats}
            mock_time.return_value = 100.0 + i

            widget.update()
            image = widget.render()

            assert isinstance(image, Image.Image)

        # История должна содержать 5 записей (все update добавляют в историю, включая первый)
        assert len(widget._rx_history) == 5


def test_network_realistic_usage_patterns():
    """
    Тест с реалистичными паттернами использования сети.

    Симулирует скачивание файла с переменной скоростью.
    """
    with patch('widgets.network.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        # RX скорости в KB/s: 100, 500, 1000, 2000, 1500, 800, 300, 100
        rx_speeds_kb = [100, 500, 1000, 2000, 1500, 800, 300, 100]

        widget = NetworkWidget(display_mode="graph", history_length=10, interface="eth0", max_speed_mbps=20.0)
        widget.set_size(128, 40)

        bytes_recv = 0
        bytes_sent = 0

        for i, speed_kb in enumerate(rx_speeds_kb):
            # Увеличиваем счётчики
            bytes_recv += int(speed_kb * 1024)  # KB -> bytes
            bytes_sent += int(speed_kb * 102)   # 10% от RX

            mock_stats = Mock()
            mock_stats.bytes_recv = bytes_recv
            mock_stats.bytes_sent = bytes_sent
            mock_psutil.net_io_counters.return_value = {"eth0": mock_stats}
            mock_time.return_value = 100.0 + i

            widget.update()

        # Последняя скорость должна быть ~100 KB/s
        assert widget._current_rx_speed == pytest.approx(100 * 1024, abs=1024)

        # История должна содержать все значения (все update добавляются в историю)
        assert len(widget._rx_history) == len(rx_speeds_kb)

        # Рендеринг должен пройти успешно
        image = widget.render()
        assert isinstance(image, Image.Image)
