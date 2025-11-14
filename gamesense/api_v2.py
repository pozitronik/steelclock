"""
Альтернативная версия API с другим подходом к биндингу экрана.
"""

from .api import GameSenseAPI, GameSenseAPIError
import logging

logger = logging.getLogger(__name__)


class GameSenseAPIv2(GameSenseAPI):
    """
    Альтернативная версия API клиента с упрощённым биндингом для raw bitmap.
    """

    def bind_screen_event_v2(
        self,
        event_name: str,
        device_type: str = "screened-128x40"
    ) -> bool:
        """
        Альтернативный метод биндинга - без image-data в хэндлере.

        Согласно SDK, image-data должно быть только в event data,
        а в хэндлере может быть пустой datas array с context-frame-key.
        """
        payload = {
            "game": self.game_name,
            "event": event_name,
            "value_optional": True,
            "handlers": [
                {
                    "device-type": device_type,
                    "zone": "one",
                    "mode": "screen",
                    "datas": [
                        {
                            # Указываем что будем брать данные из frame
                            "context-frame-key": "image-data-128x40"
                        }
                    ]
                }
            ]
        }

        try:
            response = self._post('/bind_game_event', payload)
            logger.info(f"Event bound (v2): {event_name}")
            return True
        except GameSenseAPIError as e:
            logger.error(f"Failed to bind event (v2): {e}")
            raise

    def bind_screen_event_v3(
        self,
        event_name: str,
        device_type: str = "screened-128x40"
    ) -> bool:
        """
        Ещё одна попытка - используем register_game_event вместо bind_game_event.
        """
        # Сначала регистрируем событие
        register_payload = {
            "game": self.game_name,
            "event": event_name,
            "value_optional": True
        }

        try:
            self._post('/register_game_event', register_payload)
            logger.info(f"Event registered: {event_name}")
        except GameSenseAPIError as e:
            logger.warning(f"Event registration failed (may already exist): {e}")

        # Потом биндим хэндлер
        bind_payload = {
            "game": self.game_name,
            "event": event_name,
            "handlers": [
                {
                    "device-type": device_type,
                    "zone": "one",
                    "mode": "screen",
                    "datas": []  # Пустой массив - данные придут в event
                }
            ]
        }

        try:
            response = self._post('/bind_game_event', bind_payload)
            logger.info(f"Event bound (v3): {event_name}")
            return True
        except GameSenseAPIError as e:
            logger.error(f"Failed to bind event (v3): {e}")
            raise
