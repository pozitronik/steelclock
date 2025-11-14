#!/usr/bin/env python3
"""
SteelClock - OLED display manager для SteelSeries APEX 7.

Поддерживает:
- Множественные экземпляры виджетов
- Настройку позиции, размера, z-order через конфиг
- Стилизацию виджетов (фон, рамки)
- Фон дисплея
- Виртуальный канвас / viewport (опционально)
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
from widgets.cpu import CPUWidget
from widgets.memory import MemoryWidget
from widgets.network import NetworkWidget
from widgets.disk import DiskWidget


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


class WidgetUpdateThread(threading.Thread):
    """Поток для периодического обновления виджета."""

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

            self.stop_event.wait(timeout=interval)

        logger.debug(f"Widget update thread stopped: {self.widget.name}")

    def stop(self):
        """Останавливает поток обновления"""
        self.stop_event.set()


class SteelClockApp:
    """
    Главное приложение SteelClock.

    Поддерживает расширенную конфигурацию через JSON.
    """

    def __init__(self, config_path: str = "configs/config.json"):
        """
        Инициализирует приложение.

        Args:
            config_path: Путь к файлу конфигурации
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Компоненты (инициализируются в setup())
        self.api: GameSenseAPI = None
        self.layout_manager = None
        self.compositor: Compositor = None
        self.widgets: List[Widget] = []
        self.widget_threads: List[WidgetUpdateThread] = []

        # Флаг для graceful shutdown
        self.shutdown_requested = False

        logger.info("SteelClock initialized")

    def _load_config(self) -> Dict:
        """Загружает конфигурацию из файла."""
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
        """Возвращает дефолтную конфигурацию."""
        return {
            "game_name": "STEELCLOCK",
            "game_display_name": "SteelClock",
            "refresh_rate_ms": 100,
            "display": {
                "width": 128,
                "height": 40,
                "background_color": 0
            },
            "layout": {
                "type": "basic"
            },
            "widgets": [
                {
                    "type": "clock",
                    "id": "main_clock",
                    "enabled": True,
                    "position": {"x": 0, "y": 0, "w": 128, "h": 40, "z_order": 0},
                    "style": {"background_color": 0, "border": False, "border_color": 255},
                    "properties": {"format": "%H:%M:%S", "font_size": 12, "update_interval": 1.0}
                }
            ]
        }

    def setup(self):
        """Инициализирует все компоненты приложения."""
        logger.info("Setting up SteelClock...")

        # Инициализируем GameSense API
        try:
            self.api = GameSenseAPI(
                game_name=self.config.get("game_name", "STEELCLOCK"),
                game_display_name=self.config.get("game_display_name", "SteelClock")
            )

            self.api.register_game()
            self.api.bind_screen_event("DISPLAY")

        except ServerDiscoveryError as e:
            logger.error(f"Failed to discover SteelSeries Engine: {e}")
            raise
        except GameSenseAPIError as e:
            logger.error(f"Failed to initialize GameSense API: {e}")
            raise

        # Создаём Layout Manager (обычный или с viewport)
        display_config = self.config.get("display", {})
        layout_config = self.config.get("layout", {})

        display_width = display_config.get("width", 128)
        display_height = display_config.get("height", 40)
        background_color = display_config.get("background_color", 0)

        # Создаём LayoutManager (автоматически определяет режим)
        virtual_width = layout_config.get("virtual_width")
        virtual_height = layout_config.get("virtual_height")

        self.layout_manager = LayoutManager(
            width=display_width,
            height=display_height,
            virtual_width=virtual_width,
            virtual_height=virtual_height,
            background_color=background_color
        )

        # Создаём виджеты из конфигурации
        widget_configs = self.config.get("widgets", [])
        for widget_config in widget_configs:
            # Пропускаем отключённые виджеты
            if not widget_config.get("enabled", True):
                continue

            widget = self._create_widget_from_config(widget_config)
            if widget:
                self.widgets.append(widget)

                # Добавляем виджет в layout с параметрами из конфига
                position = widget_config.get("position", {})
                self.layout_manager.add_widget(
                    widget,
                    x=position.get("x", 0),
                    y=position.get("y", 0),
                    w=position.get("w", 128),
                    h=position.get("h", 40),
                    z_order=position.get("z_order", 0)
                )

        # Создаём Compositor
        refresh_rate_ms = self.config.get("refresh_rate_ms", 100)
        self.compositor = Compositor(
            layout_manager=self.layout_manager,
            api=self.api,
            refresh_rate_ms=refresh_rate_ms,
            event_name="DISPLAY"
        )

        logger.info(f"Setup completed: {len(self.widgets)} widgets loaded")

    def _create_widget_from_config(self, config: Dict) -> Widget:
        """
        Создаёт виджет из конфигурации.

        Args:
            config: Конфигурация виджета

        Returns:
            Widget: Экземпляр виджета или None при ошибке
        """
        widget_type = config.get("type")
        widget_id = config.get("id", f"{widget_type}_auto")
        properties = config.get("properties", {})
        style = config.get("style", {})

        try:
            if widget_type == "clock":
                return ClockWidget(
                    name=widget_id,
                    format_string=properties.get("format", "%H:%M:%S"),
                    update_interval=properties.get("update_interval", 1.0),
                    font_size=properties.get("font_size", 12),
                    font=properties.get("font"),
                    background_color=style.get("background_color", 0),
                    background_opacity=style.get("background_opacity", 255),
                    border=style.get("border", False),
                    border_color=style.get("border_color", 255),
                    horizontal_align=properties.get("horizontal_align", "center"),
                    vertical_align=properties.get("vertical_align", "center"),
                    padding=properties.get("padding", 0)
                )
            elif widget_type == "cpu":
                return CPUWidget(
                    name=widget_id,
                    display_mode=properties.get("display_mode", "bar_horizontal"),
                    per_core=properties.get("per_core", False),
                    update_interval=properties.get("update_interval", 1.0),
                    history_length=properties.get("history_length", 30),
                    font=properties.get("font", None),
                    font_size=properties.get("font_size", 10),
                    horizontal_align=properties.get("horizontal_align", "center"),
                    vertical_align=properties.get("vertical_align", "center"),
                    background_color=style.get("background_color", 0),
                    background_opacity=style.get("background_opacity", 255),
                    border=style.get("border", False),
                    border_color=style.get("border_color", 255),
                    padding=style.get("padding", 0),
                    bar_border=properties.get("bar_border", False),
                    bar_margin=properties.get("bar_margin", 0),
                    fill_color=properties.get("fill_color", 255)
                )
            elif widget_type == "memory":
                return MemoryWidget(
                    name=widget_id,
                    display_mode=properties.get("display_mode", "bar_horizontal"),
                    update_interval=properties.get("update_interval", 1.0),
                    history_length=properties.get("history_length", 30),
                    font=properties.get("font", None),
                    font_size=properties.get("font_size", 10),
                    horizontal_align=properties.get("horizontal_align", "center"),
                    vertical_align=properties.get("vertical_align", "center"),
                    background_color=style.get("background_color", 0),
                    background_opacity=style.get("background_opacity", 255),
                    border=style.get("border", False),
                    border_color=style.get("border_color", 255),
                    padding=style.get("padding", 0),
                    bar_border=properties.get("bar_border", False),
                    fill_color=properties.get("fill_color", 255)
                )
            elif widget_type == "network":
                return NetworkWidget(
                    name=widget_id,
                    interface=properties.get("interface", "eth0"),
                    display_mode=properties.get("display_mode", "bar_horizontal"),
                    update_interval=properties.get("update_interval", 1.0),
                    history_length=properties.get("history_length", 30),
                    max_speed_mbps=properties.get("max_speed_mbps", 100.0),
                    speed_unit=properties.get("speed_unit", "kbps"),
                    font=properties.get("font", None),
                    font_size=properties.get("font_size", 10),
                    horizontal_align=properties.get("horizontal_align", "center"),
                    vertical_align=properties.get("vertical_align", "center"),
                    background_color=style.get("background_color", 0),
                    background_opacity=style.get("background_opacity", 255),
                    border=style.get("border", False),
                    border_color=style.get("border_color", 255),
                    padding=style.get("padding", 0),
                    bar_border=properties.get("bar_border", False),
                    bar_margin=properties.get("bar_margin", 1),
                    rx_color=properties.get("rx_color", 255),
                    tx_color=properties.get("tx_color", 128)
                )
            elif widget_type == "disk":
                return DiskWidget(
                    name=widget_id,
                    disk_name=properties.get("disk_name", None),
                    display_mode=properties.get("display_mode", "bar_horizontal"),
                    update_interval=properties.get("update_interval", 1.0),
                    history_length=properties.get("history_length", 30),
                    max_speed_mbps=properties.get("max_speed_mbps", -1),
                    font=properties.get("font", None),
                    font_size=properties.get("font_size", 10),
                    horizontal_align=properties.get("horizontal_align", "center"),
                    vertical_align=properties.get("vertical_align", "center"),
                    background_color=style.get("background_color", 0),
                    background_opacity=style.get("background_opacity", 255),
                    border=style.get("border", False),
                    border_color=style.get("border_color", 255),
                    padding=style.get("padding", 0),
                    bar_border=properties.get("bar_border", False),
                    read_color=properties.get("read_color", 255),
                    write_color=properties.get("write_color", 200)
                )
            else:
                logger.error(f"Unknown widget type: {widget_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to create widget {widget_type}/{widget_id}: {e}")
            return None

    def run(self):
        """Запускает приложение."""
        logger.info("Starting SteelClock...")

        # Запускаем потоки обновления виджетов
        for widget in self.widgets:
            thread = WidgetUpdateThread(widget)
            thread.start()
            self.widget_threads.append(thread)

        # Запускаем compositor
        self.compositor.start()

        logger.info("SteelClock is running. Press Ctrl+C to stop.")

        # Главный цикл
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
        """Останавливает приложение и очищает ресурсы."""
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
        """Обработчик системных сигналов."""
        logger.info(f"Received signal {signum}")
        self.shutdown_requested = True


def main():
    """Точка входа в приложение"""
    logger.info("=" * 60)
    logger.info("SteelClock - OLED Display Manager for SteelSeries APEX 7")
    logger.info("=" * 60)

    # Путь к конфигу (можно передать как аргумент)
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = Path(__file__).parent / "configs/config.json"

    try:
        app = SteelClockApp(config_path=str(config_path))

        # Регистрируем обработчики сигналов
        signal.signal(signal.SIGINT, app.signal_handler)
        signal.signal(signal.SIGTERM, app.signal_handler)

        app.setup()
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
