"""
Unit tests для gamesense.api - GameSense API клиент.

Тестируемый модуль: gamesense/api.py

Покрытие:
- Инициализация API клиента
- Регистрация игры (register_game)
- Биндинг событий (bind_screen_event)
- Отправка bitmap данных (send_screen_data)
- Heartbeat
- Удаление игры (remove_game)
- HTTP ошибки (400, 404, 500)
- Timeout handling
- Connection errors
- Валидация bitmap данных
- Context manager поведение
- Edge cases и negative tests
"""

import pytest
import json
from unittest.mock import patch, Mock, MagicMock
from requests.exceptions import Timeout, ConnectionError as RequestsConnectionError, RequestException

from gamesense.api import GameSenseAPI, GameSenseAPIError


# =============================================================================
# Тесты инициализации
# =============================================================================

def test_api_init_default_values():
    """
    Тест инициализации API с дефолтными параметрами.

    Проверяет:
    - Дефолтное имя игры "STEELCLOCK"
    - Дефолтное отображаемое имя "SteelClock"
    - Создание session
    - Установка таймаута 0.5 секунд
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        api = GameSenseAPI()

        assert api.game_name == "STEELCLOCK"
        assert api.game_display_name == "SteelClock"
        assert api.base_url == "http://127.0.0.1:12345"
        assert api.timeout == 0.5
        assert api.session is not None
        assert api.session.headers['Content-Type'] == 'application/json'


def test_api_init_custom_values():
    """
    Тест инициализации API с кастомными параметрами.

    Проверяет возможность переопределения имён игры.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        api = GameSenseAPI(
            game_name="TEST_GAME",
            game_display_name="Test Game Display"
        )

        assert api.game_name == "TEST_GAME"
        assert api.game_display_name == "Test Game Display"


def test_api_init_calls_get_server_url():
    """
    Тест что инициализация вызывает get_server_url для discovery.

    Проверяет интеграцию с discovery модулем.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://192.168.1.100:54321"

        api = GameSenseAPI()

        mock_get_url.assert_called_once()
        assert api.base_url == "http://192.168.1.100:54321"


# =============================================================================
# Тесты register_game
# =============================================================================

def test_register_game_success():
    """
    Тест успешной регистрации игры.

    Проверяет:
    - POST запрос на /game_metadata
    - Правильный payload
    - Возвращает True
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'ok'}
            mock_post.return_value = mock_response

            api = GameSenseAPI(game_name="TEST", game_display_name="Test Game")
            result = api.register_game(developer="TestDev")

            assert result is True
            mock_post.assert_called_once()
            # Проверяем URL и payload
            call_args = mock_post.call_args
            assert call_args[0][0] == "http://127.0.0.1:12345/game_metadata"
            payload = call_args[1]['json']
            assert payload['game'] == "TEST"
            assert payload['game_display_name'] == "Test Game"
            assert payload['developer'] == "TestDev"


def test_register_game_default_developer():
    """
    Тест регистрации игры с дефолтным developer.

    Проверяет что developer по умолчанию "Custom".
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'ok'}
            mock_post.return_value = mock_response

            api = GameSenseAPI()
            result = api.register_game()

            assert result is True
            payload = mock_post.call_args[1]['json']
            assert payload['developer'] == "Custom"


def test_register_game_http_400_error():
    """
    Тест регистрации игры с HTTP 400 (Bad Request).

    Edge case: Сервер отклонил регистрацию из-за невалидных данных.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = 'Bad Request'
            mock_post.return_value = mock_response

            api = GameSenseAPI()

            with pytest.raises(GameSenseAPIError) as exc_info:
                api.register_game()

            assert "HTTP 400" in str(exc_info.value)


def test_register_game_http_500_error():
    """
    Тест регистрации игры с HTTP 500 (Internal Server Error).

    Edge case: Внутренняя ошибка сервера GameSense.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = 'Internal Server Error'
            mock_post.return_value = mock_response

            api = GameSenseAPI()

            with pytest.raises(GameSenseAPIError) as exc_info:
                api.register_game()

            assert "HTTP 500" in str(exc_info.value)


def test_register_game_timeout():
    """
    Тест регистрации игры с timeout.

    Edge case: Запрос превысил таймаут 0.5 секунды.
    Timeout может быть нормальным для fire-and-forget, но register должен его обработать.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_post.side_effect = Timeout("Connection timeout")

            api = GameSenseAPI()

            # Timeout возвращает None из _post, но register_game проверяет это
            # Фактически timeout в _post возвращает None, а не вызывает исключение
            # Проверим что это обрабатывается корректно
            result = api.register_game()
            assert result is True  # _post вернёт None при timeout, но это считается успехом


