"""
Unit tests для LayoutManager - управление размещением виджетов на канвасе.

Тестируемый модуль: core/layout_manager.py

Покрытие:
- Инициализация (базовый и viewport режимы)
- Добавление/удаление виджетов
- Композиция изображений (composite)
- Z-order и видимость
- Viewport operations (zoom, crop, culling)
- Widget scaling
- Alpha channel support
"""

from typing import Callable, Tuple

import pytest
from unittest.mock import Mock
from PIL import Image

from core.layout_manager import LayoutManager
from core.widget import Widget


# ===========================
# Фикстуры
# ===========================

@pytest.fixture
def mock_widget() -> Mock:
    """Фикстура создающая mock виджет с базовыми методами."""
    widget = Mock(spec=Widget)
    widget.name = "TestWidget"
    widget.get_preferred_size.return_value = (64, 20)
    widget.set_size = Mock()

    # render() возвращает изображение 64x20 по умолчанию
    widget.render.return_value = Image.new('L', (64, 20), color=128)

    return widget


@pytest.fixture
def mock_widget_factory() -> Callable[..., Mock]:
    """Фабрика для создания множества mock виджетов."""
    def create_widget(name: str = "Widget", size: Tuple[int, int] = (64, 20)) -> Mock:
        widget = Mock(spec=Widget)
        widget.name = name
        widget.get_preferred_size.return_value = size
        widget.set_size = Mock()
        widget.render.return_value = Image.new('L', size, color=128)
        return widget
    return create_widget


# ===========================
# Тесты инициализации
# ===========================

def test_layout_manager_init_default_values() -> None:
    """Тест инициализации с дефолтными значениями (базовый режим)."""
    manager = LayoutManager()

    assert manager.display_width == 128
    assert manager.display_height == 40
    assert manager.virtual_width == 128
    assert manager.virtual_height == 40
    assert manager.background_color == 0
    assert manager.viewport_mode is False
    assert manager.viewport is None
    assert len(manager.layouts) == 0


def test_layout_manager_init_custom_size() -> None:
    """Тест инициализации с кастомным размером (базовый режим)."""
    manager = LayoutManager(width=256, height=80, background_color=255)

    assert manager.display_width == 256
    assert manager.display_height == 80
    assert manager.virtual_width == 256
    assert manager.virtual_height == 80
    assert manager.background_color == 255
    assert manager.viewport_mode is False


def test_layout_manager_init_viewport_mode() -> None:
    """Тест инициализации в viewport режиме (виртуальный канвас больше дисплея)."""
    manager = LayoutManager(
        width=128,
        height=40,
        virtual_width=256,
        virtual_height=80
    )

    assert manager.display_width == 128
    assert manager.display_height == 40
    assert manager.virtual_width == 256
    assert manager.virtual_height == 80
    assert manager.viewport_mode is True
    assert manager.viewport is not None
    assert manager.viewport.width == 128
    assert manager.viewport.height == 40


def test_layout_manager_width_property() -> None:
    """Тест property width возвращает virtual_width."""
    manager = LayoutManager(virtual_width=256)
    assert manager.width == 256


def test_layout_manager_height_property() -> None:
    """Тест property height возвращает virtual_height."""
    manager = LayoutManager(virtual_height=80)
    assert manager.height == 80


# ===========================
# Тесты add_widget
# ===========================

def test_layout_manager_add_widget_with_explicit_size(mock_widget: Mock) -> None:
    """Тест добавления виджета с явно указанным размером."""
    manager = LayoutManager()

    manager.add_widget(mock_widget, x=10, y=5, w=50, h=30, z_order=1)

    assert len(manager.layouts) == 1
    layout = manager.layouts[0]
    assert layout.widget == mock_widget
    assert layout.x == 10
    assert layout.y == 5
    assert layout.w == 50
    assert layout.h == 30
    assert layout.z_order == 1
    assert layout.visible is True
    assert layout.scale == 1.0

    # Проверяем что set_size был вызван
    mock_widget.set_size.assert_called_once_with(50, 30)


def test_layout_manager_add_widget_with_preferred_size(mock_widget: Mock) -> None:
    """Тест добавления виджета с preferred size (w/h = None)."""
    manager = LayoutManager()

    manager.add_widget(mock_widget, x=10, y=5)

    assert len(manager.layouts) == 1
    layout = manager.layouts[0]
    assert layout.w == 64  # from mock_widget.get_preferred_size()
    assert layout.h == 20

    mock_widget.get_preferred_size.assert_called_once()
    mock_widget.set_size.assert_called_once_with(64, 20)


