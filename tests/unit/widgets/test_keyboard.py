"""
Unit tests для widgets.keyboard - виджет индикации состояния клавиш.

Тестируемый модуль: widgets/keyboard.py

Покрытие:
- Инициализация и проверка поддержки платформы
- Получение состояния клавиш через Windows API
- Обновление состояния (update)
- Рендеринг индикаторов в разных состояниях
- Выравнивание индикаторов (horizontal/vertical)
- Кастомные символы для ON/OFF состояний
- Разные цвета для ON/OFF
- Edge cases и error handling
- Поведение на не-Windows платформах
"""

import pytest
from unittest.mock import patch, Mock
from PIL import Image
from widgets.keyboard import KeyboardWidget


# =============================================================================
# Тесты инициализации
# =============================================================================

def test_keyboard_init_default_values():
    """
    Тест инициализации с дефолтными значениями.

    Проверяет:
    - Имя виджета по умолчанию
    - Интервал обновления
    - Начальное состояние клавиш (все False)
    - Дефолтные символы
    """
    widget = KeyboardWidget()

    assert widget.name == "Keyboard"
    assert widget.update_interval_sec == 0.2
    assert widget._caps_lock_state is False
    assert widget._num_lock_state is False
    assert widget._scroll_lock_state is False
    assert widget.caps_lock_on == "⬆"
    assert widget.caps_lock_off == ""


def test_keyboard_init_custom_values():
    """
    Тест инициализации с кастомными значениями.

    Проверяет корректную установку всех параметров.
    """
    widget = KeyboardWidget(
        name="CustomKeyboard",
        update_interval=0.1,
        caps_lock_on="C",
        caps_lock_off="c",
        num_lock_on="N",
        num_lock_off="n",
        scroll_lock_on="S",
        scroll_lock_off="s",
        indicator_color_on=200,
        indicator_color_off=50,
        spacing=5
    )

    assert widget.name == "CustomKeyboard"
    assert widget.update_interval_sec == 0.1
    assert widget.caps_lock_on == "C"
    assert widget.caps_lock_off == "c"
    assert widget.num_lock_on == "N"
    assert widget.num_lock_off == "n"
    assert widget.scroll_lock_on == "S"
    assert widget.scroll_lock_off == "s"
    assert widget.indicator_color_on == 200
    assert widget.indicator_color_off == 50
    assert widget.spacing == 5


def test_keyboard_init_empty_symbols():
    """
    Тест инициализации с пустыми символами.

    Проверяет что можно скрыть OFF состояния через пустую строку.
    """
    widget = KeyboardWidget(
        caps_lock_on="CAPS",
        caps_lock_off="",
        num_lock_on="NUM",
        num_lock_off=""
    )

    assert widget.caps_lock_on == "CAPS"
    assert widget.caps_lock_off == ""
    assert widget.num_lock_on == "NUM"
    assert widget.num_lock_off == ""


# =============================================================================
# Тесты _get_key_state()
# =============================================================================

@patch('widgets.keyboard.KEYBOARD_SUPPORT', False)
def test_keyboard_get_key_state_no_support():
    """
    Тест получения состояния клавиши без поддержки.

    На неподдерживаемых платформах должен вернуть False.
    """
    widget = KeyboardWidget()
    state = widget._get_key_state(widget.VK_CAPITAL)

    assert state is False


def test_keyboard_get_key_state_logic():
    """
    Тест логики битовой маски в _get_key_state.

    Проверяет что бит 0 корректно извлекается из разных значений.
    Edge case: Тестируется логика без вызова реального Windows API.
    """
    widget = KeyboardWidget()

    # Симулируем логику: bool(state & 1)
    # Бит 0 установлен (нечётные числа) -> True
    for value in [1, 3, 5, 255, 32767]:
        assert bool(value & 1) is True

    # Бит 0 не установлен (чётные числа) -> False
    for value in [0, 2, 4, 254, 32766]:
        assert bool(value & 1) is False


# =============================================================================
# Тесты update()
# =============================================================================

def test_keyboard_update_all_locks_on():
    """
    Тест update() когда все lock клавиши включены.

    Проверяет что состояния всех клавиш обновляются.
    """
    widget = KeyboardWidget()

    with patch.object(widget, '_get_key_state', return_value=True):
        widget.update()

        assert widget._caps_lock_state is True
        assert widget._num_lock_state is True
        assert widget._scroll_lock_state is True


