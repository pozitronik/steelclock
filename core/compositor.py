"""
Compositor - главный цикл рендеринга для OLED дисплея.
Композирует виджеты и отправляет кадры на дисплей с частотой 10Hz.
"""

import logging
import threading
import time
from typing import Any, Dict, Optional

from .layout_manager import LayoutManager
from gamesense.api import GameSenseAPI, GameSenseAPIError
from utils.bitmap import image_to_bytes

logger = logging.getLogger(__name__)


class Compositor:
    """
    Управляет циклом рендеринга и отправкой кадров на дисплей.

    Запускает отдельный thread который периодически (10Hz):
    1. Запрашивает композицию у Layout Manager
    2. Конвертирует изображение в byte array
    3. Отправляет на дисплей через GameSense API
    """

    def __init__(
            self,
            layout_manager: LayoutManager,
            api: GameSenseAPI,
            refresh_rate_ms: int = 100,
            event_name: str = "DISPLAY"
    ):
        """
        Инициализирует Compositor.

        Args:
            layout_manager: Layout Manager для композиции виджетов
            api: GameSense API клиент
            refresh_rate_ms: Частота обновления в миллисекундах (по умолчанию 100ms = 10Hz)
            event_name: Имя события для GameSense API
        """
        self.layout_manager = layout_manager
        self.api = api
        self.refresh_rate_ms = refresh_rate_ms
        self.event_name = event_name

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

        # Статистика
        self._frame_count = 0
        self._error_count = 0
        self._last_error_time = 0.0

        logger.info(f"Compositor initialized: refresh rate {refresh_rate_ms}ms")

    def start(self) -> None:
        """
        Запускает цикл рендеринга в отдельном потоке.

        Raises:
            RuntimeError: Если compositor уже запущен
        """
        if self._running:
            raise RuntimeError("Compositor already running")

        self._stop_event.clear()
        self._running = True

        self._thread = threading.Thread(
            target=self._render_loop,
            name="Compositor",
            daemon=True
        )
        self._thread.start()

        logger.info("Compositor started")

    def stop(self, timeout: float = 2.0) -> None:
        """
        Останавливает цикл рендеринга.

        Args:
            timeout: Максимальное время ожидания остановки потока в секундах
        """
        if not self._running:
            return

        self._stop_event.set()
        self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

        logger.info(f"Compositor stopped. Frames rendered: {self._frame_count}, errors: {self._error_count}")

    def is_running(self) -> bool:
        """Возвращает True если compositor запущен"""
        return self._running

    def _render_loop(self) -> None:
        """
        Главный цикл рендеринга (выполняется в отдельном потоке).

        Периодически композитирует виджеты и отправляет на дисплей.
        """
        interval_sec = self.refresh_rate_ms / 1000.0
        next_frame_time = time.time()

        logger.debug("Render loop started")

        while not self._stop_event.is_set():
            try:
                # Ждём до момента следующего кадра
                current_time = time.time()
                sleep_time = next_frame_time - current_time

                if sleep_time > 0:
                    # Используем wait вместо sleep для возможности прерывания
                    if self._stop_event.wait(timeout=sleep_time):
                        break

                # Рендерим кадр
                self._render_frame()

                # Планируем следующий кадр
                next_frame_time += interval_sec

                # Если мы отстали (rendering занял слишком много времени),
                # синхронизируем с текущим временем
                if next_frame_time < time.time():
                    next_frame_time = time.time() + interval_sec

            except Exception as e:
                logger.error(f"Error in render loop: {e}", exc_info=True)
                self._error_count += 1

                # Если слишком много ошибок подряд, замедляем цикл
                if self._error_count > 10:
                    time.sleep(1.0)

        logger.debug("Render loop stopped")

    def _render_frame(self) -> None:
        """
        Рендерит один кадр и отправляет на дисплей.

        Raises:
            Exception: При ошибке композиции или отправки
        """
        try:
            # Композитируем виджеты
            image = self.layout_manager.composite()

            # Конвертируем в byte array
            byte_array = image_to_bytes(image)

            # Отправляем на дисплей
            self.api.send_screen_data(self.event_name, byte_array)

            self._frame_count += 1

            # Логируем каждую 100-ю отрисовку (каждые 10 секунд при 10Hz)
            if self._frame_count % 100 == 0:
                logger.debug(f"Frames rendered: {self._frame_count}")

        except GameSenseAPIError as e:
            # API ошибки логируем только периодически, чтобы не спамить
            current_time = time.time()
            if current_time - self._last_error_time > 5.0:
                logger.warning(f"GameSense API error: {e}")
                self._last_error_time = current_time
            self._error_count += 1

        except Exception as e:
            logger.error(f"Frame rendering error: {e}", exc_info=True)
            self._error_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику работы compositor.

        Returns:
            Dict[str, Any]: Статистика (frame_count, error_count, is_running)
        """
        return {
            'frame_count': self._frame_count,
            'error_count': self._error_count,
            'is_running': self._running,
            'refresh_rate_ms': self.refresh_rate_ms
        }

    def __enter__(self) -> "Compositor":
        """Context manager вход - запускает compositor"""
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager выход - останавливает compositor"""
        self.stop()