def test_layout_manager_add_widget_partial_preferred_size(mock_widget: Mock) -> None:
    """Тест добавления виджета с частично указанным размером."""
    manager = LayoutManager()

    # Указываем только ширину, высота берётся из preferred
    manager.add_widget(mock_widget, x=0, y=0, w=100)

    layout = manager.layouts[0]
    assert layout.w == 100
    assert layout.h == 20  # from preferred


def test_layout_manager_add_widget_z_order_sorting(mock_widget_factory: Callable[..., Mock]) -> None:
    """Тест сортировки виджетов по z_order."""
    manager = LayoutManager()

    widget1 = mock_widget_factory("Widget1")
    widget2 = mock_widget_factory("Widget2")
    widget3 = mock_widget_factory("Widget3")

    # Добавляем в произвольном порядке
    manager.add_widget(widget2, z_order=5)
    manager.add_widget(widget1, z_order=1)
    manager.add_widget(widget3, z_order=10)

    # Проверяем что отсортированы по z_order
    assert manager.layouts[0].widget == widget1  # z_order=1
    assert manager.layouts[1].widget == widget2  # z_order=5
    assert manager.layouts[2].widget == widget3  # z_order=10


def test_layout_manager_add_widget_scale_in_viewport_mode(mock_widget: Mock) -> None:
    """Тест что scale применяется только в viewport режиме."""
    manager_viewport = LayoutManager(virtual_width=256, virtual_height=80)
    manager_basic = LayoutManager()

    widget1 = Mock(spec=Widget)
    widget1.name = "W1"
    widget1.get_preferred_size.return_value = (64, 20)
    widget1.set_size = Mock()

    widget2 = Mock(spec=Widget)
    widget2.name = "W2"
    widget2.get_preferred_size.return_value = (64, 20)
    widget2.set_size = Mock()

    # Viewport режим - scale должен применяться
    manager_viewport.add_widget(widget1, scale=2.0)
    assert manager_viewport.layouts[0].scale == 2.0

    # Базовый режим - scale всегда 1.0
    manager_basic.add_widget(widget2, scale=2.0)
    assert manager_basic.layouts[0].scale == 1.0


# ===========================
# Тесты remove_widget
# ===========================

def test_layout_manager_remove_widget_success(mock_widget_factory: Callable[..., Mock]) -> None:
    """Тест удаления существующего виджета."""
    manager = LayoutManager()

    widget1 = mock_widget_factory("W1")
    widget2 = mock_widget_factory("W2")

    manager.add_widget(widget1)
    manager.add_widget(widget2)

    assert len(manager) == 2

    result = manager.remove_widget(widget1)

    assert result is True
    assert len(manager) == 1
    assert manager.layouts[0].widget == widget2


def test_layout_manager_remove_widget_not_found(mock_widget: Mock) -> None:
    """Тест удаления несуществующего виджета."""
    manager = LayoutManager()

    result = manager.remove_widget(mock_widget)

    assert result is False
    assert len(manager) == 0


def test_layout_manager_remove_widget_from_multiple(mock_widget_factory: Callable[..., Mock]) -> None:
    """Тест удаления конкретного виджета из нескольких."""
    manager = LayoutManager()

    widgets = [mock_widget_factory(f"W{i}") for i in range(5)]
    for w in widgets:
        manager.add_widget(w)

    # Удаляем средний виджет
    result = manager.remove_widget(widgets[2])

    assert result is True
    assert len(manager) == 4
    assert widgets[2] not in [layout.widget for layout in manager.layouts]


# ===========================
# Тесты composite (базовый режим)
# ===========================

def test_layout_manager_composite_basic_mode_empty() -> None:
    """Тест composite пустого layout (базовый режим)."""
    manager = LayoutManager(width=128, height=40, background_color=0)

    image = manager.composite()

    assert image.size == (128, 40)
    assert image.mode == 'L'
    # Проверяем что изображение чёрное
    pixels = list(image.getdata())
    assert all(p == 0 for p in pixels)


def test_layout_manager_composite_basic_mode_single_widget(mock_widget: Mock) -> None:
    """Тест composite одного виджета (базовый режим)."""
    manager = LayoutManager()

    manager.add_widget(mock_widget, x=10, y=5, w=64, h=20)

    image = manager.composite()

    assert image.size == (128, 40)
    mock_widget.render.assert_called_once()


