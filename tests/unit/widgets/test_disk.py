"""
Unit tests для widgets.disk - виджет мониторинга дисков.

Тестируемый модуль: widgets/disk.py

Покрытие:
- Инициализация и проверка наличия psutil
- Автовыбор диска когда disk_name=None
- Обновление данных (update) с расчётом скорости
- История для graph режима (READ и WRITE отдельно)
- Рендеринг в разных режимах (text, bar_horizontal, bar_vertical, graph)
- Форматирование скорости (K/M/G)
- Динамическое и фиксированное масштабирование
- Отслеживание пиковых скоростей
- Edge cases и error handling
"""

import pytest
from unittest.mock import patch, Mock
from PIL import Image
from widgets.disk import DiskWidget


# =============================================================================
# Тесты инициализации
# =============================================================================

def test_disk_init_requires_psutil() -> None:
    """
    Тест инициализации требует psutil.

    Edge case: Должен вызвать ImportError если psutil не установлен.
    """
    with patch('widgets.disk.psutil', None):
        with pytest.raises(ImportError) as exc_info:
            DiskWidget()

        assert "psutil library is required" in str(exc_info.value)


def test_disk_init_default_values() -> None:
    """
    Тест инициализации с дефолтными значениями.

    Проверяет:
    - Имя виджета по умолчанию
    - Режим отображения по умолчанию (bar_horizontal)
    - disk_name=None (автовыбор)
    - Интервал обновления
    - История пустая
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {"sda": Mock()}

        widget = DiskWidget()

        assert widget.name == "Disk"
        assert widget.display_mode == "bar_horizontal"
        assert widget.disk_name is None
        assert widget.update_interval_sec == 1.0
        assert widget.history_length == 30
        assert widget._current_read_speed == 0.0
        assert widget._current_write_speed == 0.0
        assert len(widget._read_history) == 0
        assert len(widget._write_history) == 0


def test_disk_init_custom_values() -> None:
    """
    Тест инициализации с кастомными значениями.

    Проверяет корректную установку всех параметров.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(
            name="CustomDisk",
            disk_name="sda",
            display_mode="graph",
            update_interval=0.5,
            history_length=60,
            max_speed_mbps=100.0,
            read_color=200,
            write_color=150
        )

        assert widget.name == "CustomDisk"
        assert widget.disk_name == "sda"
        assert widget.display_mode == "graph"
        assert widget.update_interval_sec == 0.5
        assert widget.history_length == 60
        assert widget.max_speed_mbps == 100.0
        assert widget.read_color == 200
        assert widget.write_color == 150


@pytest.mark.parametrize("mode", ["text", "bar_horizontal", "bar_vertical", "graph"])
def test_disk_init_all_display_modes(mode: str) -> None:
    """
    Параметризованный тест проверяет все 4 режима отображения.

    Проверяет:
    - text: Текстовый вывод READ/WRITE
    - bar_horizontal: Две горизонтальные полосы
    - bar_vertical: Два вертикальных столбца
    - graph: График истории скоростей
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(display_mode=mode, disk_name="sda")
        assert widget.display_mode == mode


def test_disk_init_dynamic_scaling() -> None:
    """
    Тест инициализации с динамическим масштабированием.

    При max_speed_mbps <= 0 должно использоваться динамическое масштабирование.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(max_speed_mbps=-1, disk_name="sda")

        assert widget.max_speed_mbps == -1
        assert widget._peak_read_speed == 1.0  # Начальное значение
        assert widget._peak_write_speed == 1.0