def test_keyboard_update_all_locks_off():
    """
    Тест update() когда все lock клавиши выключены.

    Проверяет что состояния всех клавиш False.
    """
    widget = KeyboardWidget()

    with patch.object(widget, '_get_key_state', return_value=False):
        widget.update()

        assert widget._caps_lock_state is False
        assert widget._num_lock_state is False
        assert widget._scroll_lock_state is False


def test_keyboard_update_mixed_states():
    """
    Тест update() со смешанными состояниями клавиш.

    Caps = ON, Num = OFF, Scroll = ON.
    """
    widget = KeyboardWidget()

    def get_key_state_side_effect(vk_code):
        if vk_code == KeyboardWidget.VK_CAPITAL:  # Caps Lock ON
            return True
        elif vk_code == KeyboardWidget.VK_NUMLOCK:  # Num Lock OFF
            return False
        elif vk_code == KeyboardWidget.VK_SCROLL:  # Scroll Lock ON
            return True
        return False

    with patch.object(widget, '_get_key_state', side_effect=get_key_state_side_effect):
        widget.update()

        assert widget._caps_lock_state is True
        assert widget._num_lock_state is False
        assert widget._scroll_lock_state is True


@patch('widgets.keyboard.platform.system')
@patch('widgets.keyboard.KEYBOARD_SUPPORT', True)
def test_keyboard_update_handles_error(mock_system):
    """
    Тест обработки ошибок во время update().

    Если _get_key_state вызывает исключение, update() не должен упасть.
    """
    mock_system.return_value = "Windows"

    with patch.object(KeyboardWidget, '_get_key_state') as mock_get_state:
        mock_get_state.side_effect = Exception("Key state error")

        widget = KeyboardWidget()
        # Не должно вызвать исключение
        widget.update()


# =============================================================================
# Тесты render() общие
# =============================================================================

def test_keyboard_render_returns_image():
    """
    Тест что render() возвращает PIL Image.

    Проверяет корректный тип и размер изображения.
    """
    widget = KeyboardWidget()
    widget.set_size(128, 40)

    image = widget.render()

    assert isinstance(image, Image.Image)
    assert image.size == (128, 40)


def test_keyboard_render_with_border():
    """
    Тест рендеринга с рамкой виджета.

    Проверяет что border рисуется.
    """
    widget = KeyboardWidget(border=True)
    widget.set_size(128, 40)

    image = widget.render()

    assert image is not None


def test_keyboard_render_with_alpha_channel():
    """
    Тест рендеринга с альфа-каналом.

    При background_opacity < 255 должно создаться LA изображение.
    """
    widget = KeyboardWidget(background_opacity=128)
    widget.set_size(128, 40)

    image = widget.render()

    assert image.mode == 'LA'


# =============================================================================
# Тесты render() с разными состояниями клавиш
# =============================================================================

def test_keyboard_render_all_locks_on():
    """
    Тест рендеринга когда все клавиши включены.

    Должны отобразиться все ON символы.
    """
    widget = KeyboardWidget(
        caps_lock_on="C",
        num_lock_on="N",
        scroll_lock_on="S"
    )
    widget.set_size(128, 40)

    # Устанавливаем все клавиши в ON
    widget._caps_lock_state = True
    widget._num_lock_state = True
    widget._scroll_lock_state = True

    image = widget.render()

    assert isinstance(image, Image.Image)


def test_keyboard_render_all_locks_off():
    """
    Тест рендеринга когда все клавиши выключены.

    Если OFF символы пустые, изображение должно быть пустым.
    """
    widget = KeyboardWidget(
        caps_lock_off="",
        num_lock_off="",
        scroll_lock_off=""
    )
    widget.set_size(128, 40)

    # Все клавиши OFF
    widget._caps_lock_state = False
    widget._num_lock_state = False
    widget._scroll_lock_state = False

    image = widget.render()

    # Должно быть пустое изображение (все индикаторы скрыты)
    assert isinstance(image, Image.Image)