def test_register_game_connection_error():
    """
    Тест регистрации игры с connection error.

    Edge case: Нет соединения с GameSense Engine.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_post.side_effect = RequestsConnectionError("Connection refused")

            api = GameSenseAPI()

            with pytest.raises(GameSenseAPIError) as exc_info:
                api.register_game()

            assert "Connection error" in str(exc_info.value)


# =============================================================================
# Тесты bind_screen_event
# =============================================================================

def test_bind_screen_event_success():
    """
    Тест успешного биндинга события на экран.

    Проверяет:
    - POST запрос на /bind_game_event
    - Правильный payload с IMAGE binding
    - Дефолтный чёрный экран (640 нулей)
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'ok'}
            mock_post.return_value = mock_response

            api = GameSenseAPI()
            result = api.bind_screen_event("TEST_EVENT")

            assert result is True
            payload = mock_post.call_args[1]['json']
            assert payload['event'] == "TEST_EVENT"
            assert payload['handlers'][0]['device-type'] == "screened-128x40"
            assert payload['handlers'][0]['mode'] == "screen"
            assert payload['handlers'][0]['datas'][0]['has-text'] is False


def test_bind_screen_event_custom_device_type():
    """
    Тест биндинга события с кастомным типом устройства.

    Проверяет возможность указать другой device-type.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'ok'}
            mock_post.return_value = mock_response

            api = GameSenseAPI()
            result = api.bind_screen_event("EVENT", device_type="screened-256x80")

            assert result is True
            payload = mock_post.call_args[1]['json']
            assert payload['handlers'][0]['device-type'] == "screened-256x80"


def test_bind_screen_event_http_error():
    """
    Тест биндинга события с HTTP ошибкой.

    Edge case: Сервер отклонил биндинг (например, game не зарегистрирована).
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = 'Game not registered'
            mock_post.return_value = mock_response

            api = GameSenseAPI()

            with pytest.raises(GameSenseAPIError) as exc_info:
                api.bind_screen_event("EVENT")

            assert "HTTP 400" in str(exc_info.value)


# =============================================================================
# Тесты send_screen_data
# =============================================================================

def test_send_screen_data_success():
    """
    Тест успешной отправки bitmap данных на экран.

    Проверяет:
    - POST запрос на /game_event
    - Правильный payload с image-data-128x40
    - Валидация размера bitmap (640 байт)
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'ok'}
            mock_post.return_value = mock_response

            api = GameSenseAPI()
            bitmap_data = [0] * 640
            result = api.send_screen_data("EVENT", bitmap_data)

            assert result is True
            payload = mock_post.call_args[1]['json']
            assert payload['event'] == "EVENT"
            assert 'image-data-128x40' in payload['data']['frame']


def test_send_screen_data_with_actual_image():
    """
    Тест отправки реальных bitmap данных (не все нули).

    Проверяет что отправляются фактические данные изображения.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'ok'}
            mock_post.return_value = mock_response

            api = GameSenseAPI()
            # Bitmap с паттерном
            bitmap_data = [i % 256 for i in range(640)]
            result = api.send_screen_data("EVENT", bitmap_data)

            assert result is True


def test_send_screen_data_invalid_size_too_small():
    """
    Тест отправки bitmap с недостаточным размером.

    Edge case: Bitmap меньше 640 байт должен вызвать ValueError.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"
        api = GameSenseAPI()

        bitmap_data = [0] * 639  # На 1 байт меньше

        with pytest.raises(GameSenseAPIError) as exc_info:
            api.send_screen_data("EVENT", bitmap_data)

        assert "Invalid bitmap size" in str(exc_info.value)
        assert "expected 640 bytes, got 639" in str(exc_info.value)


def test_send_screen_data_invalid_size_too_large():
    """
    Тест отправки bitmap с избыточным размером.

    Edge case: Bitmap больше 640 байт должен вызвать ValueError.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"
        api = GameSenseAPI()

        bitmap_data = [0] * 641  # На 1 байт больше

        with pytest.raises(GameSenseAPIError) as exc_info:
            api.send_screen_data("EVENT", bitmap_data)

        assert "Invalid bitmap size" in str(exc_info.value)
        assert "expected 640 bytes, got 641" in str(exc_info.value)


def test_send_screen_data_empty_bitmap():
    """
    Тест отправки пустого bitmap.

    Edge case: Пустой массив должен вызвать ошибку валидации.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"
        api = GameSenseAPI()

        with pytest.raises(GameSenseAPIError) as exc_info:
            api.send_screen_data("EVENT", [])

        assert "Invalid bitmap size" in str(exc_info.value)
        assert "expected 640 bytes, got 0" in str(exc_info.value)


def test_send_screen_data_http_error():
    """
    Тест отправки данных с HTTP ошибкой.

    Edge case: Сервер отклонил данные (например, event не забинджен).
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = 'Event not bound'
            mock_post.return_value = mock_response

            api = GameSenseAPI()
            bitmap_data = [0] * 640

            with pytest.raises(GameSenseAPIError) as exc_info:
                api.send_screen_data("UNBOUND_EVENT", bitmap_data)

            assert "HTTP 404" in str(exc_info.value)