def test_layout_manager_composite_basic_mode_multiple_widgets(mock_widget_factory: Callable[..., Mock]) -> None:
    """Тест composite нескольких виджетов (базовый режим)."""
    manager = LayoutManager()

    widget1 = mock_widget_factory("W1", size=(32, 10))
    widget2 = mock_widget_factory("W2", size=(32, 10))

    manager.add_widget(widget1, x=0, y=0, w=32, h=10)
    manager.add_widget(widget2, x=32, y=0, w=32, h=10)

    image = manager.composite()

    assert image.size == (128, 40)
    widget1.render.assert_called_once()
    widget2.render.assert_called_once()


def test_layout_manager_composite_widget_visibility(mock_widget_factory: Callable[..., Mock]) -> None:
    """Тест что невидимые виджеты не рендерятся."""
    manager = LayoutManager()

    widget1 = mock_widget_factory("Visible")
    widget2 = mock_widget_factory("Hidden")

    manager.add_widget(widget1, x=0, y=0)
    manager.add_widget(widget2, x=64, y=0)

    # Скрываем второй виджет
    manager.set_widget_visibility(widget2, False)

    manager.composite()

    widget1.render.assert_called_once()
    widget2.render.assert_not_called()


def test_layout_manager_composite_widget_resize(mock_widget: Mock) -> None:
    """Тест что виджет ресайзится если размер не совпадает."""
    manager = LayoutManager()

    # Виджет рендерит 64x20, но layout требует 100x30
    manager.add_widget(mock_widget, x=0, y=0, w=100, h=30)

    image = manager.composite()

    # composite должен вызвать resize
    assert image.size == (128, 40)


def test_layout_manager_composite_alpha_channel_support(mock_widget: Mock) -> None:
    """Тест поддержки альфа-канала при композитинге."""
    manager = LayoutManager(background_color=0)

    # Виджет возвращает изображение с альфа-каналом
    alpha_img = Image.new('LA', (64, 20), color=(255, 128))
    mock_widget.render.return_value = alpha_img

    manager.add_widget(mock_widget, x=10, y=5, w=64, h=20)

    image = manager.composite()

    assert image.size == (128, 40)
    # Альфа-композитинг должен отработать без ошибок


def test_layout_manager_composite_widget_render_error(mock_widget_factory: Callable[..., Mock]) -> None:
    """Тест обработки ошибки при рендеринге виджета."""
    manager = LayoutManager()

    widget1 = mock_widget_factory("Good")
    widget2 = mock_widget_factory("Bad")
    widget3 = mock_widget_factory("Good2")

    # widget2 вызывает ошибку при render()
    widget2.render.side_effect = Exception("Render failed")

    manager.add_widget(widget1, x=0, y=0)
    manager.add_widget(widget2, x=32, y=0)
    manager.add_widget(widget3, x=64, y=0)

    # Composite должен продолжить работу несмотря на ошибку
    image = manager.composite()

    assert image.size == (128, 40)
    widget1.render.assert_called_once()
    widget2.render.assert_called_once()
    widget3.render.assert_called_once()


# ===========================
# Тесты composite (viewport режим)
# ===========================

def test_layout_manager_composite_viewport_mode_apply_viewport_true(mock_widget: Mock) -> None:
    """Тест composite в viewport режиме с apply_viewport=True."""
    manager = LayoutManager(
        width=128,
        height=40,
        virtual_width=256,
        virtual_height=80
    )

    manager.add_widget(mock_widget, x=0, y=0, w=64, h=20)

    image = manager.composite(apply_viewport=True)

    # Должно вернуть изображение размером с дисплей
    assert image.size == (128, 40)


def test_layout_manager_composite_viewport_mode_apply_viewport_false(mock_widget: Mock) -> None:
    """Тест composite в viewport режиме с apply_viewport=False."""
    manager = LayoutManager(
        width=128,
        height=40,
        virtual_width=256,
        virtual_height=80
    )

    manager.add_widget(mock_widget, x=0, y=0, w=64, h=20)

    image = manager.composite(apply_viewport=False)

    # Должно вернуть полный виртуальный канвас
    assert image.size == (256, 80)


