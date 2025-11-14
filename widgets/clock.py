"""
Clock Widget - отображает текущее время на дисплее.
"""

import logging
from datetime import datetime
from PIL import Image

from core.widget import Widget
from utils.bitmap import create_blank_image, draw_centered_text

logger = logging.getLogger(__name__)


class ClockWidget(Widget):
    """
    Виджет отображения часов.

    Показывает текущее время в настраиваемом формате.
    Обновляется каждую секунду.
    """

    def __init__(
        self,
        name: str = "Clock",
        format_string: str = "%H:%M:%S",
        update_interval: float = 1.0,
        font_size: int = 12
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
        """
        super().__init__(name)

        self.format_string = format_string
        self.update_interval_sec = update_interval
        self.font_size = font_size

        # Текущее время (обновляется в update())
        self._current_time: datetime = None
        self._formatted_time: str = ""

        logger.info(f"ClockWidget initialized: format='{format_string}', interval={update_interval}s")

    def update(self) -> None:
        """
        Обновляет текущее время.

        Вызывается каждую секунду (согласно get_update_interval()).
        """
        try:
            self._current_time = datetime.now()
            self._formatted_time = self._current_time.strftime(self.format_string)

            logger.debug(f"Clock updated: {self._formatted_time}")

        except Exception as e:
            logger.error(f"Failed to update clock: {e}")
            self._formatted_time = "ERROR"

    def render(self) -> Image.Image:
        """
        Рендерит время на изображении.

        Returns:
            Image.Image: Изображение с отцентрованным текстом времени

        Raises:
            Exception: При ошибке рендеринга
        """
        # Если update() ещё не вызывался, обновляем сейчас
        if not self._formatted_time:
            self.update()

        # Создаём пустое изображение
        width, height = self.get_preferred_size()
        image = create_blank_image(width, height, color=0)

        # Рисуем время по центру
        draw_centered_text(
            image,
            self._formatted_time,
            font_size=self.font_size,
            color=255
        )

        return image

    def get_update_interval(self) -> float:
        """
        Возвращает интервал обновления.

        Returns:
            float: Интервал в секундах (по умолчанию 1.0)
        """
        return self.update_interval_sec

    def set_format(self, format_string: str) -> None:
        """
        Изменяет формат отображения времени.

        Args:
            format_string: Новый формат (strftime format)
        """
        self.format_string = format_string
        logger.info(f"Clock format changed to: {format_string}")

        # Обновляем сразу чтобы показать новый формат
        self.update()

    def get_current_time_string(self) -> str:
        """
        Возвращает текущее отформатированное время.

        Returns:
            str: Отформатированная строка времени
        """
        return self._formatted_time
