"""
Unit tests для core.widget - абстрактный базовый класс Widget.

Тестируемый модуль: core/widget.py
Класс: Widget (abstract)

Покрытие:
- Инициализация абстрактного класса
- Методы get_update_interval(), get_preferred_size(), set_size()
- Абстрактные методы update() и render() (должны вызывать NotImplementedError)
- Строковое представление
"""

import pytest
from PIL import Image
from core.widget import Widget


# =============================================================================
# Concrete Widget для тестирования абстрактного класса
# =============================================================================

class ConcreteWidget(Widget):
    """
    Конкретная реализация Widget для тестирования.

    Implements все abstract methods (update, render, get_update_interval) для возможности создания экземпляров.
    """

    def __init__(self, name: str, update_interval: float = 1.0):
        """
        Args:
            name: Имя виджета
            update_interval: Интервал обновления (хранится для get_update_interval)
        """
        super().__init__(name)
        self._update_interval = update_interval

    def update(self) -> None:
        """Пустая реализация update для тестов."""
        pass

    def render(self) -> Image.Image:
        """Возвращает пустое изображение для тестов."""
        return Image.new('L', (self._width, self._height), color=0)

    def get_update_interval(self) -> float:
        """Возвращает интервал обновления."""
        return self._update_interval


# =============================================================================
# Тесты инициализации
# =============================================================================

def test_widget_init_default_values() -> None:
    """
    Тест инициализации Widget с дефолтными значениями.

    Проверяет:
    - Дефолтные размеры (128x40)
    - Дефолтный update_interval (1.0)
    - Имя виджета
    """
    widget = ConcreteWidget(name="test_widget")

    assert widget.name == "test_widget"
    assert widget._width == 128
    assert widget._height == 40
    assert widget.get_update_interval() == 1.0


def test_widget_init_custom_values() -> None:
    """
    Тест инициализации Widget с кастомными значениями.

    Проверяет возможность переопределения всех параметров при создании.
    """
    widget = ConcreteWidget(
        name="custom",
        update_interval=0.5
    )

    assert widget.name == "custom"
    assert widget.get_update_interval() == 0.5


def test_widget_init_zero_interval() -> None:
    """
    Тест инициализации с нулевым интервалом обновления.

    Edge case: update_interval=0 должен быть допустим (виджет не обновляется автоматически).
    """
    widget = ConcreteWidget(name="test", update_interval=0.0)
    assert widget.get_update_interval() == 0.0


def test_widget_init_negative_interval() -> None:
    """
    Тест инициализации с отрицательным интервалом.

    Edge case: Отрицательный интервал допустим на уровне класса (валидация должна быть выше).
    """
    widget = ConcreteWidget(name="test", update_interval=-1.0)
    assert widget.get_update_interval() == -1.0


# =============================================================================
# Тесты методов размера
# =============================================================================

def test_get_preferred_size_default() -> None:
    """
    Тест get_preferred_size с дефолтными размерами.

    Проверяет, что preferred size совпадает с внутренними размерами.
    """
    widget = ConcreteWidget(name="test")
    width, height = widget.get_preferred_size()

    assert width == 128
    assert height == 40


def test_set_size_changes_dimensions() -> None:
    """
    Тест set_size изменяет внутренние размеры виджета.

    Проверяет:
    - Изменение _width и _height
    - get_preferred_size возвращает новые размеры
    """
    widget = ConcreteWidget(name="test")
    widget.set_size(64, 20)

    assert widget._width == 64
    assert widget._height == 20

    width, height = widget.get_preferred_size()
    assert width == 64
    assert height == 20


def test_set_size_zero_dimensions() -> None:
    """
    Тест set_size с нулевыми размерами.

    Edge case: Размеры 0x0 допустимы на уровне класса.
    """
    widget = ConcreteWidget(name="test")
    widget.set_size(0, 0)

    assert widget._width == 0
    assert widget._height == 0


def test_set_size_very_large_dimensions() -> None:
    """
    Тест set_size с очень большими размерами.

    Edge case: Проверка что класс не ограничивает размеры.
    """
    widget = ConcreteWidget(name="test")
    widget.set_size(10000, 10000)

    assert widget._width == 10000
    assert widget._height == 10000


# =============================================================================
# Тесты строкового представления
# =============================================================================

def test_widget_str_representation() -> None:
    """
    Тест строкового представления виджета.

    Проверяет, что str(widget) вызывает __repr__ (т.к. __str__ не определён).
    """
    widget = ConcreteWidget(name="my_widget")
    # Widget использует __repr__, поэтому str() вернёт то же что и repr()
    assert "my_widget" in str(widget)


def test_widget_repr_representation() -> None:
    """
    Тест __repr__ представления виджета.

    Проверяет, что __repr__ содержит класс и имя.
    """
    widget = ConcreteWidget(name="test")
    repr_str = repr(widget)

    assert "ConcreteWidget" in repr_str
    assert "test" in repr_str


# =============================================================================
# Тесты абстрактных методов (negative tests)
# =============================================================================

def test_cannot_instantiate_abstract_widget() -> None:
    """
    Тест что нельзя создать экземпляр абстрактного Widget напрямую.

    Проверяет, что попытка создания Widget (без реализации абстрактных методов)
    вызывает TypeError.
    """
    with pytest.raises(TypeError):
        # Это должно вызвать ошибку, т.к. Widget абстрактный
        Widget(name="test")  # type: ignore[abstract]


# =============================================================================
# Тесты render() конкретной реализации
# =============================================================================

def test_concrete_widget_render_returns_image() -> None:
    """
    Тест что конкретная реализация render() возвращает PIL Image.

    Проверяет:
    - Возвращается Image.Image
    - Размер соответствует размерам виджета
    """
    widget = ConcreteWidget(name="test")
    widget.set_size(64, 32)

    image = widget.render()

    assert isinstance(image, Image.Image)
    assert image.size == (64, 32)


def test_concrete_widget_update_no_error() -> None:
    """
    Тест что конкретная реализация update() выполняется без ошибок.

    Проверяет, что метод вызывается успешно.
    """
    widget = ConcreteWidget(name="test")

    # Не должно быть исключений
    widget.update()