def test_layout_manager_composite_viewport_culling(mock_widget_factory: Callable[..., Mock]) -> None:
    """Тест что виджеты вне viewport не рендерятся (culling optimization)."""
    manager = LayoutManager(
        width=128,
        height=40,
        virtual_width=256,
        virtual_height=80
    )

    widget_visible = mock_widget_factory("Visible")
    widget_outside = mock_widget_factory("Outside")

    # widget_visible в пределах viewport [0, 0, 128, 40]
    manager.add_widget(widget_visible, x=10, y=10, w=64, h=20)

    # widget_outside вне viewport
    manager.add_widget(widget_outside, x=200, y=60, w=64, h=20)

    # Viewport по умолчанию (0, 0)
    manager.composite(apply_viewport=True)

    # Только видимый виджет должен быть отрендерен
    widget_visible.render.assert_called_once()
    widget_outside.render.assert_not_called()


def test_layout_manager_composite_widget_scale_in_viewport_mode(mock_widget: Mock) -> None:
    """Тест применения локального scale виджета в viewport режиме."""
    manager = LayoutManager(
        width=128,
        height=40,
        virtual_width=256,
        virtual_height=80
    )

    # Виджет с scale=2.0
    manager.add_widget(mock_widget, x=0, y=0, w=32, h=10, scale=2.0)

    manager.composite(apply_viewport=False)

    # Виджет должен быть отрендерен и заскейлен
    mock_widget.render.assert_called_once()


# ===========================
# Тесты _apply_viewport
# ===========================

def test_layout_manager_apply_viewport_no_viewport() -> None:
    """Тест _apply_viewport без viewport (базовый режим)."""
    manager = LayoutManager()  # basic mode

    test_canvas = Image.new('L', (128, 40), color=100)
    result = manager._apply_viewport(test_canvas)

    # Должно вернуть изображение без изменений
    assert result == test_canvas


def test_layout_manager_apply_viewport_with_zoom() -> None:
    """Тест _apply_viewport с zoom."""
    manager = LayoutManager(virtual_width=256, virtual_height=80)

    # Устанавливаем zoom
    assert manager.viewport is not None
    manager.viewport.set_zoom(2.0)

    test_canvas = Image.new('L', (256, 80), color=100)
    result = manager._apply_viewport(test_canvas)

    # Результат должен быть размером с дисплей
    assert result.size == (128, 40)


def test_layout_manager_apply_viewport_crop_simple() -> None:
    """Тест _apply_viewport с простым crop."""
    manager = LayoutManager(virtual_width=256, virtual_height=80)

    # Скроллим viewport
    assert manager.viewport is not None
    manager.viewport.scroll_to(50, 20)

    test_canvas = Image.new('L', (256, 80), color=100)
    result = manager._apply_viewport(test_canvas)

    assert result.size == (128, 40)


def test_layout_manager_apply_viewport_crop_partial_outside() -> None:
    """Тест _apply_viewport когда viewport частично выходит за границы."""
    manager = LayoutManager(virtual_width=200, virtual_height=60)

    # Скроллим так чтобы viewport частично вышел за границы
    assert manager.viewport is not None
    manager.viewport.scroll_to(150, 40)

    test_canvas = Image.new('L', (200, 60), color=100)
    result = manager._apply_viewport(test_canvas)

    assert result.size == (128, 40)


def test_layout_manager_apply_viewport_completely_outside() -> None:
    """Edge case: viewport полностью вне виртуального канваса."""
    manager = LayoutManager(virtual_width=256, virtual_height=80)

    # Скроллим viewport полностью за пределы
    assert manager.viewport is not None
    manager.viewport.scroll_to(300, 100)

    test_canvas = Image.new('L', (256, 80), color=100)
    result = manager._apply_viewport(test_canvas)

    # Должно вернуть чёрный канвас размером с дисплей
    assert result.size == (128, 40)


# ===========================
# Тесты set_virtual_size
# ===========================

def test_layout_manager_set_virtual_size() -> None:
    """Тест изменения размера виртуального канваса."""
    manager = LayoutManager(width=128, height=40)

    assert manager.viewport_mode is False

    manager.set_virtual_size(256, 80)

    assert manager.virtual_width == 256
    assert manager.virtual_height == 80
    assert manager.viewport_mode is True
    assert manager.viewport is not None


def test_layout_manager_set_virtual_size_to_display_size() -> None:
    """Тест установки virtual size равного display size (выход из viewport режима)."""
    manager = LayoutManager(
        width=128,
        height=40,
        virtual_width=256,
        virtual_height=80
    )

    assert manager.viewport_mode is True

    manager.set_virtual_size(128, 40)

    assert manager.viewport_mode is False


