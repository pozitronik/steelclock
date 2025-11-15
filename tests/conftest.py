"""
Главный файл конфигурации pytest с общими fixtures для всех тестов.

Содержит:
- Базовые моки для внешних зависимостей (psutil, requests, ctypes)
- Временные директории и файлы
- Утилиты для создания тестовых данных
- Фикстуры для контроля времени
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from typing import Any, Dict

import pytest
from PIL import Image


# =============================================================================
# Mocking Fixtures - psutil
# =============================================================================

@pytest.fixture
def mock_psutil():
    """
    Базовый мок для psutil со стандартными значениями.

    Returns:
        MagicMock: Мок psutil с предустановленными значениями для CPU/Memory/Network/Disk
    """
    with patch('psutil.cpu_percent') as cpu_mock, \
         patch('psutil.cpu_count') as cpu_count_mock, \
         patch('psutil.virtual_memory') as mem_mock, \
         patch('psutil.net_io_counters') as net_mock, \
         patch('psutil.disk_io_counters') as disk_mock:

        # CPU defaults
        cpu_mock.return_value = 50.0
        cpu_count_mock.return_value = 4

        # Memory defaults
        mem_mock.return_value = Mock(
            percent=60.0,
            total=16 * 1024**3,  # 16GB
            available=6 * 1024**3,  # 6GB
            used=10 * 1024**3  # 10GB
        )

        # Network defaults
        net_mock.return_value = {
            'Ethernet': Mock(
                bytes_sent=1000000,
                bytes_recv=2000000,
                packets_sent=1000,
                packets_recv=2000
            )
        }

        # Disk defaults
        disk_mock.return_value = {
            'PhysicalDrive0': Mock(
                read_bytes=5000000,
                write_bytes=3000000,
                read_count=500,
                write_count=300
            )
        }

        yield {
            'cpu_percent': cpu_mock,
            'cpu_count': cpu_count_mock,
            'virtual_memory': mem_mock,
            'net_io_counters': net_mock,
            'disk_io_counters': disk_mock
        }


@pytest.fixture
def mock_psutil_cpu_per_core():
    """Мок для psutil.cpu_percent с per-core данными."""
    with patch('psutil.cpu_percent') as mock:
        mock.return_value = [25.0, 50.0, 75.0, 100.0]
        yield mock


# =============================================================================
# Mocking Fixtures - requests (GameSense API)
# =============================================================================

@pytest.fixture
def mock_requests_session():
    """
    Мок для requests.Session с успешными ответами API.

    Returns:
        MagicMock: Мок Session с предустановленными успешными ответами
    """
    with patch('requests.Session') as session_mock:
        # Создаём экземпляр мока
        instance = session_mock.return_value

        # POST всегда возвращает 200 OK
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.json.return_value = {'status': 'ok'}
        response_mock.text = 'OK'

        instance.post.return_value = response_mock
        instance.close.return_value = None

        yield instance


@pytest.fixture
def mock_gamesense_discovery():
    """Мок для server discovery, возвращает тестовый URL."""
    with patch('gamesense.discovery.get_server_url') as mock:
        mock.return_value = 'http://127.0.0.1:12345'
        yield mock


# =============================================================================
# Mocking Fixtures - ctypes (Windows keyboard)
# =============================================================================

@pytest.fixture
def mock_windows_keyboard():
    """
    Мок для Windows ctypes keyboard API.

    Returns:
        MagicMock: Мок с методом GetKeyState
    """
    with patch('ctypes.windll') as mock:
        # GetKeyState возвращает 0 (OFF) для всех клавиш по умолчанию
        mock.user32.GetKeyState.return_value = 0
        yield mock.user32


# =============================================================================
# Mocking Fixtures - datetime/time
# =============================================================================

@pytest.fixture
def fixed_time():
    """
    Фиксирует время для тестов.

    Returns:
        datetime: Фиксированная дата/время: 2025-11-15 12:34:56
    """
    from datetime import datetime
    from unittest.mock import patch

    fixed_datetime = datetime(2025, 11, 15, 12, 34, 56)

    with patch('datetime.datetime') as mock_datetime:
        mock_datetime.now.return_value = fixed_datetime
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        yield fixed_datetime


# =============================================================================
# Image Fixtures
# =============================================================================

@pytest.fixture
def blank_image_128x40():
    """Создаёт пустое чёрное изображение 128x40."""
    return Image.new('L', (128, 40), color=0)


@pytest.fixture
def blank_image_128x40_white():
    """Создаёт пустое белое изображение 128x40."""
    return Image.new('L', (128, 40), color=255)


@pytest.fixture
def blank_image_with_alpha():
    """Создаёт пустое изображение с альфа-каналом."""
    return Image.new('LA', (128, 40), color=(0, 128))


# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def valid_config_dict() -> Dict[str, Any]:
    """
    Возвращает валидную конфигурацию приложения.

    Returns:
        Dict[str, Any]: Минимальная валидная конфигурация
    """
    return {
        "game_name": "TEST_GAME",
        "game_display_name": "Test Game",
        "refresh_rate_ms": 100,
        "display": {
            "width": 128,
            "height": 40,
            "background_color": 0
        },
        "widgets": []
    }


@pytest.fixture
def clock_widget_config() -> Dict[str, Any]:
    """Конфигурация для Clock widget."""
    return {
        "type": "clock",
        "id": "test_clock",
        "enabled": True,
        "position": {"x": 0, "y": 0, "w": 128, "h": 40, "z_order": 0},
        "properties": {
            "format": "%H:%M:%S",
            "update_interval": 1.0,
            "font_size": 12
        },
        "style": {
            "background_color": 0,
            "border": False
        }
    }


@pytest.fixture
def cpu_widget_config() -> Dict[str, Any]:
    """Конфигурация для CPU widget."""
    return {
        "type": "cpu",
        "id": "test_cpu",
        "enabled": True,
        "position": {"x": 0, "y": 0, "w": 128, "h": 40, "z_order": 0},
        "properties": {
            "display_mode": "bar_horizontal",
            "per_core": False,
            "update_interval": 1.0,
            "fill_color": 255
        },
        "style": {
            "background_color": 0
        }
    }


# =============================================================================
# Temporary File Fixtures
# =============================================================================

@pytest.fixture
def temp_config_file(tmp_path, valid_config_dict):
    """
    Создаёт временный файл конфигурации.

    Args:
        tmp_path: Pytest fixture для временной директории
        valid_config_dict: Валидная конфигурация

    Returns:
        Path: Путь к временному config.json
    """
    import json

    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(valid_config_dict, indent=2))
    return config_file


# =============================================================================
# Platform Detection Fixtures
# =============================================================================

@pytest.fixture
def mock_windows_platform():
    """Мок для platform.system() возвращающий Windows."""
    with patch('platform.system') as mock:
        mock.return_value = 'Windows'
        yield mock


@pytest.fixture
def mock_linux_platform():
    """Мок для platform.system() возвращающий Linux."""
    with patch('platform.system') as mock:
        mock.return_value = 'Linux'
        yield mock


# =============================================================================
# Утилитарные функции для тестов
# =============================================================================

def assert_image_size(image: Image.Image, width: int, height: int):
    """
    Проверяет размер изображения.

    Args:
        image: PIL Image для проверки
        width: Ожидаемая ширина
        height: Ожидаемая высота

    Raises:
        AssertionError: Если размер не совпадает
    """
    assert image.size == (width, height), \
        f"Expected {width}x{height}, got {image.size[0]}x{image.size[1]}"


def assert_image_mode(image: Image.Image, mode: str):
    """
    Проверяет цветовой режим изображения.

    Args:
        image: PIL Image для проверки
        mode: Ожидаемый режим ('L', 'LA', 'RGB', etc.)

    Raises:
        AssertionError: Если режим не совпадает
    """
    assert image.mode == mode, \
        f"Expected mode {mode}, got {image.mode}"


# Экспортируем утилиты для использования в тестах
pytest.assert_image_size = assert_image_size
pytest.assert_image_mode = assert_image_mode