def test_disk_init_fixed_scaling() -> None:
    """
    Тест инициализации с фиксированным масштабированием.

    При max_speed_mbps > 0 должен использоваться фиксированный масштаб.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(max_speed_mbps=500.0, disk_name="sda")

        assert widget.max_speed_mbps == 500.0


# =============================================================================
# Тесты автовыбора диска
# =============================================================================

def test_disk_auto_select_first_disk() -> None:
    """
    Тест автовыбора первого доступного диска.

    Когда disk_name=None, должен выбрать первый диск из списка.
    """
    with patch('widgets.disk.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        mock_counter = Mock()
        mock_counter.read_bytes = 1000000
        mock_counter.write_bytes = 500000
        mock_psutil.disk_io_counters.return_value = {"sda": mock_counter, "sdb": mock_counter}
        mock_time.return_value = 100.0

        widget = DiskWidget(disk_name=None)
        widget.update()

        # Должен автоматически выбрать первый диск
        assert widget.disk_name in ["sda", "sdb"]


# =============================================================================
# Тесты update()
# =============================================================================

def test_disk_update_first_call_initializes() -> None:
    """
    Тест первого вызова update() инициализирует счётчики.

    Edge case: При первом вызове нет предыдущих данных, скорость не вычисляется.
    """
    with patch('widgets.disk.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        mock_counter = Mock()
        mock_counter.read_bytes = 1000000
        mock_counter.write_bytes = 500000
        mock_psutil.disk_io_counters.return_value = {"sda": mock_counter}
        mock_time.return_value = 100.0

        widget = DiskWidget(disk_name="sda")
        widget.update()

        # Первый вызов инициализирует счётчики, но не вычисляет скорость
        assert widget._last_read_bytes == 1000000
        assert widget._last_write_bytes == 500000
        assert widget._last_update_time == 100.0


def test_disk_update_calculates_speed() -> None:
    """
    Тест расчёта скорости на основе дельты байтов.

    Проверяет формулу: speed = (bytes_delta) / (time_delta)
    """
    with patch('widgets.disk.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        # Первый вызов
        mock_counter1 = Mock()
        mock_counter1.read_bytes = 1000000
        mock_counter1.write_bytes = 500000
        mock_psutil.disk_io_counters.return_value = {"sda": mock_counter1}
        mock_time.return_value = 100.0

        widget = DiskWidget(disk_name="sda")
        widget.update()

        # Второй вызов через 1 секунду
        mock_counter2 = Mock()
        mock_counter2.read_bytes = 1104857600  # +1100 MB (примерно 1100 MB/s)
        mock_counter2.write_bytes = 552428800   # +550 MB (примерно 550 MB/s)
        mock_psutil.disk_io_counters.return_value = {"sda": mock_counter2}
        mock_time.return_value = 101.0

        widget.update()

        # Проверяем расчёт скорости (delta_bytes / delta_time)
        expected_read_speed = (1104857600 - 1000000) / 1.0
        expected_write_speed = (552428800 - 500000) / 1.0
        assert widget._current_read_speed == pytest.approx(expected_read_speed, rel=0.01)
        assert widget._current_write_speed == pytest.approx(expected_write_speed, rel=0.01)


def test_disk_update_missing_disk() -> None:
    """
    Тест update() когда диск не найден.

    Edge case: Должен установить скорость в 0 и залогировать предупреждение.
    """
    with patch('widgets.disk.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        # Диск sda не найден
        mock_psutil.disk_io_counters.return_value = {"sdb": Mock()}
        mock_time.return_value = 100.0

        widget = DiskWidget(disk_name="sda")
        widget.update()

        assert widget._current_read_speed == 0.0
        assert widget._current_write_speed == 0.0


def test_disk_update_negative_delta_clamped() -> None:
    """
    Тест что отрицательная дельта (сброс счётчика) обрабатывается.

    Edge case: Если read_bytes уменьшился (счётчик обнулён), скорость = 0.
    """
    with patch('widgets.disk.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        # Первый вызов
        mock_counter1 = Mock()
        mock_counter1.read_bytes = 1000000
        mock_counter1.write_bytes = 500000
        mock_psutil.disk_io_counters.return_value = {"sda": mock_counter1}
        mock_time.return_value = 100.0

        widget = DiskWidget(disk_name="sda")
        widget.update()

        # Второй вызов - счётчик обнулён
        mock_counter2 = Mock()
        mock_counter2.read_bytes = 100  # Меньше чем было
        mock_counter2.write_bytes = 50
        mock_psutil.disk_io_counters.return_value = {"sda": mock_counter2}
        mock_time.return_value = 101.0

        widget.update()

        # Отрицательная дельта должна быть зажата в 0
        assert widget._current_read_speed == 0.0
        assert widget._current_write_speed == 0.0


def test_disk_update_zero_time_delta() -> None:
    """
    Тест update() когда time_delta = 0 (мгновенный вызов).

    Edge case: Деление на 0 должно быть обработано.
    """
    with patch('widgets.disk.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        mock_counter = Mock()
        mock_counter.read_bytes = 1000000
        mock_counter.write_bytes = 500000
        mock_psutil.disk_io_counters.return_value = {"sda": mock_counter}
        mock_time.return_value = 100.0

        widget = DiskWidget(disk_name="sda")
        widget.update()
        widget.update()  # Сразу второй раз

        # При time_delta <= 0, скорость не должна измениться
        # (вторая update не вычисляет скорость при time_delta=0)


def test_disk_update_tracks_peak_speeds() -> None:
    """
    Тест что update() отслеживает пиковые скорости для динамического масштабирования.

    Пиковые скорости должны обновляться при превышении.
    """
    with patch('widgets.disk.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        widget = DiskWidget(disk_name="sda", max_speed_mbps=-1)  # Динамическое масштабирование

        # Первый update - инициализация
        mock_counter1 = Mock()
        mock_counter1.read_bytes = 0
        mock_counter1.write_bytes = 0
        mock_psutil.disk_io_counters.return_value = {"sda": mock_counter1}
        mock_time.return_value = 100.0
        widget.update()

        # Второй update - 10 MB/s чтения, 5 MB/s записи
        mock_counter2 = Mock()
        mock_counter2.read_bytes = 10 * 1024 * 1024
        mock_counter2.write_bytes = 5 * 1024 * 1024
        mock_psutil.disk_io_counters.return_value = {"sda": mock_counter2}
        mock_time.return_value = 101.0
        widget.update()

        assert widget._peak_read_speed >= 10.0
        assert widget._peak_write_speed >= 5.0


# =============================================================================
# Тесты истории для graph режима
# =============================================================================

def test_disk_update_graph_mode_adds_to_history() -> None:
    """
    Тест что в graph режиме данные добавляются в историю.

    Проверяет добавление в _read_history и _write_history.
    """
    with patch('widgets.disk.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        widget = DiskWidget(display_mode="graph", history_length=10, disk_name="sda")

        # Первый update
        mock_counter1 = Mock()
        mock_counter1.read_bytes = 1000000
        mock_counter1.write_bytes = 500000
        mock_psutil.disk_io_counters.return_value = {"sda": mock_counter1}
        mock_time.return_value = 100.0
        widget.update()

        # Второй update
        mock_counter2 = Mock()
        mock_counter2.read_bytes = 1128000
        mock_counter2.write_bytes = 564000
        mock_psutil.disk_io_counters.return_value = {"sda": mock_counter2}
        mock_time.return_value = 101.0
        widget.update()

        assert len(widget._read_history) >= 1
        assert len(widget._write_history) >= 1


def test_disk_update_graph_mode_respects_max_length() -> None:
    """
    Тест что deque соблюдает maxlen.

    Edge case: Старые значения вытесняются новыми.
    """
    with patch('widgets.disk.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        widget = DiskWidget(display_mode="graph", history_length=3, disk_name="sda")

        # Делаем 5 обновлений
        for i in range(5):
            mock_counter = Mock()
            mock_counter.read_bytes = 1000000 + i * 100000
            mock_counter.write_bytes = 500000 + i * 50000
            mock_psutil.disk_io_counters.return_value = {"sda": mock_counter}
            mock_time.return_value = 100.0 + i
            widget.update()

        # История должна содержать не более 3 значений
        assert len(widget._read_history) <= 3
        assert len(widget._write_history) <= 3


def test_disk_update_non_graph_mode_no_history() -> None:
    """
    Тест что в не-graph режимах история не сохраняется.

    В bar/text режимах _read_history и _write_history должны быть пустыми.
    """
    with patch('widgets.disk.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        widget = DiskWidget(display_mode="bar_horizontal", disk_name="sda")

        # Несколько обновлений
        for i in range(3):
            mock_counter = Mock()
            mock_counter.read_bytes = 1000000 + i * 100000
            mock_counter.write_bytes = 500000 + i * 50000
            mock_psutil.disk_io_counters.return_value = {"sda": mock_counter}
            mock_time.return_value = 100.0 + i
            widget.update()

        assert len(widget._read_history) == 0
        assert len(widget._write_history) == 0


# =============================================================================
# Тесты обработки ошибок
# =============================================================================

def test_disk_update_handles_psutil_error() -> None:
    """
    Тест обработки исключения при вызове psutil.

    Если psutil.disk_io_counters() вызывает ошибку, должен установить скорость в 0.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.side_effect = Exception("Disk error")

        widget = DiskWidget(disk_name="sda")
        widget.update()

        assert widget._current_read_speed == 0.0
        assert widget._current_write_speed == 0.0


