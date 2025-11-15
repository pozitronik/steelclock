"""
Unit tests для main.py - главное приложение SteelClock.

Тестируемый модуль: main.py

Покрытие:
- WidgetUpdateThread
- SteelClockApp инициализация и конфигурация
- Setup компонентов
- Создание виджетов из конфигурации
- Run/shutdown lifecycle
- Signal handling
- main() entry point
"""

import pytest
import json
import signal
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call, mock_open

# Импортируем после патча
import sys
from typing import Any

# Мокаем все виджеты перед импортом main
@pytest.fixture(autouse=True)
def mock_all_widgets():
    """Автоматически мокируем все виджеты для всех тестов."""
    with patch('main.ClockWidget') as mock_clock, \
         patch('main.CPUWidget') as mock_cpu, \
         patch('main.MemoryWidget') as mock_memory, \
         patch('main.NetworkWidget') as mock_network, \
         patch('main.DiskWidget') as mock_disk, \
         patch('main.KeyboardWidget') as mock_keyboard:

        # Настраиваем моки
        for mock_widget in [mock_clock, mock_cpu, mock_memory, mock_network, mock_disk, mock_keyboard]:
            instance = Mock()
            instance.name = "test_widget"
            instance.get_update_interval.return_value = 1.0
            instance.update = Mock()
            mock_widget.return_value = instance

        yield {
            'clock': mock_clock,
            'cpu': mock_cpu,
            'memory': mock_memory,
            'network': mock_network,
            'disk': mock_disk,
            'keyboard': mock_keyboard
        }


# ===========================
# Фикстуры
# ===========================

