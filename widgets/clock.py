"""
Clock Widget - отображает текущее время на дисплее с поддержкой стилизации.
"""

import logging
from typing import Optional
from datetime import datetime
from PIL import Image, ImageDraw

from core.widget import Widget
from utils.bitmap import create_blank_image, draw_aligned_text

logger = logging.getLogger(__name__)


class ClockWidget(Widget):
    """
    Виджет отображения часов с поддержкой стилизации.

    Поддерживает:
    - Настраиваемый формат времени
    - Фон и рамка
    - Размер шрифта
    - Интервал обновления
    """

    def __init__(
        self,
        name: str = "Clock",
        format_string: str = "%H:%M:%S",
        update_interval: float = 1.0,
        font_size: int = 12,
        font: Optional[str] = None,
        background_color: int = 0,
        background_opacity: int = 255,
        border: bool = False,
        border_color: int = 255,
        horizontal_align: str = "center",
        vertical_align: str = "center",
        padding: int = 0
    ):
        """
        Инициализирует Clock Widget.

        Args:
            name: Имя виджета
            format_string: Формат даты/времени (strftime format)
                Примеры:
                - "%H:%M:%S" - 15:43:27
                - "%H:%M" - 15:43
                - "%Y-%m-%d %H:%M" - 2025-11-14 15:43
                - "%d.%m.%Y" - 14.11.2025
            update_interval: Интервал обновления в секундах
            font_size: Размер шрифта
            font: Имя шрифта или путь к файлу (None = default)
                Примеры:
                - "Arial"
                - "Consolas"
                - "C:/Windows/Fonts/arial.ttf"
            background_color: Цвет фона (0-255, 0=чёрный, 255=белый)
            background_opacity: Прозрачность фона (0=полностью прозрачный, 255=непрозрачный)
            border: Рисовать ли рамку
            border_color: Цвет рамки (0-255)
            horizontal_align: Горизонтальное выравнивание ("left", "center", "right")
            vertical_align: Вертикальное выравнивание ("top", "center", "bottom")
            padding: Отступ от краёв в пикселях
        """
        super().__init__(name)

        self.format_string = format_string
        self.update_interval_sec = update_interval
        self.font_size = font_size
        self.font = font
        self.background_color = background_color
        self.background_opacity = background_opacity
        self.border = border
        self.border_color = border_color
        self.horizontal_align = horizontal_align
        self.vertical_align = vertical_align
        self.padding = padding

        # Текущее время (обновляется в update())
        self._current_time: datetime = None
        self._formatted_time: str = ""

        logger.info(
            f"ClockWidget initialized: {name}, format='{format_string}', "
            f"interval={update_interval}s, font_size={font_size}, font={font or 'default'}, "
            f"bg={background_color}, border={border}, align={horizontal_align}/{vertical_align}, padding={padding}"
        )

    def update(self) -> None:
        """Обновляет текущее время."""
        try:
            self._current_time = datetime.now()
            self._formatted_time = self._current_time.strftime(self.format_string)
            logger.debug(f"Clock updated: {self._formatted_time}")
        except Exception as e:
            logger.error(f"Failed to update clock: {e}")
            self._formatted_time = "ERROR"

    def render(self) -> Image.Image:
        """
        Рендерит время на изображении с учётом стилей.

        Returns:
            Image.Image: Изображение с отцентрованным текстом времени
        """
        # Если update() ещё не вызывался, обновляем сейчас
        if not self._formatted_time:
            self.update()

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
            # Рамка всегда непрозрачная (полная видимость)
            border_color = (self.border_color, 255) if image.mode == 'LA' else self.border_color
            draw.rectangle(
                [0, 0, width-1, height-1],
                outline=border_color,
                fill=None
            )

        # Рисуем текст с заданным выравниванием
        # Текст должен контрастировать с фоном
        text_color = 0 if self.background_color > 128 else 255

        draw_aligned_text(
            image,
            self._formatted_time,
            font_size=self.font_size,
            color=text_color,
            font=self.font,
            horizontal_align=self.horizontal_align,
            vertical_align=self.vertical_align,
            padding=self.padding
        )

        return image

    def get_update_interval(self) -> float:
        """Возвращает интервал обновления."""
        return self.update_interval_sec

    def set_format(self, format_string: str) -> None:
        """
        Изменяет формат отображения времени.

        Args:
            format_string: Новый формат (strftime format)
        """
        self.format_string = format_string
        logger.info(f"Clock format changed to: {format_string}")
        self.update()

    def get_current_time_string(self) -> str:
        """Возвращает текущее отформатированное время."""
        return self._formatted_time
