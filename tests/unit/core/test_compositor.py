"""
Unit tests для Compositor - главный цикл рендеринга для OLED дисплея.

Тестируемый модуль: core/compositor.py

Покрытие:
- Инициализация
- Запуск/остановка render loop (threading)
- Рендеринг кадров
- Обработка ошибок
- Статистика
- Context manager
"""

import time
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from core.compositor import Compositor
from core.layout_manager import LayoutManager
from gamesense.api import GameSenseAPI, GameSenseAPIError


# ===========================
# Фикстуры
# ===========================

@pytest.fixture
def mock_layout_manager() -> Mock:
    """Фикстура создающая mock LayoutManager."""
    manager = Mock(spec=LayoutManager)
    # composite() возвращает пустое изображение
    manager.composite.return_value = Image.new('L', (128, 40), color=0)
    return manager


@pytest.fixture
def mock_api() -> Mock:
    """Фикстура создающая mock GameSenseAPI."""
    api = Mock(spec=GameSenseAPI)
    api.send_screen_data = Mock()
    return api


@pytest.fixture
def compositor(mock_layout_manager: Mock, mock_api: Mock) -> Compositor:
    """Фикстура создающая Compositor."""
    return Compositor(
        layout_manager=mock_layout_manager,
        api=mock_api,
        refresh_rate_ms=100,
        event_name="TEST_EVENT"
    )


# ===========================
# Тесты инициализации
# ===========================