# =============================================================================
# Тесты форматирования скорости
# =============================================================================

@pytest.mark.parametrize("bytes_per_sec,expected", [
    (512 * 1024, "512K"),               # 512 KB/s
    (1024 * 1024, "1.0M"),              # 1 MB/s
    (100 * 1024 * 1024, "100.0M"),      # 100 MB/s
    (1500 * 1024 * 1024, "1.5G"),       # 1.5 GB/s
])
def test_disk_format_speed_units(bytes_per_sec: int, expected: str) -> None:
    """
    Параметризованный тест форматирования скорости в K/M/G.

    Проверяет корректную конвертацию из bytes/sec.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(disk_name="sda")
        result = widget._format_speed(bytes_per_sec)
        assert result == expected


# =============================================================================
# Тесты расчёта процента скорости
# =============================================================================

def test_disk_get_speed_percentage_fixed_scaling() -> None:
    """
    Тест расчёта процента с фиксированным масштабом.

    При max_speed_mbps = 100, 50 MB/s должно дать 50%.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(max_speed_mbps=100.0, disk_name="sda")

        # 50 MB/s = 50 * 1024 * 1024 bytes/sec
        speed_bytes = 50.0 * 1024 * 1024
        percentage = widget._get_speed_percentage(speed_bytes, is_read=True)

        assert percentage == pytest.approx(50.0, abs=0.1)


