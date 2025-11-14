"""
Keyboard Widget - отображает статус клавиш-индикаторов клавиатуры.
"""

import logging
import platform
from typing import Optional
from PIL import Image, ImageDraw

from core.widget import Widget
from utils.bitmap import create_blank_image, load_font

logger = logging.getLogger(__name__)

# Попытка импортировать необходимые модули для проверки состояния клавиш
try:
    if platform.system() == "Windows":
        import ctypes
        KEYBOARD_SUPPORT = True
    else:
        # На Linux можно использовать Xlib, но это сложнее
        # Пока поддержка только для Windows
        KEYBOARD_SUPPORT = False
        logger.warning("Keyboard lock state detection is only supported on Windows")
except ImportError:
    KEYBOARD_SUPPORT = False
    logger.warning("Failed to import required modules for keyboard state detection")


class KeyboardWidget(Widget):
    """
    Виджет индикации состояния клавиш-индикаторов клавиатуры.

    Отображает состояние:
    - Caps Lock
    - Num Lock
    - Scroll Lock

    Каждый индикатор может иметь свой символ для состояний ON и OFF.
    """

    # Виртуальные коды клавиш для Windows
    VK_CAPITAL = 0x14  # Caps Lock
    VK_NUMLOCK = 0x90  # Num Lock
    VK_SCROLL = 0x91   # Scroll Lock

    def __init__(
        self,
        name: str = "Keyboard",
        update_interval: float = 0.2,
        font: str = None,
        font_size: int = 10,
        horizontal_align: str = "center",
        vertical_align: str = "center",
        background_color: int = 0,
        background_opacity: int = 255,
        border: bool = False,
        border_color: int = 255,
        padding: int = 2,
        spacing: int = 3,
        caps_lock_on: str = "⬆",
        caps_lock_off: str = "",
        num_lock_on: str = "🔒",
        num_lock_off: str = "",
        scroll_lock_on: str = "⬇",
        scroll_lock_off: str = "",
        indicator_color_on: int = 255,
        indicator_color_off: int = 100
    ):
        """
        Инициализирует Keyboard Widget.

        Args:
            name: Имя виджета
            update_interval: Интервал обновления в секундах
            font: Шрифт (имя или путь к TTF файлу)
                Для отображения эмодзи используйте:
                - Windows: "Segoe UI Emoji"
                - Linux: "Noto Color Emoji"
            font_size: Размер шрифта (в пикселях)
            horizontal_align: Горизонтальное выравнивание ("left", "center", "right")
            vertical_align: Вертикальное выравнивание ("top", "center", "bottom")
            background_color: Цвет фона (0-255)
            background_opacity: Прозрачность фона (0=полностью прозрачный, 255=непрозрачный)
            border: Рисовать ли рамку виджета
            border_color: Цвет рамки виджета (0-255)
            padding: Отступ от краёв виджета
            spacing: Промежуток между индикаторами (в пикселях)
            caps_lock_on: Символ для Caps Lock в состоянии ON
            caps_lock_off: Символ для Caps Lock в состоянии OFF (пустая строка = не показывать)
            num_lock_on: Символ для Num Lock в состоянии ON
            num_lock_off: Символ для Num Lock в состоянии OFF (пустая строка = не показывать)
            scroll_lock_on: Символ для Scroll Lock в состоянии ON
            scroll_lock_off: Символ для Scroll Lock в состоянии OFF (пустая строка = не показывать)
            indicator_color_on: Цвет символов в состоянии ON (0-255)
            indicator_color_off: Цвет символов в состоянии OFF (0-255)
        """
        super().__init__(name)

        if not KEYBOARD_SUPPORT:
            logger.warning("Keyboard widget initialized but keyboard state detection is not supported on this platform")

        self.update_interval_sec = update_interval
        self.font = font
        self.font_size = font_size
        self.horizontal_align = horizontal_align
        self.vertical_align = vertical_align
        self.background_color = background_color
        self.background_opacity = background_opacity
        self.border = border
        self.border_color = border_color
        self.padding = padding
        self.spacing = spacing

        # Символы для индикаторов
        self.caps_lock_on = caps_lock_on
        self.caps_lock_off = caps_lock_off
        self.num_lock_on = num_lock_on
        self.num_lock_off = num_lock_off
        self.scroll_lock_on = scroll_lock_on
        self.scroll_lock_off = scroll_lock_off

        # Цвета
        self.indicator_color_on = indicator_color_on
        self.indicator_color_off = indicator_color_off

        # Текущее состояние клавиш
        self._caps_lock_state: bool = False
        self._num_lock_state: bool = False
        self._scroll_lock_state: bool = False

        logger.info(
            f"KeyboardWidget initialized: {name}, interval={update_interval}s, "
            f"font_size={font_size}"
        )

    def _get_key_state(self, vk_code: int) -> bool:
        """
        Получает состояние клавиши-индикатора.

        Args:
            vk_code: Виртуальный код клавиши

        Returns:
            True если клавиша включена, False иначе
        """
        if not KEYBOARD_SUPPORT or platform.system() != "Windows":
            return False

        try:
            # GetKeyState возвращает ненулевое значение если клавиша включена
            state = ctypes.windll.user32.GetKeyState(vk_code)
            # Младший бит показывает состояние toggle (включено/выключено)
            return bool(state & 1)
        except Exception as e:
            logger.error(f"Failed to get key state for VK {vk_code}: {e}")
            return False

    def update(self) -> None:
        """Обновляет состояние клавиш-индикаторов."""
        try:
            self._caps_lock_state = self._get_key_state(self.VK_CAPITAL)
            self._num_lock_state = self._get_key_state(self.VK_NUMLOCK)
            self._scroll_lock_state = self._get_key_state(self.VK_SCROLL)

            logger.debug(
                f"Keyboard state: CAPS={self._caps_lock_state}, "
                f"NUM={self._num_lock_state}, SCROLL={self._scroll_lock_state}"
            )
        except Exception as e:
            logger.error(f"Failed to update Keyboard: {e}")

    def render(self) -> Image.Image:
        """
        Рендерит виджет с индикаторами клавиатуры.

        Returns:
            Image.Image: Отрендеренное изображение
        """
        width, height = self.get_preferred_size()

        # Создаём изображение с фоном
        image = create_blank_image(
            width, height,
            color=self.background_color,
            opacity=self.background_opacity
        )

        # Рисуем рамку если нужно
        if self.border:
            draw = ImageDraw.Draw(image)
            border_color = (self.border_color, 255) if image.mode == 'LA' else self.border_color
            draw.rectangle(
                [0, 0, width-1, height-1],
                outline=border_color,
                fill=None
            )

        # Формируем текст индикаторов
        indicators = []

        # Caps Lock
        if self._caps_lock_state:
            if self.caps_lock_on:
                indicators.append((self.caps_lock_on, self.indicator_color_on))
        else:
            if self.caps_lock_off:
                indicators.append((self.caps_lock_off, self.indicator_color_off))

        # Num Lock
        if self._num_lock_state:
            if self.num_lock_on:
                indicators.append((self.num_lock_on, self.indicator_color_on))
        else:
            if self.num_lock_off:
                indicators.append((self.num_lock_off, self.indicator_color_off))

        # Scroll Lock
        if self._scroll_lock_state:
            if self.scroll_lock_on:
                indicators.append((self.scroll_lock_on, self.indicator_color_on))
        else:
            if self.scroll_lock_off:
                indicators.append((self.scroll_lock_off, self.indicator_color_off))

        # Рендерим индикаторы
        if indicators:
            self._render_indicators(image, indicators)

        return image

    def _render_indicators(self, image: Image.Image, indicators: list) -> None:
        """
        Рендерит индикаторы на изображении.

        Args:
            image: PIL Image для рисования
            indicators: Список кортежей (символ, цвет)
        """
        draw = ImageDraw.Draw(image)
        font_obj = load_font(self.font, self.font_size)

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        # Вычисляем размеры каждого индикатора
        indicator_sizes = []
        total_width = 0

        for i, (symbol, _) in enumerate(indicators):
            bbox = draw.textbbox((0, 0), symbol, font=font_obj)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            indicator_sizes.append((width, height))
            total_width += width
            if i < len(indicators) - 1:
                total_width += self.spacing

        # Вычисляем максимальную высоту для вертикального выравнивания
        max_height = max(h for _, h in indicator_sizes) if indicator_sizes else 0

        # Вычисляем начальную X координату в зависимости от выравнивания
        if self.horizontal_align == "left":
            current_x = content_x
        elif self.horizontal_align == "right":
            current_x = content_x + content_w - total_width
        else:  # center
            current_x = content_x + (content_w - total_width) // 2

        # Рендерим каждый индикатор
        for (symbol, color), (width, height) in zip(indicators, indicator_sizes):
            # Вычисляем Y координату в зависимости от вертикального выравнивания
            if self.vertical_align == "top":
                y = content_y
            elif self.vertical_align == "bottom":
                y = content_y + content_h - height
            else:  # center
                y = content_y + (content_h - height) // 2

            # Текст всегда непрозрачный (полная видимость)
            text_color = (color, 255) if image.mode == 'LA' else color
            draw.text((current_x, y), symbol, fill=text_color, font=font_obj)

            # Сдвигаем X координату для следующего индикатора
            current_x += width + self.spacing

    def get_update_interval(self) -> float:
        """Возвращает интервал обновления."""
        return self.update_interval_sec