def test_layout_manager_set_virtual_size_creates_viewport() -> None:
    """Тест что set_virtual_size создаёт viewport при переходе в viewport режим."""
    manager = LayoutManager()

    assert manager.viewport is None

    manager.set_virtual_size(256, 80)

    assert manager.viewport is not None
    assert manager.viewport.width == 128
    assert manager.viewport.height == 40


# ===========================
# Тесты constrain_viewport
# ===========================

def test_layout_manager_constrain_viewport_basic_mode() -> None:
    """Тест constrain_viewport в базовом режиме (no-op)."""
    manager = LayoutManager()

    # Не должно вызвать ошибку
    manager.constrain_viewport()


def test_layout_manager_constrain_viewport_with_zoom() -> None:
    """Тест constrain_viewport с zoom."""
    manager = LayoutManager(virtual_width=256, virtual_height=80)

    assert manager.viewport is not None
    manager.viewport.set_zoom(2.0)
    manager.viewport.scroll_to(1000, 1000)  # Вне границ

    manager.constrain_viewport()

    # Viewport должен быть ограничен
    zoomed_width = int(256 * 2.0)
    zoomed_height = int(80 * 2.0)
    max_offset_x = max(0, zoomed_width - 128)
    max_offset_y = max(0, zoomed_height - 40)

    assert manager.viewport.offset_x <= max_offset_x
    assert manager.viewport.offset_y <= max_offset_y


# ===========================
# Тесты get_widget_at
# ===========================

def test_layout_manager_get_widget_at_found(mock_widget: Mock) -> None:
    """Тест get_widget_at когда виджет найден."""
    manager = LayoutManager()

    manager.add_widget(mock_widget, x=10, y=10, w=50, h=30)

    # Точка внутри виджета
    widget = manager.get_widget_at(30, 20)

    assert widget == mock_widget


def test_layout_manager_get_widget_at_not_found(mock_widget: Mock) -> None:
    """Тест get_widget_at когда виджет не найден."""
    manager = LayoutManager()

    manager.add_widget(mock_widget, x=10, y=10, w=50, h=30)

    # Точка вне виджета
    widget = manager.get_widget_at(100, 100)

    assert widget is None


def test_layout_manager_get_widget_at_overlapping_widgets(mock_widget_factory: Callable[..., Mock]) -> None:
    """Тест get_widget_at с перекрывающимися виджетами (должен вернуть верхний)."""
    manager = LayoutManager()

    widget1 = mock_widget_factory("Bottom", size=(100, 50))
    widget2 = mock_widget_factory("Top", size=(50, 25))

    manager.add_widget(widget1, x=0, y=0, w=100, h=50, z_order=1)
    manager.add_widget(widget2, x=10, y=10, w=50, h=25, z_order=10)

    # Точка где оба виджета перекрываются
    widget = manager.get_widget_at(30, 20)

    # Должен вернуть виджет с большим z_order
    assert widget == widget2


def test_layout_manager_get_widget_at_invisible_widget(mock_widget: Mock) -> None:
    """Тест get_widget_at пропускает невидимые виджеты."""
    manager = LayoutManager()

    manager.add_widget(mock_widget, x=10, y=10, w=50, h=30)
    manager.set_widget_visibility(mock_widget, False)

    # Точка внутри виджета, но виджет невидим
    widget = manager.get_widget_at(30, 20)

    assert widget is None


def test_layout_manager_get_widget_at_edge_cases(mock_widget: Mock) -> None:
    """Edge case: проверка границ виджета."""
    manager = LayoutManager()

    manager.add_widget(mock_widget, x=10, y=10, w=50, h=30)

    # Левый верхний угол - внутри
    assert manager.get_widget_at(10, 10) == mock_widget

    # Правый нижний угол - 1 - внутри
    assert manager.get_widget_at(59, 39) == mock_widget

    # Правый нижний угол - снаружи
    assert manager.get_widget_at(60, 40) is None


# ===========================
# Тесты set_widget_visibility
# ===========================

def test_layout_manager_set_widget_visibility_show_hide(mock_widget: Mock) -> None:
    """Тест set_widget_visibility для показа/скрытия виджета."""
    manager = LayoutManager()

    manager.add_widget(mock_widget, x=0, y=0)

    # По умолчанию видим
    assert manager.layouts[0].visible is True

    # Скрываем
    manager.set_widget_visibility(mock_widget, False)
    assert manager.layouts[0].visible is False

    # Показываем
    manager.set_widget_visibility(mock_widget, True)
    assert manager.layouts[0].visible is True


