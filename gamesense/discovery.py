"""
Модуль обнаружения SteelSeries GameSense сервера.
Читает coreProps.json для получения адреса HTTP сервера.
"""

import json
import os
from pathlib import Path
from typing import Optional, Tuple


class ServerDiscoveryError(Exception):
    """Ошибка при обнаружении сервера GameSense"""
    pass


def discover_server() -> Tuple[str, int]:
    """
    Обнаруживает адрес и порт SteelSeries GameSense сервера.

    Returns:
        Tuple[str, int]: (host, port) например ("127.0.0.1", 51248)

    Raises:
        ServerDiscoveryError: Если не удалось найти или прочитать coreProps.json
    """
    config_path = _find_core_props_path()

    if not config_path:
        raise ServerDiscoveryError(
            "Cannot find coreProps.json. Is SteelSeries Engine 3 installed?"
        )

    if not config_path.exists():
        raise ServerDiscoveryError(
            f"Config file not found at: {config_path}"
        )

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        address = data.get('address')
        if not address:
            raise ServerDiscoveryError("No 'address' field in coreProps.json")

        # Парсим адрес вида "127.0.0.1:51248"
        if ':' not in address:
            raise ServerDiscoveryError(f"Invalid address format: {address}")

        host, port_str = address.rsplit(':', 1)
        port = int(port_str)

        return (host, port)

    except json.JSONDecodeError as e:
        raise ServerDiscoveryError(f"Invalid JSON in coreProps.json: {e}")
    except ValueError as e:
        raise ServerDiscoveryError(f"Invalid port number: {e}")
    except Exception as e:
        raise ServerDiscoveryError(f"Error reading coreProps.json: {e}")


def _find_core_props_path() -> Optional[Path]:
    r"""
    Находит путь к coreProps.json в зависимости от ОС.

    Поддерживает:
    - Windows: %PROGRAMDATA%\SteelSeries\SteelSeries Engine 3\coreProps.json
    - macOS: /Library/Application Support/SteelSeries Engine 3/coreProps.json

    Returns:
        Optional[Path]: Путь к файлу или None если не найден
    """
    # Проверяем переменную окружения (Windows)
    program_data = os.environ.get('PROGRAMDATA')
    if program_data:
        path = Path(program_data) / 'SteelSeries' / 'SteelSeries Engine 3' / 'coreProps.json'
        if path.exists():
            return path

    # Fallback для Windows с жёстко заданным путём
    windows_path = Path('C:/ProgramData/SteelSeries/SteelSeries Engine 3/coreProps.json')
    if windows_path.exists():
        return windows_path

    # macOS путь (на случай если когда-то понадобится)
    mac_path = Path('/Library/Application Support/SteelSeries Engine 3/coreProps.json')
    if mac_path.exists():
        return mac_path

    return None


def get_server_url() -> str:
    """
    Получает полный URL сервера GameSense.

    Returns:
        str: URL вида "http://127.0.0.1:51248"

    Raises:
        ServerDiscoveryError: Если не удалось обнаружить сервер
    """
    host, port = discover_server()
    return f"http://{host}:{port}"