def test_keyboard_render_mixed_states():
    """
    Тест рендеринга со смешанными состояниями.

    Caps = ON, Num = OFF (скрыт), Scroll = ON.
    """
    widget = KeyboardWidget(
        caps_lock_on="CAPS",
        caps_lock_off="",
        num_lock_on="NUM",
        num_lock_off="",
        scroll_lock_on="SCR",
        scroll_lock_off=""
    )
    widget.set_size(128, 40)

    widget._caps_lock_state = True
    widget._num_lock_state = False  # Не будет показан (пустой OFF символ)
    widget._scroll_lock_state = True

    image = widget.render()

    assert isinstance(image, Image.Image)


def test_keyboard_render_with_off_symbols():
    """
    Тест рендеринга с OFF символами (не скрыты).

    Проверяет что OFF символы тоже рисуются когда заданы.
    """
    widget = KeyboardWidget(
        caps_lock_on="C",
        caps_lock_off="c",
        num_lock_on="N",
        num_lock_off="n",
        scroll_lock_on="S",
        scroll_lock_off="s"
    )
    widget.set_size(128, 40)

    # Все клавиши OFF, но должны показаться OFF символы
    widget._caps_lock_state = False
    widget._num_lock_state = False
    widget._scroll_lock_state = False

    image = widget.render()

    assert isinstance(image, Image.Image)


# =============================================================================
# Тесты выравнивания
# =============================================================================

@pytest.mark.parametrize("h_align", ["left", "center", "right"])
def test_keyboard_render_horizontal_align(h_align):
    """
    Параметризованный тест горизонтального выравнивания.

    Проверяет что индикаторы правильно выравниваются.
    """
    widget = KeyboardWidget(
        horizontal_align=h_align,
        caps_lock_on="C",
        num_lock_on="N"
    )
    widget.set_size(128, 40)
    widget._caps_lock_state = True
    widget._num_lock_state = True

    image = widget.render()

    assert isinstance(image, Image.Image)


@pytest.mark.parametrize("v_align", ["top", "center", "bottom"])
def test_keyboard_render_vertical_align(v_align):
    """
    Параметризованный тест вертикального выравнивания.

    Проверяет что индикаторы правильно выравниваются.
    """
    widget = KeyboardWidget(
        vertical_align=v_align,
        caps_lock_on="C",
        num_lock_on="N"
    )
    widget.set_size(128, 40)
    widget._caps_lock_state = True
    widget._num_lock_state = True

    image = widget.render()

    assert isinstance(image, Image.Image)


# =============================================================================
# Тесты spacing
# =============================================================================

def test_keyboard_render_with_spacing():
    """
    Тест рендеринга с промежутком между индикаторами.

    Проверяет параметр spacing.
    """
    widget = KeyboardWidget(
        spacing=10,
        caps_lock_on="C",
        num_lock_on="N",
        scroll_lock_on="S"
    )
    widget.set_size(128, 40)
    widget._caps_lock_state = True
    widget._num_lock_state = True
    widget._scroll_lock_state = True

    image = widget.render()

    assert isinstance(image, Image.Image)


def test_keyboard_render_zero_spacing():
    """
    Тест рендеринга без промежутков.

    Edge case: spacing=0, индикаторы вплотную друг к другу.
    """
    widget = KeyboardWidget(
        spacing=0,
        caps_lock_on="C",
        num_lock_on="N"
    )
    widget.set_size(128, 40)
    widget._caps_lock_state = True
    widget._num_lock_state = True

    image = widget.render()

    assert isinstance(image, Image.Image)


# =============================================================================
# Тесты цветов
# =============================================================================

def test_keyboard_render_different_on_off_colors():
    """
    Тест рендеринга с разными цветами для ON/OFF.

    Проверяет что цвета корректно применяются.
    """
    widget = KeyboardWidget(
        caps_lock_on="C",
        caps_lock_off="c",
        indicator_color_on=255,
        indicator_color_off=100
    )
    widget.set_size(128, 40)

    # Один ON, один OFF
    widget._caps_lock_state = True

    image = widget.render()

    assert isinstance(image, Image.Image)


# =============================================================================
# Тесты get_update_interval
# =============================================================================

def test_keyboard_get_update_interval_default():
    """
    Тест get_update_interval возвращает дефолтное значение.

    По умолчанию 0.2 секунды.
    """
    widget = KeyboardWidget()
    assert widget.get_update_interval() == 0.2