def test_layout_manager_set_widget_visibility_nonexistent_widget(mock_widget: Mock) -> None:
    """Тест set_widget_visibility для несуществующего виджета (не должно вызвать ошибку)."""
    manager = LayoutManager()

    # Не должно вызвать ошибку
    manager.set_widget_visibility(mock_widget, False)


# ===========================
# Тесты clear и __len__
# ===========================

def test_layout_manager_clear(mock_widget_factory: Callable[..., Mock]) -> None:
    """Тест clear удаляет все виджеты."""
    manager = LayoutManager()

    for i in range(5):
        widget = mock_widget_factory(f"W{i}")
        manager.add_widget(widget)

    assert len(manager) == 5

    manager.clear()

    assert len(manager) == 0
    assert len(manager.layouts) == 0


def test_layout_manager_len(mock_widget_factory: Callable[..., Mock]) -> None:
    """Тест __len__ возвращает количество виджетов."""
    manager = LayoutManager()

    assert len(manager) == 0

    for i in range(3):
        widget = mock_widget_factory(f"W{i}")
        manager.add_widget(widget)

    assert len(manager) == 3


def test_layout_manager_clear_empty() -> None:
    """Edge case: clear на пустом layout."""
    manager = LayoutManager()

    manager.clear()

    assert len(manager) == 0


# ===========================
# Integration тесты
# ===========================

def test_layout_manager_full_workflow(mock_widget_factory: Callable[..., Mock]) -> None:
    """Integration тест: полный workflow добавления, композиции и удаления виджетов."""
    manager = LayoutManager(width=128, height=40)

    # Добавляем 3 виджета
    widget1 = mock_widget_factory("W1", size=(40, 20))
    widget2 = mock_widget_factory("W2", size=(40, 20))
    widget3 = mock_widget_factory("W3", size=(40, 20))

    manager.add_widget(widget1, x=0, y=0, w=40, h=20, z_order=1)
    manager.add_widget(widget2, x=40, y=0, w=40, h=20, z_order=2)
    manager.add_widget(widget3, x=80, y=0, w=40, h=20, z_order=3)

    assert len(manager) == 3

    # Композитим
    image = manager.composite()
    assert image.size == (128, 40)

    # Скрываем средний виджет
    manager.set_widget_visibility(widget2, False)
    manager.composite()
    widget2.render.assert_called_once()  # Первый composite

    # Удаляем виджет
    manager.remove_widget(widget1)
    assert len(manager) == 2

    # Очищаем
    manager.clear()
    assert len(manager) == 0


def test_layout_manager_viewport_workflow(mock_widget_factory: Callable[..., Mock]) -> None:
    """Integration тест: работа с viewport (scroll, zoom)."""
    manager = LayoutManager(
        width=128,
        height=40,
        virtual_width=256,
        virtual_height=80
    )

    widget = mock_widget_factory("W1")
    manager.add_widget(widget, x=150, y=50, w=64, h=20)

    # Виджет вне viewport
    manager.composite(apply_viewport=True)
    widget.render.assert_not_called()

    # Скроллим к виджету
    assert manager.viewport is not None
    manager.viewport.scroll_to(100, 30)
    manager.composite(apply_viewport=True)
    widget.render.assert_called_once()

    # Зумируем
    manager.viewport.set_zoom(2.0)
    manager.constrain_viewport()
    image3 = manager.composite(apply_viewport=True)

    assert image3.size == (128, 40)


def test_layout_manager_z_order_rendering(mock_widget_factory: Callable[..., Mock]) -> None:
    """Integration тест: проверка правильного порядка рендеринга по z_order."""
    manager = LayoutManager()

    # Создаём виджеты с разными цветами
    widget_bottom = mock_widget_factory("Bottom")
    widget_bottom.render.return_value = Image.new('L', (64, 40), color=50)

    widget_top = mock_widget_factory("Top")
    widget_top.render.return_value = Image.new('L', (64, 40), color=200)

    # Добавляем в обратном порядке
    manager.add_widget(widget_top, x=0, y=0, w=64, h=40, z_order=10)
    manager.add_widget(widget_bottom, x=0, y=0, w=64, h=40, z_order=1)

    image = manager.composite()

    # Виджет с большим z_order должен быть сверху
    # Проверяем что пиксели имеют цвет верхнего виджета
    pixel = image.getpixel((32, 20))
    assert pixel == 200  # Цвет верхнего виджета