def test_compositor_init_default_values(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест инициализации с дефолтными значениями."""
    comp = Compositor(
        layout_manager=mock_layout_manager,
        api=mock_api
    )

    assert comp.layout_manager == mock_layout_manager
    assert comp.api == mock_api
    assert comp.refresh_rate_ms == 100
    assert comp.event_name == "DISPLAY"
    assert comp._thread is None
    assert comp._running is False
    assert comp._frame_count == 0
    assert comp._error_count == 0


def test_compositor_init_custom_values(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест инициализации с кастомными значениями."""
    comp = Compositor(
        layout_manager=mock_layout_manager,
        api=mock_api,
        refresh_rate_ms=50,
        event_name="CUSTOM_EVENT"
    )

    assert comp.refresh_rate_ms == 50
    assert comp.event_name == "CUSTOM_EVENT"


# ===========================
# Тесты start/stop
# ===========================

def test_compositor_start(compositor: Compositor) -> None:
    """Тест запуска compositor."""
    assert compositor._running is False
    assert compositor._thread is None

    compositor.start()

    assert compositor._running is True
    assert compositor._thread is not None
    assert compositor._thread.is_alive()
    assert compositor._thread.daemon is True
    assert compositor._thread.name == "Compositor"

    # Очистка
    compositor.stop()


def test_compositor_start_already_running(compositor: Compositor) -> None:
    """Тест что start вызывает RuntimeError если уже запущен."""
    compositor.start()

    with pytest.raises(RuntimeError, match="already running"):
        compositor.start()

    compositor.stop()


def test_compositor_stop(compositor: Compositor) -> None:
    """Тест остановки compositor."""
    compositor.start()
    assert compositor._running is True

    compositor.stop()

    assert compositor._running is False
    # Thread должен завершиться
    time.sleep(0.2)
    assert not compositor._thread.is_alive()


def test_compositor_stop_not_running(compositor: Compositor) -> None:
    """Тест stop когда compositor не запущен (no-op)."""
    assert compositor._running is False

    # Не должно вызвать ошибку
    compositor.stop()

    assert compositor._running is False


def test_compositor_is_running(compositor: Compositor) -> None:
    """Тест is_running возвращает статус."""
    assert compositor.is_running() is False

    compositor.start()
    assert compositor.is_running() is True

    compositor.stop()
    time.sleep(0.1)
    assert compositor.is_running() is False


def test_compositor_stop_with_timeout(compositor: Compositor) -> None:
    """Тест stop с timeout параметром."""
    compositor.start()

    # Останавливаем с коротким timeout
    compositor.stop(timeout=0.5)

    assert compositor._running is False


# ===========================
# Тесты _render_frame
# ===========================

def test_compositor_render_frame_success(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест успешного рендеринга одного кадра."""
    comp = Compositor(mock_layout_manager, mock_api)

    # Мокаем image_to_bytes
    with patch('core.compositor.image_to_bytes') as mock_to_bytes:
        mock_to_bytes.return_value = [0] * 5120

        comp._render_frame()

        # Проверяем что composite был вызван
        mock_layout_manager.composite.assert_called_once()

        # Проверяем что image_to_bytes был вызван
        mock_to_bytes.assert_called_once()

        # Проверяем что send_screen_data был вызван
        mock_api.send_screen_data.assert_called_once_with("DISPLAY", [0] * 5120)

        # Проверяем что frame_count увеличился
        assert comp._frame_count == 1


def test_compositor_render_frame_logs_every_100_frames(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест что логируется каждый 100-й кадр."""
    comp = Compositor(mock_layout_manager, mock_api)

    with patch('core.compositor.image_to_bytes') as mock_to_bytes:
        mock_to_bytes.return_value = [0] * 5120

        # Рендерим 100 кадров
        for i in range(100):
            comp._render_frame()

        assert comp._frame_count == 100


def test_compositor_render_frame_gamesense_api_error(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест обработки GameSenseAPIError при рендеринге."""
    comp = Compositor(mock_layout_manager, mock_api)

    # API вызывает ошибку
    with patch('core.compositor.image_to_bytes') as mock_to_bytes:
        mock_to_bytes.return_value = [0] * 5120
        mock_api.send_screen_data.side_effect = GameSenseAPIError("API Error")

        comp._render_frame()

        # Ошибка должна быть обработана
        assert comp._error_count == 1
        # Время последней ошибки должно быть записано
        assert comp._last_error_time > 0


def test_compositor_render_frame_generic_error(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест обработки общей ошибки при рендеринге."""
    comp = Compositor(mock_layout_manager, mock_api)

    # composite вызывает ошибку
    mock_layout_manager.composite.side_effect = Exception("Render error")

    comp._render_frame()

    # Ошибка должна быть обработана
    assert comp._error_count == 1


def test_compositor_render_frame_rate_limit_error_logging(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест rate-limiting логирования ошибок API."""
    comp = Compositor(mock_layout_manager, mock_api)

    with patch('core.compositor.image_to_bytes') as mock_to_bytes, \
            patch('time.time') as mock_time:
        mock_to_bytes.return_value = [0] * 5120
        mock_api.send_screen_data.side_effect = GameSenseAPIError("API Error")

        # Первая ошибка в момент времени 0
        mock_time.return_value = 0.0
        comp._render_frame()
        assert comp._last_error_time == 0.0

        # Вторая ошибка через 1 секунду (меньше 5 сек - не логируется)
        mock_time.return_value = 1.0
        comp._render_frame()
        assert comp._last_error_time == 0.0  # Не обновилось

        # Третья ошибка через 6 секунд (больше 5 сек - логируется)
        mock_time.return_value = 6.0
        comp._render_frame()
        assert comp._last_error_time == 6.0  # Обновилось

        assert comp._error_count == 3


# ===========================
# Тесты _render_loop
# ===========================

def test_compositor_render_loop_executes_frames(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Integration тест: render loop выполняет несколько кадров."""
    comp = Compositor(mock_layout_manager, mock_api, refresh_rate_ms=10)

    with patch('core.compositor.image_to_bytes') as mock_to_bytes:
        mock_to_bytes.return_value = [0] * 5120

        comp.start()
        time.sleep(0.15)  # Даём время отрендерить несколько кадров
        comp.stop()

        # Должно быть отрендерено 10+ кадров (10ms interval, 150ms sleep)
        assert comp._frame_count >= 5
        assert mock_layout_manager.composite.call_count >= 5


def test_compositor_render_loop_stops_on_event(compositor: Compositor) -> None:
    """Тест что render loop останавливается при установке stop_event."""
    with patch('core.compositor.image_to_bytes') as mock_to_bytes:
        mock_to_bytes.return_value = [0] * 5120

        compositor.start()
        time.sleep(0.05)
        initial_count = compositor._frame_count

        compositor.stop()
        time.sleep(0.1)

        # Frame count не должен увеличиться после stop
        assert compositor._frame_count == initial_count


def test_compositor_render_loop_handles_errors(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест что render loop продолжает работу при ошибках."""
    comp = Compositor(mock_layout_manager, mock_api, refresh_rate_ms=10)

    call_count = [0]

    def composite_side_effect() -> Image.Image:
        call_count[0] += 1
        if call_count[0] == 2:
            raise Exception("Test error")
        return Image.new('L', (128, 40), color=0)

    mock_layout_manager.composite.side_effect = composite_side_effect

    with patch('core.compositor.image_to_bytes') as mock_to_bytes:
        mock_to_bytes.return_value = [0] * 5120

        comp.start()
        time.sleep(0.1)
        comp.stop()

        # Несмотря на ошибку во втором кадре, остальные должны отрендериться
        assert comp._error_count >= 1
        assert comp._frame_count >= 1  # Успешные кадры


def test_compositor_render_loop_sleeps_on_many_errors(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест что render loop замедляется при большом количестве ошибок."""
    comp = Compositor(mock_layout_manager, mock_api, refresh_rate_ms=10)

    # Заставляем composite всегда вызывать ошибку
    mock_layout_manager.composite.side_effect = Exception("Persistent error")

    with patch('time.sleep') as mock_sleep:
        comp.start()
        time.sleep(0.2)
        comp.stop()

        # После 10+ ошибок должен вызваться sleep(1.0)
        if comp._error_count > 10:
            mock_sleep.assert_any_call(1.0)


def test_compositor_render_loop_timing(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест что render loop синхронизируется по времени."""
    comp = Compositor(mock_layout_manager, mock_api, refresh_rate_ms=50)

    with patch('core.compositor.image_to_bytes') as mock_to_bytes:
        mock_to_bytes.return_value = [0] * 5120

        start_time = time.time()
        comp.start()
        time.sleep(0.3)
        comp.stop()
        elapsed = time.time() - start_time

        # За 300ms при 50ms interval должно быть ~6 кадров
        expected_frames = int(elapsed / 0.05)
        assert comp._frame_count >= expected_frames - 2  # С небольшой погрешностью


# ===========================
# Тесты get_stats
# ===========================

def test_compositor_get_stats(compositor: Compositor) -> None:
    """Тест get_stats возвращает статистику."""
    stats = compositor.get_stats()

    assert stats['frame_count'] == 0
    assert stats['error_count'] == 0
    assert stats['is_running'] is False
    assert stats['refresh_rate_ms'] == 100


def test_compositor_get_stats_after_rendering(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест get_stats после рендеринга."""
    comp = Compositor(mock_layout_manager, mock_api)

    with patch('core.compositor.image_to_bytes') as mock_to_bytes:
        mock_to_bytes.return_value = [0] * 5120

        # Рендерим несколько кадров
        for i in range(5):
            comp._render_frame()

        stats = comp.get_stats()

        assert stats['frame_count'] == 5
        assert stats['error_count'] == 0


def test_compositor_get_stats_with_errors(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест get_stats после ошибок."""
    comp = Compositor(mock_layout_manager, mock_api)

    mock_layout_manager.composite.side_effect = Exception("Error")

    for i in range(3):
        comp._render_frame()

    stats = comp.get_stats()

    assert stats['frame_count'] == 0  # Ни один кадр не успешен
    assert stats['error_count'] == 3


# ===========================
# Тесты context manager
# ===========================

def test_compositor_context_manager(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест использования compositor как context manager."""
    comp = Compositor(mock_layout_manager, mock_api)

    assert comp.is_running() is False

    with comp:
        assert comp.is_running() is True

    time.sleep(0.1)
    assert comp.is_running() is False


def test_compositor_context_manager_with_exception(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Тест что context manager корректно останавливается при исключении."""
    comp = Compositor(mock_layout_manager, mock_api)

    try:
        with comp:
            assert comp.is_running() is True
            raise ValueError("Test exception")
    except ValueError:
        pass

    time.sleep(0.1)
    assert comp.is_running() is False


def test_compositor_context_manager_auto_cleanup(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Integration тест: context manager автоматически очищает ресурсы."""
    comp = Compositor(mock_layout_manager, mock_api, refresh_rate_ms=10)

    with patch('core.compositor.image_to_bytes') as mock_to_bytes:
        mock_to_bytes.return_value = [0] * 5120

        with comp:
            time.sleep(0.1)  # Рендерим несколько кадров

        # После выхода из context должно остановиться
        time.sleep(0.1)
        assert comp.is_running() is False
        assert comp._frame_count > 0


# ===========================
# Edge cases и граничные условия
# ===========================

def test_compositor_zero_refresh_rate(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Edge case: нулевой refresh rate."""
    comp = Compositor(mock_layout_manager, mock_api, refresh_rate_ms=0)

    # Не должно вызвать ошибку при инициализации
    assert comp.refresh_rate_ms == 0


def test_compositor_multiple_start_stop_cycles(compositor: Compositor) -> None:
    """Integration тест: несколько циклов start/stop."""
    with patch('core.compositor.image_to_bytes') as mock_to_bytes:
        mock_to_bytes.return_value = [0] * 5120

        # Первый цикл
        compositor.start()
        time.sleep(0.05)
        compositor.stop()
        time.sleep(0.05)

        # Второй цикл - можно перезапустить после остановки
        compositor2 = Compositor(compositor.layout_manager, compositor.api)
        compositor2.start()
        time.sleep(0.05)
        compositor2.stop()

        assert compositor2._frame_count > 0


def test_compositor_thread_daemon_mode(compositor: Compositor) -> None:
    """Тест что thread запускается в daemon режиме."""
    compositor.start()

    assert compositor._thread is not None
    assert compositor._thread.daemon is True

    compositor.stop()


def test_compositor_empty_event_name(mock_layout_manager: Mock, mock_api: Mock) -> None:
    """Edge case: пустое имя события."""
    comp = Compositor(
        mock_layout_manager,
        mock_api,
        event_name=""
    )

    assert comp.event_name == ""

    with patch('core.compositor.image_to_bytes') as mock_to_bytes:
        mock_to_bytes.return_value = [0] * 5120

        comp._render_frame()

        # send_screen_data должен быть вызван с пустым именем
        mock_api.send_screen_data.assert_called_once_with("", [0] * 5120)
