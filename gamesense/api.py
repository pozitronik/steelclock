"""
Клиент для взаимодействия с SteelSeries GameSense API.
Реализует регистрацию игры, биндинг событий и отправку данных на дисплей.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import requests  # type: ignore[import-untyped]

from .discovery import get_server_url

logger = logging.getLogger(__name__)


class GameSenseAPIError(Exception):
    """Ошибка при работе с GameSense API"""
    pass


class GameSenseAPI:
    """
    Клиент для взаимодействия с SteelSeries GameSense API.

    Управляет регистрацией приложения, биндингом событий и отправкой
    данных на OLED дисплей клавиатуры.
    """

    def __init__(self, game_name: str = "STEELCLOCK", game_display_name: str = "SteelClock"):
        """
        Инициализирует API клиент.

        Args:
            game_name: Внутреннее имя игры (A-Z, 0-9, дефис, подчёркивание)
            game_display_name: Отображаемое имя игры
        """
        self.game_name = game_name
        self.game_display_name = game_display_name
        self.base_url = get_server_url()
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})

        # Короткий таймаут для fire-and-forget паттерна (как в SDK примере)
        self.timeout = 0.5

        logger.info(f"GameSense API initialized: {self.base_url}")

    def register_game(self, developer: str = "Custom") -> bool:
        """
        Регистрирует игру в SteelSeries Engine.

        Args:
            developer: Имя разработчика

        Returns:
            bool: True если регистрация успешна

        Raises:
            GameSenseAPIError: При ошибке регистрации
        """
        payload = {
            "game": self.game_name,
            "game_display_name": self.game_display_name,
            "developer": developer
        }

        try:
            _ = self._post('/game_metadata', payload)
            logger.info(f"Game registered: {self.game_name}")
            return True
        except GameSenseAPIError as e:
            logger.error(f"Failed to register game: {e}")
            raise

    def bind_screen_event(
        self,
        event_name: str,
        device_type: str = "screened-128x40"
    ) -> bool:
        """
        Создаёт биндинг для отображения на экране.

        Args:
            event_name: Имя события (A-Z, 0-9, дефис, подчёркивание)
            device_type: Тип устройства (screened-128x40 для APEX 7)

        Returns:
            bool: True если биндинг создан успешно

        Raises:
            GameSenseAPIError: При ошибке биндинга
        """
        # Создаём IMAGE binding с дефолтным чёрным экраном (640 нулей)
        # Затем события могут переопределять его через frame["image-data-128x40"]
        # Согласно SDK: "context frame data sent for any IMAGE BINDING can include
        # image data in specific keys to show instead of the default image"
        # Важно: image-data ДОЛЖЕН быть валидным массивом (640 байт для 128x40),
        # пустой массив вызывает HTTP 500
        default_blank_screen = [0] * 640  # Чёрный экран по умолчанию

        payload = {
            "game": self.game_name,
            "event": event_name,
            "value_optional": True,  # Значение опционально, данные в frame
            "handlers": [
                {
                    "device-type": device_type,
                    "zone": "one",
                    "mode": "screen",
                    "datas": [
                        {
                            "has-text": False,        # Это IMAGE binding
                            "image-data": default_blank_screen  # Валидный дефолт (будет переопределён)
                        }
                    ]
                }
            ]
        }

        try:
            _ = self._post('/bind_game_event', payload)
            logger.info(f"Event bound: {event_name}")
            return True
        except GameSenseAPIError as e:
            logger.error(f"Failed to bind event: {e}")
            raise

    def send_screen_data(
        self,
        event_name: str,
        bitmap_data: List[int]
    ) -> bool:
        """
        Отправляет bitmap данные на дисплей.

        Args:
            event_name: Имя события (должно быть забинджено ранее)
            bitmap_data: Массив байтов (640 байт для 128x40 monochrome)

        Returns:
            bool: True если отправка успешна

        Raises:
            GameSenseAPIError: При ошибке отправки
        """
        if len(bitmap_data) != 640:
            raise GameSenseAPIError(
                f"Invalid bitmap size: expected 640 bytes, got {len(bitmap_data)}"
            )

        payload = {
            "game": self.game_name,
            "event": event_name,
            "data": {
                "value": 1,  # Dummy value, т.к. value_optional=True
                "frame": {
                    "image-data-128x40": bitmap_data
                }
            }
        }

        try:
            self._post('/game_event', payload)
            return True
        except GameSenseAPIError as e:
            # Не логируем каждый frame error, только критичные
            if "Connection" in str(e):
                logger.error(f"Failed to send screen data: {e}")
            raise

    def heartbeat(self) -> bool:
        """
        Отправляет heartbeat для поддержания соединения.

        Returns:
            bool: True если heartbeat успешен

        Raises:
            GameSenseAPIError: При ошибке heartbeat
        """
        payload = {
            "game": self.game_name
        }

        try:
            self._post('/game_heartbeat', payload)
            return True
        except GameSenseAPIError as e:
            logger.warning(f"Heartbeat failed: {e}")
            raise

    def remove_game(self) -> bool:
        """
        Удаляет регистрацию игры из SteelSeries Engine.

        Returns:
            bool: True если удаление успешно
        """
        payload = {
            "game": self.game_name
        }

        try:
            self._post('/remove_game', payload)
            logger.info(f"Game removed: {self.game_name}")
            return True
        except GameSenseAPIError:
            # Игнорируем ошибки при cleanup
            return False

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Выполняет POST запрос к API.

        Args:
            endpoint: Endpoint (например '/game_metadata')
            payload: JSON payload

        Returns:
            Optional[Dict[str, Any]]: Ответ от сервера или None

        Raises:
            GameSenseAPIError: При HTTP ошибке
        """
        url = f"{self.base_url}{endpoint}"

        try:
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout
            )

            # GameSense API возвращает разные коды:
            # 200 - успех
            # 400 - bad request
            # 404 - не найдено
            # 500 - внутренняя ошибка сервера
            if response.status_code == 200:
                try:
                    result: Any = response.json()
                    # API обычно возвращает dict, но может быть и None
                    if result is None or isinstance(result, dict):
                        return result
                    # Если вернули что-то другое, оборачиваем в dict
                    return {"data": result}
                except json.JSONDecodeError:
                    return None
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                raise GameSenseAPIError(error_msg)

        except requests.exceptions.Timeout:
            # Timeout может быть нормальным для fire-and-forget паттерна
            return None
        except requests.exceptions.ConnectionError as e:
            raise GameSenseAPIError(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            raise GameSenseAPIError(f"Request error: {e}")

    def __enter__(self) -> "GameSenseAPI":
        """Context manager вход"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager выход - cleanup"""
        try:
            self.remove_game()
        except Exception:
            pass
        self.session.close()