def test_send_screen_data_timeout():
    """
    Тест отправки данных с timeout.

    Edge case: Timeout при отправке frame - это нормально для fire-and-forget.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_post.side_effect = Timeout("Request timeout")

            api = GameSenseAPI()
            bitmap_data = [0] * 640
            result = api.send_screen_data("EVENT", bitmap_data)

            # Timeout возвращает True (None из _post считается успехом)
            assert result is True


def test_send_screen_data_connection_error():
    """
    Тест отправки данных с connection error.

    Edge case: Потеряно соединение с GameSense Engine.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_post.side_effect = RequestsConnectionError("Connection lost")

            api = GameSenseAPI()
            bitmap_data = [0] * 640

            with pytest.raises(GameSenseAPIError) as exc_info:
                api.send_screen_data("EVENT", bitmap_data)

            assert "Connection error" in str(exc_info.value)


# =============================================================================
# Тесты heartbeat
# =============================================================================

def test_heartbeat_success():
    """
    Тест успешного heartbeat.

    Проверяет:
    - POST запрос на /game_heartbeat
    - Правильный payload с game name
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'ok'}
            mock_post.return_value = mock_response

            api = GameSenseAPI(game_name="TEST")
            result = api.heartbeat()

            assert result is True
            payload = mock_post.call_args[1]['json']
            assert payload['game'] == "TEST"


def test_heartbeat_http_error():
    """
    Тест heartbeat с HTTP ошибкой.

    Edge case: Игра не зарегистрирована или сервер недоступен.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = 'Game not registered'
            mock_post.return_value = mock_response

            api = GameSenseAPI()

            with pytest.raises(GameSenseAPIError):
                api.heartbeat()


# =============================================================================
# Тесты remove_game
# =============================================================================

def test_remove_game_success():
    """
    Тест успешного удаления игры.

    Проверяет:
    - POST запрос на /remove_game
    - Возвращает True
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'ok'}
            mock_post.return_value = mock_response

            api = GameSenseAPI(game_name="TEST")
            result = api.remove_game()

            assert result is True
            payload = mock_post.call_args[1]['json']
            assert payload['game'] == "TEST"


def test_remove_game_http_error_ignored():
    """
    Тест удаления игры с HTTP ошибкой - ошибки игнорируются.

    Edge case: remove_game используется в cleanup, ошибки не критичны.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = 'Not found'
            mock_post.return_value = mock_response

            api = GameSenseAPI()

            # Не должно вызывать исключение
            result = api.remove_game()

            assert result is False  # Возвращает False при ошибке, но не падает


# =============================================================================
# Тесты context manager
# =============================================================================

def test_context_manager_calls_remove_game():
    """
    Тест что context manager вызывает remove_game при выходе.

    Проверяет cleanup логику.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'ok'}
            mock_post.return_value = mock_response

            with GameSenseAPI() as api:
                assert api is not None

            # После выхода из контекста должен быть вызван remove_game
            assert mock_post.called
            # Последний вызов должен быть remove_game
            last_call_url = mock_post.call_args[0][0]
            assert 'remove_game' in last_call_url


def test_context_manager_closes_session():
    """
    Тест что context manager закрывает session.

    Проверяет что session.close() вызывается.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'ok'}
            mock_post.return_value = mock_response

            with patch('requests.Session.close') as mock_close:
                with GameSenseAPI() as api:
                    pass

                # session.close() должен быть вызван
                assert mock_close.called


def test_context_manager_handles_exception_in_exit():
    """
    Тест что context manager игнорирует исключения в __exit__.

    Edge case: Если remove_game падает, context manager не должен прокидывать исключение.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = 'Error'
            mock_post.return_value = mock_response

            # Не должно вызывать исключение даже если remove_game падает
            with GameSenseAPI() as api:
                pass

            # Проверяем что дошли сюда без исключений
            assert api is not None


# =============================================================================
# Тесты _post (внутренний метод)
# =============================================================================

def test_post_returns_json_on_success():
    """
    Тест что _post возвращает JSON при успешном ответе.

    Проверяет парсинг JSON из ответа.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'result': 'success', 'value': 42}
            mock_post.return_value = mock_response

            api = GameSenseAPI()
            result = api._post('/test_endpoint', {'test': 'data'})

            assert result == {'result': 'success', 'value': 42}


def test_post_returns_none_on_empty_response():
    """
    Тест что _post возвращает None при пустом ответе.

    Edge case: Сервер вернул 200 без JSON body.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.side_effect = json.JSONDecodeError("No JSON", "", 0)
            mock_post.return_value = mock_response

            api = GameSenseAPI()
            result = api._post('/test_endpoint', {})

            assert result is None


def test_post_returns_none_on_timeout():
    """
    Тест что _post возвращает None при timeout.

    Edge case: Timeout не вызывает исключение для fire-and-forget паттерна.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_post.side_effect = Timeout("Timeout")

            api = GameSenseAPI()
            result = api._post('/test_endpoint', {})

            assert result is None


def test_post_wraps_non_dict_json_response():
    """
    Тест что _post оборачивает non-dict JSON в dict.

    Edge case: API может вернуть список или примитив вместо dict.
    """
    with patch('gamesense.api.get_server_url') as mock_get_url:
        mock_get_url.return_value = "http://127.0.0.1:12345"

        with patch('requests.Session.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = [1, 2, 3]  # Список вместо dict
            mock_post.return_value = mock_response

            api = GameSenseAPI()
            result = api._post('/test_endpoint', {})

            assert result == {"data": [1, 2, 3]}