@pytest.fixture
def temp_config_file():
    """Фикстура создающая временный файл конфигурации."""
    config_data = {
        "game_name": "TEST_GAME",
        "game_display_name": "Test Game",
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
                "id": "test_clock",
                "enabled": True,
                "position": {"x": 0, "y": 0, "w": 128, "h": 20},
                "properties": {"format": "%H:%M"}
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def mock_api():
    """Фикстура создающая mock GameSenseAPI."""
    with patch('main.GameSenseAPI') as mock_api_class:
        api_instance = Mock()
        api_instance.register_game = Mock()
        api_instance.bind_screen_event = Mock()
        api_instance.heartbeat = Mock()
        api_instance.remove_game = Mock()
        mock_api_class.return_value = api_instance
        yield api_instance


@pytest.fixture
def mock_components():
    """Фикстура мокирующая все основные компоненты."""
    with patch('main.LayoutManager') as mock_layout, \
         patch('main.Compositor') as mock_comp:

        layout_instance = Mock()
        layout_instance.add_widget = Mock()
        mock_layout.return_value = layout_instance

        comp_instance = Mock()
        comp_instance.start = Mock()
        comp_instance.stop = Mock()
        mock_comp.return_value = comp_instance

        yield {
            'layout_manager': layout_instance,
            'compositor': comp_instance
        }


# ===========================
# Тесты WidgetUpdateThread
# ===========================

def test_widget_update_thread_init():
    """Тест инициализации WidgetUpdateThread."""
    from main import WidgetUpdateThread

    mock_widget = Mock()
    mock_widget.name = "TestWidget"
    mock_widget.get_update_interval.return_value = 1.0

    thread = WidgetUpdateThread(mock_widget)

    assert thread.widget == mock_widget
    assert thread.daemon is True
    assert thread.name == "Widget-TestWidget"


def test_widget_update_thread_run():
    """Тест run() метода WidgetUpdateThread."""
    from main import WidgetUpdateThread

    mock_widget = Mock()
    mock_widget.name = "TestWidget"
    mock_widget.get_update_interval.return_value = 0.05
    mock_widget.update = Mock()

    thread = WidgetUpdateThread(mock_widget)
    thread.start()
    time.sleep(0.15)  # Дать время выполнить несколько обновлений
    thread.stop()
    thread.join(timeout=1.0)

    # Должно быть несколько вызовов update()
    assert mock_widget.update.call_count >= 1


def test_widget_update_thread_handles_errors():
    """Тест обработки ошибок в WidgetUpdateThread."""
    from main import WidgetUpdateThread

    mock_widget = Mock()
    mock_widget.name = "TestWidget"
    mock_widget.get_update_interval.return_value = 0.05
    mock_widget.update.side_effect = Exception("Test error")

    thread = WidgetUpdateThread(mock_widget)
    thread.start()
    time.sleep(0.15)
    thread.stop()
    thread.join(timeout=1.0)

    # Thread должен продолжать работу несмотря на ошибки
    assert mock_widget.update.call_count >= 1


# ===========================
# Тесты SteelClockApp.__init__
# ===========================

def test_steelclock_app_init_with_valid_config(temp_config_file):
    """Тест инициализации SteelClockApp с валидным конфигом."""
    from main import SteelClockApp

    app = SteelClockApp(config_path=temp_config_file)

    assert app.config_path == Path(temp_config_file)
    assert app.config['game_name'] == "TEST_GAME"
    assert app.api is None  # Ещё не инициализировано
    assert app.layout_manager is None
    assert app.compositor is None
    assert len(app.widgets) == 0
    assert app.shutdown_requested is False


def test_steelclock_app_init_with_missing_config():
    """Тест инициализации SteelClockApp с отсутствующим конфигом."""
    from main import SteelClockApp

    app = SteelClockApp(config_path="/nonexistent/config.json")

    # Должен использовать дефолтную конфигурацию
    assert app.config['game_name'] == "STEELCLOCK"
    assert len(app.config['widgets']) == 1


def test_steelclock_app_load_config_invalid_json():
    """Тест _load_config с невалидным JSON."""
    from main import SteelClockApp

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("{invalid json")
        temp_path = f.name

    try:
        with pytest.raises(json.JSONDecodeError):
            SteelClockApp(config_path=temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_steelclock_app_load_config_not_a_dict():
    """Тест _load_config когда конфиг не dict."""
    from main import SteelClockApp

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(["not", "a", "dict"], f)
        temp_path = f.name

    try:
        with pytest.raises(ValueError, match="Config must be a JSON object"):
            SteelClockApp(config_path=temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_steelclock_app_default_config():
    """Тест _default_config возвращает валидную конфигурацию."""
    from main import SteelClockApp

    app = SteelClockApp(config_path="/nonexistent/config.json")
    config = app.config

    assert config['game_name'] == "STEELCLOCK"
    assert config['display']['width'] == 128
    assert len(config['widgets']) == 1
    assert config['widgets'][0]['type'] == "clock"


# ===========================
# Тесты SteelClockApp.setup()
# ===========================

def test_steelclock_app_setup_success(temp_config_file, mock_api, mock_components):
    """Тест успешного setup()."""
    from main import SteelClockApp

    app = SteelClockApp(config_path=temp_config_file)
    app.setup()

    # API должен быть инициализирован
    assert app.api is not None
    mock_api.register_game.assert_called_once()
    mock_api.bind_screen_event.assert_called_once_with("DISPLAY")

    # LayoutManager должен быть создан
    assert app.layout_manager is not None

    # Compositor должен быть создан
    assert app.compositor is not None

    # Виджеты должны быть созданы
    assert len(app.widgets) == 1


def test_steelclock_app_setup_server_discovery_error(temp_config_file):
    """Тест setup() при ошибке discovery."""
    from main import SteelClockApp
    from gamesense.discovery import ServerDiscoveryError

    with patch('main.GameSenseAPI') as mock_api_class:
        mock_api_class.side_effect = ServerDiscoveryError("Discovery failed")

        app = SteelClockApp(config_path=temp_config_file)

        with pytest.raises(ServerDiscoveryError):
            app.setup()


def test_steelclock_app_setup_api_error(temp_config_file):
    """Тест setup() при ошибке API."""
    from main import SteelClockApp
    from gamesense.api import GameSenseAPIError

    with patch('main.GameSenseAPI') as mock_api_class:
        api_instance = Mock()
        api_instance.register_game.side_effect = GameSenseAPIError("API failed")
        mock_api_class.return_value = api_instance

        app = SteelClockApp(config_path=temp_config_file)

        with pytest.raises(GameSenseAPIError):
            app.setup()


def test_steelclock_app_setup_disabled_widgets(mock_api, mock_components):
    """Тест setup() с отключёнными виджетами."""
    from main import SteelClockApp

    config_data = {
        "widgets": [
            {"type": "clock", "id": "clock1", "enabled": True},
            {"type": "cpu", "id": "cpu1", "enabled": False},
            {"type": "memory", "id": "mem1", "enabled": True}
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name

    try:
        app = SteelClockApp(config_path=temp_path)
        app.setup()

        # Должно быть создано 2 виджета (cpu отключён)
        assert len(app.widgets) == 2
    finally:
        Path(temp_path).unlink(missing_ok=True)


# ===========================
# Тесты _create_widget_from_config()
# ===========================

def test_create_widget_clock(mock_all_widgets):
    """Тест создания Clock виджета."""
    from main import SteelClockApp

    app = SteelClockApp(config_path="/nonexistent/config.json")

    config = {
        "type": "clock",
        "id": "test_clock",
        "properties": {"format": "%H:%M", "font_size": 14},
        "style": {"background_color": 0, "border": True}
    }

    widget = app._create_widget_from_config(config)

    assert widget is not None
    mock_all_widgets['clock'].assert_called_once()


def test_create_widget_cpu(mock_all_widgets):
    """Тест создания CPU виджета."""
    from main import SteelClockApp

    app = SteelClockApp(config_path="/nonexistent/config.json")

    config = {
        "type": "cpu",
        "id": "test_cpu",
        "properties": {"display_mode": "bar_horizontal", "per_core": True}
    }

    widget = app._create_widget_from_config(config)

    assert widget is not None
    mock_all_widgets['cpu'].assert_called_once()


def test_create_widget_memory(mock_all_widgets):
    """Тест создания Memory виджета."""
    from main import SteelClockApp

    app = SteelClockApp(config_path="/nonexistent/config.json")

    config = {
        "type": "memory",
        "id": "test_memory"
    }

    widget = app._create_widget_from_config(config)

    assert widget is not None
    mock_all_widgets['memory'].assert_called_once()


def test_create_widget_network(mock_all_widgets):
    """Тест создания Network виджета."""
    from main import SteelClockApp

    app = SteelClockApp(config_path="/nonexistent/config.json")

    config = {
        "type": "network",
        "id": "test_network",
        "properties": {"interface": "eth0"}
    }

    widget = app._create_widget_from_config(config)

    assert widget is not None
    mock_all_widgets['network'].assert_called_once()


def test_create_widget_disk(mock_all_widgets):
    """Тест создания Disk виджета."""
    from main import SteelClockApp

    app = SteelClockApp(config_path="/nonexistent/config.json")

    config = {
        "type": "disk",
        "id": "test_disk",
        "properties": {"disk_name": "sda"}
    }

    widget = app._create_widget_from_config(config)

    assert widget is not None
    mock_all_widgets['disk'].assert_called_once()


def test_create_widget_keyboard(mock_all_widgets):
    """Тест создания Keyboard виджета."""
    from main import SteelClockApp

    app = SteelClockApp(config_path="/nonexistent/config.json")

    config = {
        "type": "keyboard",
        "id": "test_keyboard"
    }

    widget = app._create_widget_from_config(config)

    assert widget is not None
    mock_all_widgets['keyboard'].assert_called_once()


def test_create_widget_unknown_type():
    """Тест создания виджета неизвестного типа."""
    from main import SteelClockApp

    app = SteelClockApp(config_path="/nonexistent/config.json")

    config = {
        "type": "unknown_widget",
        "id": "test"
    }

    widget = app._create_widget_from_config(config)

    assert widget is None


def test_create_widget_with_exception(mock_all_widgets):
    """Тест создания виджета когда конструктор вызывает ошибку."""
    from main import SteelClockApp

    mock_all_widgets['clock'].side_effect = Exception("Widget creation failed")

    app = SteelClockApp(config_path="/nonexistent/config.json")

    config = {
        "type": "clock",
        "id": "test_clock"
    }

    widget = app._create_widget_from_config(config)

    assert widget is None


# ===========================
# Тесты run() и shutdown()
# ===========================

def test_steelclock_app_run(temp_config_file, mock_api, mock_components):
    """Тест run() метода."""
    from main import SteelClockApp

    app = SteelClockApp(config_path=temp_config_file)
    app.setup()

    # Запускаем в отдельном потоке и останавливаем через shutdown_requested
    import threading

    def run_app():
        app.run()

    thread = threading.Thread(target=run_app)
    thread.start()

    time.sleep(0.2)
    app.shutdown_requested = True
    thread.join(timeout=2.0)

    # Compositor должен быть запущен
    mock_components['compositor'].start.assert_called_once()


def test_steelclock_app_run_without_setup():
    """Тест run() без предварительного setup()."""
    from main import SteelClockApp

    app = SteelClockApp(config_path="/nonexistent/config.json")

    with pytest.raises(AssertionError):
        app.run()


def test_steelclock_app_shutdown(temp_config_file, mock_api, mock_components):
    """Тест shutdown() метода."""
    from main import SteelClockApp

    app = SteelClockApp(config_path=temp_config_file)
    app.setup()

    # Создаём mock потоки
    mock_thread = Mock()
    mock_thread.stop = Mock()
    mock_thread.join = Mock()
    app.widget_threads.append(mock_thread)

    app.shutdown()

    # Compositor должен быть остановлен
    mock_components['compositor'].stop.assert_called_once()

    # Потоки должны быть остановлены
    mock_thread.stop.assert_called_once()
    mock_thread.join.assert_called_once()

    # API должен удалить игру
    mock_api.remove_game.assert_called_once()

    assert app.shutdown_requested is True


def test_steelclock_app_shutdown_idempotent(temp_config_file, mock_api, mock_components):
    """Тест что shutdown() идемпотентен."""
    from main import SteelClockApp

    app = SteelClockApp(config_path=temp_config_file)
    app.setup()

    app.shutdown()
    app.shutdown()  # Второй вызов

    # stop должен быть вызван только один раз
    assert mock_components['compositor'].stop.call_count == 1


def test_steelclock_app_signal_handler():
    """Тест обработчика сигналов."""
    from main import SteelClockApp

    app = SteelClockApp(config_path="/nonexistent/config.json")

    assert app.shutdown_requested is False

    app.signal_handler(signal.SIGINT, None)

    assert app.shutdown_requested is True


# ===========================
# Тесты main()
# ===========================

def test_main_with_config_arg(temp_config_file, mock_api, mock_components):
    """Тест main() с аргументом конфигурации."""
    from main import main

    with patch('sys.argv', ['main.py', temp_config_file]), \
         patch('main.SteelClockApp') as mock_app_class:

        mock_app = Mock()
        mock_app.setup = Mock()
        mock_app.run = Mock(side_effect=KeyboardInterrupt())
        mock_app.signal_handler = Mock()
        mock_app_class.return_value = mock_app

        try:
            main()
        except SystemExit:
            pass

        # App должен быть создан с указанным путём
        mock_app_class.assert_called_once()
        call_args = mock_app_class.call_args[1]
        assert call_args['config_path'] == temp_config_file


def test_main_without_config_arg(mock_api, mock_components):
    """Тест main() без аргументов (дефолтный конфиг)."""
    from main import main

    with patch('sys.argv', ['main.py']), \
         patch('main.SteelClockApp') as mock_app_class, \
         patch('main.Path') as mock_path:

        mock_app = Mock()
        mock_app.setup = Mock()
        mock_app.run = Mock(side_effect=KeyboardInterrupt())
        mock_app.signal_handler = Mock()
        mock_app_class.return_value = mock_app

        try:
            main()
        except SystemExit:
            pass

        # App должен быть создан
        mock_app_class.assert_called_once()


def test_main_server_discovery_error(mock_components):
    """Тест main() при ошибке discovery."""
    from main import main
    from gamesense.discovery import ServerDiscoveryError

    with patch('sys.argv', ['main.py']), \
         patch('main.SteelClockApp') as mock_app_class:

        mock_app = Mock()
        mock_app.setup.side_effect = ServerDiscoveryError("Discovery failed")
        mock_app_class.return_value = mock_app

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1


def test_main_generic_exception(mock_components):
    """Тест main() при общей ошибке."""
    from main import main

    with patch('sys.argv', ['main.py']), \
         patch('main.SteelClockApp') as mock_app_class:

        mock_app = Mock()
        mock_app.setup.side_effect = Exception("Fatal error")
        mock_app_class.return_value = mock_app

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1


# ===========================
# Integration тесты
# ===========================

def test_full_app_lifecycle(temp_config_file, mock_api, mock_components):
    """Integration тест: полный жизненный цикл приложения."""
    from main import SteelClockApp

    # Создаём приложение
    app = SteelClockApp(config_path=temp_config_file)

    # Setup
    app.setup()
    assert app.api is not None
    assert app.layout_manager is not None
    assert app.compositor is not None
    assert len(app.widgets) > 0

    # Shutdown
    app.shutdown()
    assert app.shutdown_requested is True
    mock_components['compositor'].stop.assert_called_once()


def test_multiple_widgets_creation(mock_api, mock_components):
    """Integration тест: создание нескольких виджетов."""
    from main import SteelClockApp

    config_data = {
        "widgets": [
            {"type": "clock", "id": "clock1", "enabled": True},
            {"type": "cpu", "id": "cpu1", "enabled": True},
            {"type": "memory", "id": "mem1", "enabled": True},
            {"type": "network", "id": "net1", "enabled": True},
            {"type": "disk", "id": "disk1", "enabled": True},
            {"type": "keyboard", "id": "kbd1", "enabled": True}
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name

    try:
        app = SteelClockApp(config_path=temp_path)
        app.setup()

        # Должны быть созданы все 6 виджетов
        assert len(app.widgets) == 6
    finally:
        Path(temp_path).unlink(missing_ok=True)