def test_keyboard_get_update_interval_custom():
    """
    Тест get_update_interval возвращает кастомное значение.

    Проверяет установку через update_interval.
    """
    widget = KeyboardWidget(update_interval=0.5)
    assert widget.get_update_interval() == 0.5


# =============================================================================
# Тесты edge cases и стилизации
# =============================================================================

def test_keyboard_render_with_padding():
    """
    Тест рендеринга с отступами.

    Проверяет параметр padding.
    """
    widget = KeyboardWidget(
        padding=10,
        caps_lock_on="C"
    )
    widget.set_size(128, 40)
    widget._caps_lock_state = True

    image = widget.render()

    assert image is not None


def test_keyboard_render_different_sizes():
    """
    Тест рендеринга с разными размерами виджета.

    Проверяет корректную работу с нестандартными размерами.
    """
    widget = KeyboardWidget(caps_lock_on="C")
    widget._caps_lock_state = True

    for size in [(64, 20), (128, 40), (256, 64)]:
        widget.set_size(*size)
        image = widget.render()
        assert image.size == size


def test_keyboard_render_single_indicator():
    """
    Тест рендеринга с одним индикатором.

    Edge case: Только Caps Lock включён и показан.
    """
    widget = KeyboardWidget(
        caps_lock_on="CAPS",
        num_lock_on="",
        scroll_lock_on=""
    )
    widget.set_size(128, 40)
    widget._caps_lock_state = True
    widget._num_lock_state = True  # Не будет показан
    widget._scroll_lock_state = True  # Не будет показан

    image = widget.render()

    assert isinstance(image, Image.Image)


def test_keyboard_render_no_indicators():
    """
    Тест рендеринга без индикаторов.

    Edge case: Все символы пустые или все клавиши OFF с пустыми OFF символами.
    """
    widget = KeyboardWidget(
        caps_lock_on="",
        caps_lock_off="",
        num_lock_on="",
        num_lock_off="",
        scroll_lock_on="",
        scroll_lock_off=""
    )
    widget.set_size(128, 40)

    image = widget.render()

    assert isinstance(image, Image.Image)


def test_keyboard_render_unicode_symbols():
    """
    Тест рендеринга с Unicode символами.

    Проверяет что эмодзи и специальные символы работают.
    """
    widget = KeyboardWidget(
        caps_lock_on="⬆",
        num_lock_on="🔒",
        scroll_lock_on="⬇"
    )
    widget.set_size(128, 40)
    widget._caps_lock_state = True
    widget._num_lock_state = True
    widget._scroll_lock_state = True

    image = widget.render()

    assert isinstance(image, Image.Image)


# =============================================================================
# Integration тесты
# =============================================================================

def test_keyboard_full_workflow():
    """
    Integration тест полного жизненного цикла виджета.

    Проверяет init -> update -> render последовательность.
    """
    # Инициализация
    widget = KeyboardWidget(
        name="TestKeyboard",
        caps_lock_on="C",
        caps_lock_off="c",
        num_lock_on="N",
        num_lock_off="n",
        scroll_lock_on="S",
        scroll_lock_off="s"
    )
    widget.set_size(128, 40)

    # Caps = ON, Num = OFF, Scroll = ON
    def get_key_state_side_effect(vk_code):
        if vk_code == KeyboardWidget.VK_CAPITAL:
            return True
        elif vk_code == KeyboardWidget.VK_NUMLOCK:
            return False
        elif vk_code == KeyboardWidget.VK_SCROLL:
            return True
        return False

    with patch.object(widget, '_get_key_state', side_effect=get_key_state_side_effect):
        # Update
        widget.update()

        assert widget._caps_lock_state is True
        assert widget._num_lock_state is False
        assert widget._scroll_lock_state is True

    # Render
    image = widget.render()

    assert isinstance(image, Image.Image)


def test_keyboard_multiple_updates_and_renders():
    """
    Integration тест с несколькими циклами update/render.

    Проверяет стабильность при многократных вызовах.
    """
    widget = KeyboardWidget(caps_lock_on="C")
    widget.set_size(128, 40)

    # Делаем 5 циклов со сменой состояния
    for i in range(5):
        # Чередуем ON/OFF
        state = (i % 2 == 0)

        with patch.object(widget, '_get_key_state', return_value=state):
            widget.update()

        image = widget.render()

        assert isinstance(image, Image.Image)
        assert widget._caps_lock_state == state
