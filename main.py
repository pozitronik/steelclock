#!/usr/bin/env python3
"""
SteelClock - OLED display manager для SteelSeries APEX 7.

Отображает время и системную информацию на OLED дисплее клавиатуры.
"""

import json
import logging
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Dict, List

from gamesense.api import GameSenseAPI, GameSenseAPIError
from gamesense.discovery import ServerDiscoveryError
from core.layout_manager import LayoutManager
from core.compositor import Compositor
from core.widget import Widget
from widgets.clock import ClockWidget


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


class WidgetUpdateThread(threading.Thread):
    """
    Поток для периодического обновления виджета.

    Вызывает widget.update() с интервалом widget.get_update_interval().
    """

    def __init__(self, widget: Widget):
        super().__init__(name=f"Widget-{widget.name}", daemon=True)
        self.widget = widget
        self.stop_event = threading.Event()

    def run(self):
        """Главный цикл обновления виджета"""
        interval = self.widget.get_update_interval()
        logger.debug(f"Widget update thread started: {self.widget.name} (interval={interval}s)")

        while not self.stop_event.is_set():
            try:
                self.widget.update()
            except Exception as e:
                logger.error(f"Error updating widget {self.widget.name}: {e}")

            # Ждём следующего обновления (с возможностью прерывания)
            self.stop_event.wait(timeout=interval)

        logger.debug(f"Widget update thread stopped: {self.widget.name}")

    def stop(self):
        """Останавливает поток обновления"""
        self.stop_event.set()


