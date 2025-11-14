"""
Memory Widget - отображает загрузку памяти в различных режимах.
"""

import logging
from typing import Optional
from collections import deque
from PIL import Image, ImageDraw

try:
    import psutil
except ImportError:
    psutil = None

from core.widget import Widget
from utils.bitmap import create_blank_image

logger = logging.getLogger(__name__)


class MemoryWidget(Widget):
    """
    Виджет мониторинга памяти с поддержкой различных режимов отображения.

    Режимы:
    - text: Текстовый вывод загрузки (только цифра)
    - bar_horizontal: Горизонтальная полоса
    - bar_vertical: Вертикальный столбец
    - graph: График истории загрузки

    Чистый примитив визуализации без текстовых меток.
    """

    def __init__(
        self,
        name: str = "Memory",
        display_mode: str = "bar_horizontal",
        update_interval: float = 1.0,
        history_length: int = 30,
        background_color: int = 0,
        border: bool = False,
        border_color: int = 255,
        padding: int = 0,
        bar_border: bool = False,
        fill_color: int = 255
    ):
        """
        Инициализирует Memory Widget.

        Args:
            name: Имя виджета
            display_mode: Режим отображения ("text", "bar_horizontal", "bar_vertical", "graph")
            update_interval: Интервал обновления в секундах
            history_length: Количество образцов для graph режима
            background_color: Цвет фона (0-255)
            border: Рисовать ли рамку виджета
            border_color: Цвет рамки виджета (0-255)
            padding: Отступ от краёв виджета
            bar_border: Рисовать ли рамку вокруг бара
            fill_color: Цвет заполнения бара/графика (0-255)
        """
        super().__init__(name)

        if psutil is None:
            raise ImportError("psutil library is required for Memory widget. Install: pip install psutil")

        self.display_mode = display_mode
        self.update_interval_sec = update_interval
        self.history_length = history_length
        self.background_color = background_color
        self.border = border
        self.border_color = border_color
        self.padding = padding
        self.bar_border = bar_border
        self.fill_color = fill_color

        # Текущая загрузка памяти (процент)
        self._current_usage: Optional[float] = None

        # История для graph режима (очередь образцов)
        self._usage_history: deque = deque(maxlen=history_length)

        logger.info(
            f"MemoryWidget initialized: {name}, mode={display_mode}, interval={update_interval}s"
        )

    def update(self) -> None:
        """Обновляет данные о загрузке памяти."""
        try:
            # Получаем информацию о памяти
            mem = psutil.virtual_memory()
            # Clamp to 0-100 range
            self._current_usage = max(0.0, min(100.0, mem.percent))

            # Добавляем в историю для graph режима
            if self.display_mode == "graph":
                self._usage_history.append(self._current_usage)

            logger.debug(f"Memory updated: {self._current_usage:.1f}%")

        except Exception as e:
            logger.error(f"Failed to update Memory: {e}")
            self._current_usage = 0.0

    def render(self) -> Image.Image:
        """
        Рендерит виджет в зависимости от режима отображения.

        Returns:
            Image.Image: Отрендеренное изображение
        """
        # Если update() ещё не вызывался, обновляем сейчас
        if self._current_usage is None:
            self.update()

        width, height = self.get_preferred_size()

        # Создаём изображение с фоном
        image = create_blank_image(width, height, color=self.background_color)

        # Рисуем рамку если нужно
        if self.border:
            draw = ImageDraw.Draw(image)
            draw.rectangle(
                [0, 0, width-1, height-1],
                outline=self.border_color,
                fill=None
            )

        # Рендерим в зависимости от режима
        if self.display_mode == "text":
            self._render_text(image)
        elif self.display_mode == "bar_horizontal":
            self._render_bar_horizontal(image)
        elif self.display_mode == "bar_vertical":
            self._render_bar_vertical(image)
        elif self.display_mode == "graph":
            self._render_graph(image)
        else:
            logger.warning(f"Unknown display mode: {self.display_mode}")

        return image

    def _render_text(self, image: Image.Image) -> None:
        """Рендерит текстовое представление загрузки памяти (только цифра)."""
        draw = ImageDraw.Draw(image)

        # Вычисляем доступное пространство (внутри рамки и padding)
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        # Одно число по центру
        text = f"{self._current_usage:.0f}"

        # Центрируем в доступном пространстве
        bbox = draw.textbbox((0, 0), text)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = content_x + (content_w - text_w) // 2
        y = content_y + (content_h - text_h) // 2

        draw.text((x, y), text, fill=self.fill_color)

    def _render_bar_horizontal(self, image: Image.Image) -> None:
        """Рендерит горизонтальную полосу загрузки."""
        draw = ImageDraw.Draw(image)

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        # Один горизонтальный бар на всю ширину
        if self.bar_border:
            draw.rectangle(
                [content_x, content_y, content_x + content_w - 1, content_y + content_h - 1],
                outline=self.fill_color,
                fill=None
            )
            # Заполнение внутри рамки
            fill_w = int((content_w - 2) * (self._current_usage / 100.0))
            if fill_w > 0:
                draw.rectangle(
                    [content_x + 1, content_y + 1, content_x + fill_w, content_y + content_h - 2],
                    fill=self.fill_color
                )
        else:
            # Заполнение без рамки
            fill_w = int(content_w * (self._current_usage / 100.0))
            if fill_w > 0:
                draw.rectangle(
                    [content_x, content_y, content_x + fill_w - 1, content_y + content_h - 1],
                    fill=self.fill_color
                )

    def _render_bar_vertical(self, image: Image.Image) -> None:
        """Рендерит вертикальный столбец загрузки."""
        draw = ImageDraw.Draw(image)

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        # Один вертикальный бар на всю высоту
        fill_h = int(content_h * (self._current_usage / 100.0))
        fill_y = content_y + content_h - fill_h

        if self.bar_border:
            draw.rectangle(
                [content_x, content_y, content_x + content_w - 1, content_y + content_h - 1],
                outline=self.fill_color,
                fill=None
            )
            # Заполнение внутри рамки (снизу вверх)
            if fill_h > 2:
                draw.rectangle(
                    [content_x + 1, max(fill_y, content_y + 1), content_x + content_w - 2, content_y + content_h - 2],
                    fill=self.fill_color
                )
        else:
            # Заполнение без рамки (снизу вверх)
            if fill_h > 0:
                draw.rectangle(
                    [content_x, fill_y, content_x + content_w - 1, content_y + content_h - 1],
                    fill=self.fill_color
                )

    def _render_graph(self, image: Image.Image) -> None:
        """Рендерит график истории загрузки."""
        if len(self._usage_history) < 2:
            # Недостаточно данных для графика
            return

        draw = ImageDraw.Draw(image)

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        # График истории
        points = []
        for i, sample in enumerate(self._usage_history):
            x = content_x + int((i / (len(self._usage_history) - 1)) * content_w)
            y = content_y + content_h - int((sample / 100.0) * content_h)
            points.append((x, y))

        # Рисуем линию
        if len(points) >= 2:
            draw.line(points, fill=self.fill_color, width=1)

        # Заполнение под графиком
        if len(points) >= 2:
            # Создаём полигон для заливки
            fill_points = points.copy()
            fill_points.append((points[-1][0], content_y + content_h))
            fill_points.append((points[0][0], content_y + content_h))
            draw.polygon(fill_points, fill=self.fill_color // 2, outline=None)

    def get_update_interval(self) -> float:
        """Возвращает интервал обновления."""
        return self.update_interval_sec