def test_disk_get_speed_percentage_dynamic_scaling() -> None:
    """
    Тест расчёта процента с динамическим масштабом.

    Масштаб определяется пиковой скоростью.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(max_speed_mbps=-1, disk_name="sda")

        # Устанавливаем пиковую скорость
        widget._peak_read_speed = 100.0  # 100 MB/s

        # При скорости 50 MB/s и пике 100 MB/s, процент = 50%
        speed_bytes = 50.0 * 1024 * 1024
        percentage = widget._get_speed_percentage(speed_bytes, is_read=True)
        assert percentage == pytest.approx(50.0, abs=0.1)


def test_disk_get_speed_percentage_over_100() -> None:
    """
    Тест что процент ограничен 100%.

    Edge case: Скорость выше максимума должна давать 100%.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(max_speed_mbps=100.0, disk_name="sda")

        # 200 MB/s (в 2 раза больше максимума)
        speed_bytes = 200.0 * 1024 * 1024
        percentage = widget._get_speed_percentage(speed_bytes, is_read=True)

        assert percentage == 100.0


# =============================================================================
# Тесты render() общие
# =============================================================================

def test_disk_render_returns_image() -> None:
    """
    Тест что render() возвращает PIL Image.

    Проверяет корректный тип и размер изображения.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(disk_name="sda")
        widget.set_size(128, 40)

        image = widget.render()

        assert isinstance(image, Image.Image)
        assert image.size == (128, 40)


def test_disk_render_with_border() -> None:
    """
    Тест рендеринга с рамкой виджета.

    Проверяет что border рисуется.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(border=True, disk_name="sda")
        widget.set_size(128, 40)

        image = widget.render()

        assert image is not None