class SteelClockApp:
    """
    Главное приложение SteelClock.

    Управляет жизненным циклом всех компонентов:
    - GameSense API
    - Layout Manager
    - Widgets
    - Compositor
    """

    def __init__(self, config_path: str = "config.json"):
        """
        Инициализирует приложение.

        Args:
            config_path: Путь к файлу конфигурации
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Компоненты (инициализируются в setup())
        self.api: GameSenseAPI = None
        self.layout_manager: LayoutManager = None
        self.compositor: Compositor = None
        self.widgets: List[Widget] = []
        self.widget_threads: List[WidgetUpdateThread] = []

        # Флаг для graceful shutdown
        self.shutdown_requested = False

        logger.info("SteelClock initialized")

    def _load_config(self) -> Dict:
        """
        Загружает конфигурацию из файла.

        Returns:
            Dict: Конфигурация приложения

        Raises:
            FileNotFoundError: Если файл не найден
            json.JSONDecodeError: Если JSON невалиден
        """
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return self._default_config()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Config loaded from: {self.config_path}")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}")
            raise

    def _default_config(self) -> Dict:
        """
        Возвращает дефолтную конфигурацию.

        Returns:
            Dict: Дефолтная конфигурация
        """
        return {
            "game_name": "STEELCLOCK",
            "game_display_name": "SteelClock",
            "refresh_rate_ms": 100,
            "widgets": [
                {
                    "type": "clock",
                    "format": "%H:%M:%S",
                    "update_interval": 1.0,
                    "font_size": 12
                }
            ]
        }

    def setup(self):
        """
        Инициализирует все компоненты приложения.

        Raises:
            ServerDiscoveryError: Если не найден SteelSeries Engine
            GameSenseAPIError: Если ошибка при работе с API
        """
        logger.info("Setting up SteelClock...")

        # Инициализируем GameSense API
        try:
            self.api = GameSenseAPI(
                game_name=self.config.get("game_name", "STEELCLOCK"),
                game_display_name=self.config.get("game_display_name", "SteelClock")
            )

            # Регистрируем игру
            self.api.register_game()

            # Биндим событие для дисплея
            self.api.bind_screen_event("DISPLAY")

        except ServerDiscoveryError as e:
            logger.error(f"Failed to discover SteelSeries Engine: {e}")
            logger.error("Make sure SteelSeries Engine 3 is installed and running")
            raise
        except GameSenseAPIError as e:
            logger.error(f"Failed to initialize GameSense API: {e}")
            raise

        # Создаём Layout Manager
        self.layout_manager = LayoutManager(width=128, height=40)

        # Создаём виджеты из конфигурации
        widget_configs = self.config.get("widgets", [])
        for widget_config in widget_configs:
            widget = self._create_widget(widget_config)
            if widget:
                self.widgets.append(widget)

        # Добавляем виджеты в layout
        # Для MVP с одним fullscreen clock просто добавляем на (0, 0)
        for widget in self.widgets:
            self.layout_manager.add_widget(
                widget,
                x=0, y=0,
                w=128, h=40,
                z_order=0
            )

        # Создаём Compositor
        refresh_rate_ms = self.config.get("refresh_rate_ms", 100)
        self.compositor = Compositor(
            layout_manager=self.layout_manager,
            api=self.api,
            refresh_rate_ms=refresh_rate_ms,
            event_name="DISPLAY"
        )

        logger.info("Setup completed successfully")

    def _create_widget(self, config: Dict) -> Widget:
        """
        Создаёт виджет из конфигурации.

        Args:
            config: Конфигурация виджета

        Returns:
            Widget: Экземпляр виджета или None при ошибке
        """
        widget_type = config.get("type")

        try:
            if widget_type == "clock":
                return ClockWidget(
                    name=config.get("name", "Clock"),
                    format_string=config.get("format", "%H:%M:%S"),
                    update_interval=config.get("update_interval", 1.0),
                    font_size=config.get("font_size", 12)
                )
            else:
                logger.error(f"Unknown widget type: {widget_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to create widget {widget_type}: {e}")
            return None

    def run(self):
        """
        Запускает приложение.

        Запускает потоки обновления виджетов и compositor,
        затем ждёт сигнала завершения.
        """
        logger.info("Starting SteelClock...")

        # Запускаем потоки обновления виджетов
        for widget in self.widgets:
            thread = WidgetUpdateThread(widget)
            thread.start()
            self.widget_threads.append(thread)

        # Запускаем compositor
        self.compositor.start()

        logger.info("SteelClock is running. Press Ctrl+C to stop.")

        # Главный цикл - просто ждём сигнала завершения
        try:
            while not self.shutdown_requested:
                time.sleep(1.0)

                # Периодически отправляем heartbeat
                try:
                    self.api.heartbeat()
                except Exception as e:
                    logger.debug(f"Heartbeat error (non-critical): {e}")

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")

        self.shutdown()

    def shutdown(self):
        """
        Останавливает приложение и очищает ресурсы.
        """
        if self.shutdown_requested:
            return

        logger.info("Shutting down SteelClock...")
        self.shutdown_requested = True

        # Останавливаем compositor
        if self.compositor:
            self.compositor.stop()

        # Останавливаем потоки обновления виджетов
        for thread in self.widget_threads:
            thread.stop()

        # Ждём завершения потоков
        for thread in self.widget_threads:
            thread.join(timeout=1.0)

        # Удаляем регистрацию игры
        if self.api:
            try:
                self.api.remove_game()
            except Exception:
                pass

        logger.info("SteelClock stopped")

    def signal_handler(self, signum, frame):
        """
        Обработчик системных сигналов (SIGINT, SIGTERM).
        """
        logger.info(f"Received signal {signum}")
        self.shutdown_requested = True


def main():
    """Точка входа в приложение"""
    logger.info("=" * 60)
    logger.info("SteelClock - OLED Display Manager for SteelSeries APEX 7")
    logger.info("=" * 60)

    # Путь к конфигу
    config_path = Path(__file__).parent / "config.json"

    try:
        # Создаём приложение
        app = SteelClockApp(config_path=str(config_path))

        # Регистрируем обработчики сигналов
        signal.signal(signal.SIGINT, app.signal_handler)
        signal.signal(signal.SIGTERM, app.signal_handler)

        # Инициализируем
        app.setup()

        # Запускаем
        app.run()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except ServerDiscoveryError:
        logger.error("Cannot connect to SteelSeries Engine")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
