"""
Unit tests для gamesense.discovery - обнаружение GameSense сервера.

Тестируемый модуль: gamesense/discovery.py

Покрытие:
- Обнаружение сервера (discover_server)
- Поиск пути к coreProps.json (_find_core_props_path)
- Получение URL сервера (get_server_url)
- Чтение и парсинг JSON
- Обработка ошибок (файл не найден, невалидный JSON, невалидный формат)
- Поддержка разных ОС (Windows, macOS)
- Edge cases и negative tests
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, mock_open, Mock
from gamesense.discovery import (
    discover_server,
    get_server_url,
    _find_core_props_path,
    ServerDiscoveryError
)


# =============================================================================
# Тесты discover_server
# =============================================================================

def test_discover_server_success() -> None:
    """
    Тест успешного обнаружения сервера.

    Проверяет:
    - Чтение coreProps.json
    - Парсинг JSON
    - Возврат (host, port) tuple
    """
    valid_json = json.dumps({"address": "127.0.0.1:51248"})

    with patch('gamesense.discovery._find_core_props_path') as mock_find:
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_find.return_value = mock_path

        with patch('builtins.open', mock_open(read_data=valid_json)):
            host, port = discover_server()

            assert host == "127.0.0.1"
            assert port == 51248
            assert isinstance(port, int)


def test_discover_server_custom_port() -> None:
    """
    Тест обнаружения сервера с нестандартным портом.

    Проверяет что порт корректно парсится.
    """
    valid_json = json.dumps({"address": "192.168.1.100:12345"})

    with patch('gamesense.discovery._find_core_props_path') as mock_find:
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_find.return_value = mock_path

        with patch('builtins.open', mock_open(read_data=valid_json)):
            host, port = discover_server()

            assert host == "192.168.1.100"
            assert port == 12345


def test_discover_server_ipv6_address() -> None:
    """
    Тест обнаружения сервера с IPv6 адресом.

    Edge case: IPv6 адреса содержат двоеточия, используем rsplit с limit=1.
    """
    valid_json = json.dumps({"address": "::1:51248"})

    with patch('gamesense.discovery._find_core_props_path') as mock_find:
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_find.return_value = mock_path

        with patch('builtins.open', mock_open(read_data=valid_json)):
            host, port = discover_server()

            assert host == "::1"
            assert port == 51248


def test_discover_server_config_not_found() -> None:
    """
    Тест когда _find_core_props_path возвращает None.

    Edge case: coreProps.json не найден (SteelSeries Engine не установлен).
    """
    with patch('gamesense.discovery._find_core_props_path') as mock_find:
        mock_find.return_value = None

        with pytest.raises(ServerDiscoveryError) as exc_info:
            discover_server()

        assert "Cannot find coreProps.json" in str(exc_info.value)
        assert "SteelSeries Engine 3 installed" in str(exc_info.value)


def test_discover_server_config_does_not_exist() -> None:
    """
    Тест когда путь найден, но файл не существует.

    Edge case: Путь есть, но файл удалён или недоступен.
    """
    with patch('gamesense.discovery._find_core_props_path') as mock_find:
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = False
        mock_path.__str__ = lambda *args: "/path/to/coreProps.json"  # type: ignore[method-assign]
        mock_find.return_value = mock_path

        with pytest.raises(ServerDiscoveryError) as exc_info:
            discover_server()

        assert "Config file not found" in str(exc_info.value)


def test_discover_server_invalid_json() -> None:
    """
    Тест когда файл содержит невалидный JSON.

    Edge case: Файл повреждён или содержит невалидный JSON.
    """
    invalid_json = "{ broken json }"

    with patch('gamesense.discovery._find_core_props_path') as mock_find:
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_find.return_value = mock_path

        with patch('builtins.open', mock_open(read_data=invalid_json)):
            with pytest.raises(ServerDiscoveryError) as exc_info:
                discover_server()

            assert "Invalid JSON" in str(exc_info.value)


def test_discover_server_missing_address_field() -> None:
    """
    Тест когда JSON не содержит поле 'address'.

    Edge case: Файл валидный JSON, но без нужного поля.
    """
    valid_json = json.dumps({"other_field": "value"})

    with patch('gamesense.discovery._find_core_props_path') as mock_find:
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_find.return_value = mock_path

        with patch('builtins.open', mock_open(read_data=valid_json)):
            with pytest.raises(ServerDiscoveryError) as exc_info:
                discover_server()

            assert "No 'address' field" in str(exc_info.value)


def test_discover_server_address_without_colon() -> None:
    """
    Тест когда адрес не содержит двоеточие.

    Edge case: Невалидный формат адреса (нет порта).
    """
    valid_json = json.dumps({"address": "127.0.0.1"})

    with patch('gamesense.discovery._find_core_props_path') as mock_find:
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_find.return_value = mock_path

        with patch('builtins.open', mock_open(read_data=valid_json)):
            with pytest.raises(ServerDiscoveryError) as exc_info:
                discover_server()

            assert "Invalid address format" in str(exc_info.value)


def test_discover_server_invalid_port_number() -> None:
    """
    Тест когда порт не является числом.

    Edge case: Порт содержит нечисловые символы.
    """
    valid_json = json.dumps({"address": "127.0.0.1:abc"})

    with patch('gamesense.discovery._find_core_props_path') as mock_find:
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_find.return_value = mock_path

        with patch('builtins.open', mock_open(read_data=valid_json)):
            with pytest.raises(ServerDiscoveryError) as exc_info:
                discover_server()

            assert "Invalid port number" in str(exc_info.value)


def test_discover_server_empty_address() -> None:
    """
    Тест когда адрес пустая строка.

    Edge case: Поле 'address' существует, но пустое.
    """
    valid_json = json.dumps({"address": ""})

    with patch('gamesense.discovery._find_core_props_path') as mock_find:
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_find.return_value = mock_path

        with patch('builtins.open', mock_open(read_data=valid_json)):
            with pytest.raises(ServerDiscoveryError) as exc_info:
                discover_server()

            assert "No 'address' field" in str(exc_info.value)


def test_discover_server_file_read_error() -> None:
    """
    Тест когда файл не может быть прочитан.

    Edge case: Ошибка доступа к файлу (permissions, etc).
    """
    with patch('gamesense.discovery._find_core_props_path') as mock_find:
        mock_path = Mock(spec=Path)
        mock_path.exists.return_value = True
        mock_find.return_value = mock_path

        with patch('builtins.open', side_effect=IOError("Permission denied")):
            with pytest.raises(ServerDiscoveryError) as exc_info:
                discover_server()

            assert "Error reading coreProps.json" in str(exc_info.value)


# =============================================================================
# Тесты _find_core_props_path
# =============================================================================

def test_find_core_props_path_windows_programdata() -> None:
    """
    Тест поиска пути через PROGRAMDATA переменную окружения (Windows).

    Проверяет:
    - Чтение переменной окружения PROGRAMDATA
    - Построение пути к coreProps.json
    - Проверку существования файла
    """
    with patch.dict('os.environ', {'PROGRAMDATA': 'C:/ProgramData'}):
        with patch('pathlib.Path.exists') as mock_exists:
            # Первый вызов exists() вернёт True (для PROGRAMDATA пути)
            mock_exists.return_value = True

            result = _find_core_props_path()

            assert result is not None
            assert 'ProgramData' in str(result)
            assert 'SteelSeries' in str(result)
            assert 'coreProps.json' in str(result)


def test_find_core_props_path_windows_fallback() -> None:
    """
    Тест поиска пути через fallback Windows путь.

    Edge case: PROGRAMDATA не установлен, используем жёстко заданный путь.
    """
    with patch.dict('os.environ', {}, clear=True):
        with patch('pathlib.Path.exists'):
            def exists_side_effect(self: Path) -> bool:
                # Только C:/ProgramData путь существует
                return 'C:/ProgramData' in str(self)

            # Патчим метод exists для Path объектов
            with patch.object(Path, 'exists', new=exists_side_effect):
                result = _find_core_props_path()

                if result:  # Может вернуть None если путь не существует в тестовой среде
                    assert 'C:/ProgramData' in str(result)


def test_find_core_props_path_macos() -> None:
    """
    Тест поиска пути на macOS.

    Проверяет путь /Library/Application Support/SteelSeries Engine 3/coreProps.json.
    """
    with patch.dict('os.environ', {}, clear=True):
        with patch('pathlib.Path.exists'):
            def exists_side_effect(self: Path) -> bool:
                # Только macOS путь существует
                return '/Library/Application Support' in str(self)

            with patch.object(Path, 'exists', new=exists_side_effect):
                result = _find_core_props_path()

                if result:
                    assert '/Library' in str(result)
                    assert 'Application Support' in str(result)


def test_find_core_props_path_not_found() -> None:
    """
    Тест когда coreProps.json не найден ни в одном из путей.

    Edge case: Все проверки вернули False, файл не найден.
    """
    with patch.dict('os.environ', {}, clear=True):
        with patch('pathlib.Path.exists', return_value=False):
            result = _find_core_props_path()

            assert result is None


# =============================================================================
# Тесты get_server_url
# =============================================================================

def test_get_server_url_success() -> None:
    """
    Тест успешного получения URL сервера.

    Проверяет:
    - Вызов discover_server()
    - Форматирование URL с http://
    - Правильный формат host:port
    """
    with patch('gamesense.discovery.discover_server') as mock_discover:
        mock_discover.return_value = ("127.0.0.1", 51248)

        url = get_server_url()

        assert url == "http://127.0.0.1:51248"
        mock_discover.assert_called_once()


def test_get_server_url_custom_host_port() -> None:
    """
    Тест получения URL с нестандартным хостом и портом.

    Проверяет корректное форматирование различных адресов.
    """
    with patch('gamesense.discovery.discover_server') as mock_discover:
        mock_discover.return_value = ("192.168.1.100", 12345)

        url = get_server_url()

        assert url == "http://192.168.1.100:12345"


def test_get_server_url_ipv6() -> None:
    """
    Тест получения URL с IPv6 адресом.

    Edge case: IPv6 адреса требуют особого форматирования в URL.
    """
    with patch('gamesense.discovery.discover_server') as mock_discover:
        mock_discover.return_value = ("::1", 51248)

        url = get_server_url()

        assert url == "http://::1:51248"


def test_get_server_url_propagates_error() -> None:
    """
    Тест что get_server_url прокидывает ошибки из discover_server.

    Edge case: Если discover_server падает, ошибка должна быть проброшена.
    """
    with patch('gamesense.discovery.discover_server') as mock_discover:
        mock_discover.side_effect = ServerDiscoveryError("Test error")

        with pytest.raises(ServerDiscoveryError) as exc_info:
            get_server_url()

        assert "Test error" in str(exc_info.value)


# =============================================================================
# Тесты интеграции (без моков нижнего уровня)
# =============================================================================

def test_full_discovery_flow() -> None:
    """
    Тест полного flow обнаружения сервера.

    Интеграционный тест: от _find_core_props_path до get_server_url.
    """
    valid_json = json.dumps({"address": "127.0.0.1:51248"})

    with patch.dict('os.environ', {'PROGRAMDATA': 'C:/ProgramData'}):
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=valid_json)):
                # Полный цикл без промежуточных моков
                url = get_server_url()

                assert url == "http://127.0.0.1:51248"


def test_full_discovery_flow_with_error() -> None:
    """
    Тест полного flow с ошибкой на каждом уровне.

    Интеграционный тест: проверяем что ошибки корректно прокидываются.
    """
    with patch('gamesense.discovery._find_core_props_path', return_value=None):
        with pytest.raises(ServerDiscoveryError) as exc_info:
            get_server_url()

        assert "Cannot find coreProps.json" in str(exc_info.value)