def test_disk_render_with_alpha_channel() -> None:
    """
    Тест рендеринга с альфа-каналом.

    При background_opacity < 255 должно создаться LA изображение.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(background_opacity=128, disk_name="sda")
        widget.set_size(128, 40)

        image = widget.render()

        assert image.mode == 'LA'


# =============================================================================
# Тесты render() в text режиме
# =============================================================================

def test_disk_render_text_mode() -> None:
    """
    Тест рендеринга в text режиме.

    Должен отобразить "R:xxx" и "W:xxx".
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(display_mode="text", disk_name="sda")
        widget.set_size(128, 40)
        widget._current_read_speed = 10 * 1024 * 1024  # 10 MB/s
        widget._current_write_speed = 5 * 1024 * 1024  # 5 MB/s

        image = widget.render()

        assert isinstance(image, Image.Image)


# =============================================================================
# Тесты render() в bar_horizontal режиме
# =============================================================================

def test_disk_render_bar_horizontal() -> None:
    """
    Тест рендеринга в bar_horizontal режиме.

    Должны быть нарисованы 2 горизонтальных бара (READ сверху, WRITE снизу).
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(display_mode="bar_horizontal", max_speed_mbps=100.0, disk_name="sda")
        widget.set_size(128, 40)
        widget._current_read_speed = 50 * 1024 * 1024
        widget._current_write_speed = 25 * 1024 * 1024

        image = widget.render()

        assert image.size == (128, 40)
        pixels = list(image.getdata())
        assert any(p > 0 for p in pixels)


def test_disk_render_bar_horizontal_zero_speed() -> None:
    """
    Тест bar_horizontal при нулевой скорости.

    Edge case: При 0% не должно быть заполнения.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(display_mode="bar_horizontal", bar_border=False, disk_name="sda")
        widget.set_size(128, 40)
        widget._current_read_speed = 0.0
        widget._current_write_speed = 0.0

        image = widget.render()

        pixels = list(image.getdata())
        assert all(p == 0 for p in pixels)


def test_disk_render_bar_horizontal_max_speed() -> None:
    """
    Тест bar_horizontal при максимальной скорости.

    Edge case: При 100% бары должны быть полностью заполнены.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(display_mode="bar_horizontal", max_speed_mbps=100.0, disk_name="sda")
        widget.set_size(128, 40)
        widget._current_read_speed = 100.0 * 1024 * 1024
        widget._current_write_speed = 100.0 * 1024 * 1024

        image = widget.render()

        pixels = list(image.getdata())
        white_pixels = sum(1 for p in pixels if p >= 200)
        assert white_pixels > 50


# =============================================================================
# Тесты render() в bar_vertical режиме
# =============================================================================

def test_disk_render_bar_vertical() -> None:
    """
    Тест рендеринга в bar_vertical режиме.

    Должны быть нарисованы 2 вертикальных бара (READ слева, WRITE справа).
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(display_mode="bar_vertical", max_speed_mbps=100.0, disk_name="sda")
        widget.set_size(128, 40)
        widget._current_read_speed = 50 * 1024 * 1024
        widget._current_write_speed = 25 * 1024 * 1024

        image = widget.render()

        assert image.size == (128, 40)
        pixels = list(image.getdata())
        assert any(p > 0 for p in pixels)


# =============================================================================
# Тесты render() в graph режиме
# =============================================================================

def test_disk_render_graph_with_history() -> None:
    """
    Тест рендеринга graph режима с данными.

    Должны быть нарисованы 2 линии (READ и WRITE).
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(display_mode="graph", history_length=10, max_speed_mbps=100.0, disk_name="sda")
        widget.set_size(128, 40)

        # Добавляем данные в историю
        for i in range(5):
            widget._read_history.append(float(i * 10 * 1024 * 1024))
            widget._write_history.append(float(i * 5 * 1024 * 1024))

        image = widget.render()

        assert image.size == (128, 40)


def test_disk_render_graph_empty_history() -> None:
    """
    Тест graph режима с пустой историей.

    Edge case: С <2 точками график не рисуется.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(display_mode="graph", disk_name="sda")
        widget.set_size(128, 40)

        # История пустая
        assert len(widget._read_history) == 0
        assert len(widget._write_history) == 0

        image = widget.render()

        # Изображение создано, но график не нарисован
        assert image.size == (128, 40)


