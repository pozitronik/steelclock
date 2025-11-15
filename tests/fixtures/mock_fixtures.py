"""
Фикстуры с готовыми моками для переиспользования в тестах.

Содержит:
- Фабрики моков для сложных объектов
- Специализированные моки для конкретных сценариев
- Утилиты для создания моковых данных
"""

from typing import Callable, Generator, Tuple
from unittest.mock import Mock, patch

import pytest


# =============================================================================
# psutil Mock Factories
# =============================================================================

@pytest.fixture
def psutil_cpu_mock_factory() -> Callable[..., Mock]:
    """
    Фабрика для создания моков psutil.cpu_percent с разными значениями.

    Returns:
        Callable: Функция для создания мока с заданным значением CPU
    """
    def create_cpu_mock(value: float = 50.0, per_core: bool = False) -> Mock:
        """
        Args:
            value: Значение CPU usage (или список для per-core)
            per_core: True для per-core mode
        """
        with patch('psutil.cpu_percent') as mock:
            if per_core:
                mock.return_value = value if isinstance(value, list) else [value] * 4
            else:
                mock.return_value = value
            return mock
    return create_cpu_mock


@pytest.fixture
def psutil_memory_mock_factory() -> Callable[..., Mock]:
    """Фабрика для создания моков psutil.virtual_memory."""
    def create_memory_mock(percent: float = 60.0) -> Mock:
        """Args: percent: Memory usage в процентах"""
        with patch('psutil.virtual_memory') as mock:
            mock.return_value = Mock(
                percent=percent,
                total=16 * 1024**3,
                available=int(16 * 1024**3 * (100 - percent) / 100),
                used=int(16 * 1024**3 * percent / 100)
            )
            return mock
    return create_memory_mock


@pytest.fixture
def psutil_network_mock_factory() -> Callable[..., Mock]:
    """Фабрика для создания моков psutil.net_io_counters."""
    def create_network_mock(bytes_sent: int = 1000, bytes_recv: int = 2000, interface: str = 'Ethernet') -> Mock:
        """
        Args:
            bytes_sent: Отправленные байты
            bytes_recv: Полученные байты
            interface: Имя интерфейса
        """
        with patch('psutil.net_io_counters') as mock:
            mock.return_value = {
                interface: Mock(
                    bytes_sent=bytes_sent,
                    bytes_recv=bytes_recv,
                    packets_sent=100,
                    packets_recv=200
                )
            }
            return mock
    return create_network_mock


@pytest.fixture
def psutil_disk_mock_factory() -> Callable[..., Mock]:
    """Фабрика для создания моков psutil.disk_io_counters."""
    def create_disk_mock(read_bytes: int = 5000, write_bytes: int = 3000, disk_name: str = 'PhysicalDrive0') -> Mock:
        """
        Args:
            read_bytes: Прочитанные байты
            write_bytes: Записанные байты
            disk_name: Имя диска
        """
        with patch('psutil.disk_io_counters') as mock:
            mock.return_value = {
                disk_name: Mock(
                    read_bytes=read_bytes,
                    write_bytes=write_bytes,
                    read_count=50,
                    write_count=30
                )
            }
            return mock
    return create_disk_mock


# =============================================================================
# requests Mock Factories
# =============================================================================

@pytest.fixture
def mock_successful_api_response() -> Mock:
    """Мок успешного HTTP ответа от GameSense API."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {'status': 'ok'}
    response.text = 'OK'
    return response


@pytest.fixture
def mock_api_error_response() -> Mock:
    """Мок HTTP ответа с ошибкой 400."""
    response = Mock()
    response.status_code = 400
    response.json.side_effect = ValueError("No JSON")
    response.text = 'Bad Request'
    return response


@pytest.fixture
def mock_api_timeout_response() -> Mock:
    """Мок для симуляции timeout."""
    import requests
    mock = Mock()
    mock.post.side_effect = requests.exceptions.Timeout("Request timed out")
    return mock


@pytest.fixture
def mock_api_connection_error() -> Mock:
    """Мок для симуляции connection error."""
    import requests
    mock = Mock()
    mock.post.side_effect = requests.exceptions.ConnectionError("Connection refused")
    return mock


# =============================================================================
# Font Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_font_truetype() -> Generator[Mock, None, None]:
    """Мок для PIL ImageFont.truetype."""
    with patch('PIL.ImageFont.truetype') as mock:
        # Возвращаем мок font object
        font_mock = Mock()
        font_mock.getbbox.return_value = (0, 0, 50, 10)  # Стандартный размер текста
        mock.return_value = font_mock
        yield mock


@pytest.fixture
def mock_font_load_default() -> Generator[Mock, None, None]:
    """Мок для PIL ImageFont.load_default."""
    with patch('PIL.ImageFont.load_default') as mock:
        font_mock = Mock()
        font_mock.getbbox.return_value = (0, 0, 40, 8)
        mock.return_value = font_mock
        yield mock


# =============================================================================
# File System Mocks
# =============================================================================

@pytest.fixture
def mock_font_path_exists() -> Generator[Tuple[Mock, Mock], None, None]:
    """Мок для os.path.exists/isfile - шрифт найден."""
    with patch('os.path.isfile') as mock_isfile, \
         patch('pathlib.Path.exists') as mock_exists:
        mock_isfile.return_value = True
        mock_exists.return_value = True
        yield (mock_isfile, mock_exists)


@pytest.fixture
def mock_font_path_missing() -> Generator[Tuple[Mock, Mock], None, None]:
    """Мок для os.path.exists/isfile - шрифт не найден."""
    with patch('os.path.isfile') as mock_isfile, \
         patch('pathlib.Path.exists') as mock_exists:
        mock_isfile.return_value = False
        mock_exists.return_value = False
        yield (mock_isfile, mock_exists)


# =============================================================================
# Keyboard State Mocks
# =============================================================================

@pytest.fixture
def mock_keyboard_all_off() -> Generator[Mock, None, None]:
    """Мок ctypes для всех клавиш в состоянии OFF."""
    with patch('ctypes.windll') as mock_windll:
        mock_windll.user32.GetKeyState.return_value = 0  # OFF
        yield mock_windll.user32


@pytest.fixture
def mock_keyboard_caps_on() -> Generator[Mock, None, None]:
    """Мок ctypes с Caps Lock в состоянии ON."""
    with patch('ctypes.windll') as mock_windll:
        def get_key_state(vk_code: int) -> int:
            if vk_code == 0x14:  # VK_CAPITAL (Caps Lock)
                return 1  # ON
            return 0  # OFF для остальных

        mock_windll.user32.GetKeyState.side_effect = get_key_state
        yield mock_windll.user32


# =============================================================================
# Threading Mocks
# =============================================================================

@pytest.fixture
def mock_threading_no_delay() -> Generator[Mock, None, None]:
    """Мок для threading.Event.wait - пропускает задержки."""
    with patch('threading.Event.wait') as mock_wait:
        # wait() сразу возвращается без ожидания
        mock_wait.return_value = False
        yield mock_wait


@pytest.fixture
def mock_time_no_sleep() -> Generator[Mock, None, None]:
    """Мок для time.sleep - пропускает задержки."""
    with patch('time.sleep') as mock_sleep:
        # sleep() ничего не делает
        mock_sleep.return_value = None
        yield mock_sleep