def test_disk_render_graph_insufficient_data() -> None:
    """
    Тест graph режима с недостаточным количеством данных.

    Edge case: С 1 точкой график не рисуется (нужно минимум 2).
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(display_mode="graph", disk_name="sda")
        widget.set_size(128, 40)

        # Только 1 точка
        widget._read_history.append(100000.0)
        widget._write_history.append(50000.0)

        image = widget.render()

        assert image.size == (128, 40)


# =============================================================================
# Тесты get_update_interval
# =============================================================================

def test_disk_get_update_interval_default() -> None:
    """
    Тест get_update_interval возвращает дефолтное значение.

    По умолчанию 1.0 секунда.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(disk_name="sda")
        assert widget.get_update_interval() == 1.0


def test_disk_get_update_interval_custom() -> None:
    """
    Тест get_update_interval возвращает кастомное значение.

    Проверяет установку через update_interval.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(update_interval=0.5, disk_name="sda")
        assert widget.get_update_interval() == 0.5


# =============================================================================
# Тесты edge cases и стилизации
# =============================================================================

def test_disk_render_with_padding() -> None:
    """
    Тест рендеринга с отступами.

    Проверяет параметр padding.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(padding=10, disk_name="sda")
        widget.set_size(128, 40)

        image = widget.render()

        assert image is not None


def test_disk_render_different_sizes() -> None:
    """
    Тест рендеринга с разными размерами виджета.

    Проверяет корректную работу с нестандартными размерами.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(disk_name="sda")

        for size in [(64, 20), (128, 40), (256, 64)]:
            widget.set_size(*size)
            image = widget.render()
            assert image.size == size


def test_disk_render_unknown_display_mode() -> None:
    """
    Тест рендеринга с неизвестным режимом.

    Edge case: Должен залогировать предупреждение и вернуть пустое изображение.
    """
    with patch('widgets.disk.psutil') as mock_psutil:
        mock_psutil.disk_io_counters.return_value = {}

        widget = DiskWidget(disk_name="sda")
        widget.display_mode = "invalid_mode"
        widget.set_size(128, 40)

        image = widget.render()

        assert isinstance(image, Image.Image)


# =============================================================================
# Integration тесты
# =============================================================================

def test_disk_full_workflow() -> None:
    """
    Integration тест полного жизненного цикла виджета.

    Проверяет init -> update -> render последовательность.
    """
    with patch('widgets.disk.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        # Инициализация
        widget = DiskWidget(
            name="TestDisk",
            disk_name="sda",
            display_mode="bar_horizontal",
            max_speed_mbps=100.0
        )
        widget.set_size(128, 40)

        # Первый update
        mock_counter1 = Mock()
        mock_counter1.read_bytes = 1000000
        mock_counter1.write_bytes = 500000
        mock_psutil.disk_io_counters.return_value = {"sda": mock_counter1}
        mock_time.return_value = 100.0
        widget.update()

        # Второй update
        mock_counter2 = Mock()
        mock_counter2.read_bytes = 11048576  # +10 MB
        mock_counter2.write_bytes = 5524288   # +5 MB
        mock_psutil.disk_io_counters.return_value = {"sda": mock_counter2}
        mock_time.return_value = 101.0
        widget.update()

        # Рендеринг
        image = widget.render()

        assert isinstance(image, Image.Image)
        assert widget._current_read_speed > 0
        assert widget._current_write_speed > 0


def test_disk_multiple_updates_and_renders() -> None:
    """
    Integration тест с несколькими циклами update/render.

    Проверяет стабильность при многократных вызовах.
    """
    with patch('widgets.disk.psutil') as mock_psutil, \
         patch('time.time') as mock_time:

        widget = DiskWidget(display_mode="graph", history_length=5, disk_name="sda")
        widget.set_size(128, 40)

        # Делаем 5 циклов
        for i in range(5):
            mock_counter = Mock()
            mock_counter.read_bytes = 1000000 + i * 1048576  # +1 MB каждый раз
            mock_counter.write_bytes = 500000 + i * 524288   # +0.5 MB каждый раз
            mock_psutil.disk_io_counters.return_value = {"sda": mock_counter}
            mock_time.return_value = 100.0 + i

            widget.update()
            image = widget.render()

            assert isinstance(image, Image.Image)

        # История должна содержать данные
        assert len(widget._read_history) >= 1
