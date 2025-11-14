"""
CPU Widget - отображает загрузку процессора в различных режимах.
"""

import logging
from typing import List, Optional
from collections import deque
from PIL import Image, ImageDraw

try:
    import psutil
except ImportError:
    psutil = None

from core.widget import Widget
from utils.bitmap import create_blank_image
from utils.text_renderer import render_single_line_text, render_grid_text

logger = logging.getLogger(__name__)


class CPUWidget(Widget):
    """
    Виджет мониторинга CPU с поддержкой различных режимов отображения.

    Режимы:
    - text: Текстовый вывод загрузки
    - bar_horizontal: Горизонтальные полосы (как в htop)
    - bar_vertical: Вертикальные столбцы
    - graph: График истории загрузки (как в Task Manager)

    Поддерживает агрегированный и per-core режимы.
    """

    def __init__(
        self,
        name: str = "CPU",
        display_mode: str = "bar_horizontal",
        per_core: bool = False,
        update_interval: float = 1.0,
        history_length: int = 30,
        font: Optional[str] = None,
        font_size: int = 10,
        horizontal_align: str = "center",
        vertical_align: str = "center",
        background_color: int = 0,
        background_opacity: int = 255,
        border: bool = False,
        border_color: int = 255,
        padding: int = 0,
        bar_border: bool = False,
        bar_margin: int = 0,
        fill_color: int = 255
    ):
        """
        Инициализирует CPU Widget.

        Args:
            name: Имя виджета
            display_mode: Режим отображения ("text", "bar_horizontal", "bar_vertical", "graph")
            per_core: True = по ядрам, False = агрегированное значение
            update_interval: Интервал обновления в секундах
            history_length: Количество образцов для graph режима
            font: Шрифт для text режима (имя или путь к TTF файлу)
            font_size: Размер шрифта для text режима (в пикселях)
            horizontal_align: Горизонтальное выравнивание текста ("left", "center", "right")
            vertical_align: Вертикальное выравнивание текста ("top", "center", "bottom")
            background_color: Цвет фона (0-255)
            background_opacity: Прозрачность фона (0=полностью прозрачный, 255=непрозрачный)
            border: Рисовать ли рамку виджета
            border_color: Цвет рамки виджета (0-255)
            padding: Отступ от краёв виджета
            bar_border: Рисовать ли рамки вокруг баров (в per-core режиме)
            bar_margin: Отступ между барами (в per-core режиме)
            fill_color: Цвет заполнения баров/графиков (0-255)
        """
        super().__init__(name)

        if psutil is None:
            raise ImportError("psutil library is required for CPU widget. Install: pip install psutil")

        self.display_mode = display_mode
        self.per_core = per_core
        self.update_interval_sec = update_interval
        self.history_length = history_length
        self.font = font
        self.font_size = font_size
        self.horizontal_align = horizontal_align
        self.vertical_align = vertical_align
        self.background_color = background_color
        self.background_opacity = background_opacity
        self.border = border
        self.border_color = border_color
        self.padding = padding
        self.bar_border = bar_border
        self.bar_margin = bar_margin
        self.fill_color = fill_color

        # Текущая загрузка (агрегированная или по ядрам)
        self._current_usage: Optional[float | List[float]] = None

        # История для graph режима (очередь образцов)
        # Каждый элемент: float (aggregate) или List[float] (per-core)
        self._usage_history: deque[float | List[float]] = deque(maxlen=history_length)

        # Количество ядер
        self._core_count = psutil.cpu_count(logical=True)

        # Флаги для однократного показа предупреждений
        self._warned_bar_height = False
        self._warned_graph_height = False

        logger.info(
            f"CPUWidget initialized: {name}, mode={display_mode}, "
            f"per_core={per_core}, cores={self._core_count}, interval={update_interval}s"
        )

    def update(self) -> None:
        """Обновляет данные о загрузке CPU."""
        try:
            if self.per_core:
                # Загрузка по каждому ядру
                usage = psutil.cpu_percent(interval=0.1, percpu=True)
                # Clamp values to 0-100 range
                self._current_usage = [max(0.0, min(100.0, u)) for u in usage]
            else:
                # Агрегированная загрузка
                usage = psutil.cpu_percent(interval=0.1)
                # Clamp to 0-100 range
                self._current_usage = max(0.0, min(100.0, usage))

            # Добавляем в историю для graph режима
            if self.display_mode == "graph":
                self._usage_history.append(self._current_usage)

            # Log first few cores for debugging
            if self.per_core and isinstance(self._current_usage, list):
                logger.debug(f"CPU updated (first 4 cores): {self._current_usage[:4]}")
            else:
                logger.debug(f"CPU updated: {self._current_usage}")

        except Exception as e:
            logger.error(f"Failed to update CPU: {e}")
            self._current_usage = 0.0 if not self.per_core else [0.0] * self._core_count

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
        """Рендерит текстовое представление загрузки CPU (только цифры)."""
        if self.per_core:
            # Per-core: сетка чисел, равномерно распределённых
            render_grid_text(
                image,
                self._current_usage,
                font=self.font,
                font_size=self.font_size,
                color=self.fill_color,
                padding=self.padding,
                decimal_places=0
            )
        else:
            # Агрегированный: одно число с выравниванием
            text = f"{self._current_usage:.0f}"
            render_single_line_text(
                image,
                text,
                font=self.font,
                font_size=self.font_size,
                color=self.fill_color,
                horizontal_align=self.horizontal_align,
                vertical_align=self.vertical_align,
                padding=self.padding
            )

    def _render_bar_horizontal(self, image: Image.Image) -> None:
        """Рендерит горизонтальные полосы загрузки."""
        draw = ImageDraw.Draw(image)

        # Подготавливаем цвета с полной непрозрачностью для контента
        fill_color = (self.fill_color, 255) if image.mode == 'LA' else self.fill_color

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        if self.per_core:
            # Per-core: разделяем высоту на N частей
            cores_count = len(self._current_usage)
            total_margin = self.bar_margin * (cores_count - 1)
            available_h = content_h - total_margin

            if available_h <= 0:
                return

            bar_height = available_h / cores_count

            # Log dimensions for debugging (once)
            if bar_height < 3 and not self._warned_bar_height:
                logger.warning(f"Bar height very small: {bar_height:.2f}px for {cores_count} cores. "
                              f"Consider using aggregate mode or larger widget height.")
                self._warned_bar_height = True

            y = content_y

            for i, usage in enumerate(self._current_usage):
                bar_y = int(y)
                bar_h = int(bar_height)

                if bar_h > 0:
                    # Рисуем рамку бара если нужно
                    if self.bar_border:
                        draw.rectangle(
                            [content_x, bar_y, content_x + content_w - 1, bar_y + bar_h - 1],
                            outline=fill_color,
                            fill=None
                        )
                        # Заполнение внутри рамки
                        fill_w = int((content_w - 2) * (usage / 100.0))
                        if i == 0:  # Log first bar for debugging
                            logger.debug(f"Bar {i}: usage={usage:.1f}%, fill_w={fill_w}/{content_w-2}")
                        if fill_w > 0:
                            draw.rectangle(
                                [content_x + 1, bar_y + 1, content_x + fill_w, bar_y + bar_h - 2],
                                fill=fill_color
                            )
                    else:
                        # Заполнение без рамки
                        fill_w = int(content_w * (usage / 100.0))
                        if i == 0:  # Log first bar for debugging
                            logger.debug(f"Bar {i}: usage={usage:.1f}%, fill_w={fill_w}/{content_w}")
                        if fill_w > 0:
                            draw.rectangle(
                                [content_x, bar_y, content_x + fill_w - 1, bar_y + bar_h - 1],
                                fill=fill_color
                            )

                # Переходим к следующему бару
                y += bar_height
                if i < cores_count - 1:
                    y += self.bar_margin
        else:
            # Агрегированный: один горизонтальный бар на всю ширину
            if self.bar_border:
                draw.rectangle(
                    [content_x, content_y, content_x + content_w - 1, content_y + content_h - 1],
                    outline=fill_color,
                    fill=None
                )
                # Заполнение внутри рамки
                fill_w = int((content_w - 2) * (self._current_usage / 100.0))
                if fill_w > 0:
                    draw.rectangle(
                        [content_x + 1, content_y + 1, content_x + fill_w, content_y + content_h - 2],
                        fill=fill_color
                    )
            else:
                # Заполнение без рамки
                fill_w = int(content_w * (self._current_usage / 100.0))
                if fill_w > 0:
                    draw.rectangle(
                        [content_x, content_y, content_x + fill_w - 1, content_y + content_h - 1],
                        fill=fill_color
                    )

    def _render_bar_vertical(self, image: Image.Image) -> None:
        """Рендерит вертикальные столбцы загрузки."""
        draw = ImageDraw.Draw(image)

        # Подготавливаем цвета с полной непрозрачностью для контента
        fill_color = (self.fill_color, 255) if image.mode == 'LA' else self.fill_color

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        if self.per_core:
            # Per-core: разделяем ширину на N частей
            cores_count = len(self._current_usage)
            total_margin = self.bar_margin * (cores_count - 1)
            available_w = content_w - total_margin

            if available_w <= 0:
                return

            bar_width = available_w / cores_count
            x = content_x

            for i, usage in enumerate(self._current_usage):
                bar_x = int(x)
                bar_w = int(bar_width)

                if bar_w > 0:
                    # Вычисляем заполнение снизу вверх
                    fill_h = int(content_h * (usage / 100.0))
                    fill_y = content_y + content_h - fill_h

                    # Рисуем рамку бара если нужно
                    if self.bar_border:
                        draw.rectangle(
                            [bar_x, content_y, bar_x + bar_w - 1, content_y + content_h - 1],
                            outline=fill_color,
                            fill=None
                        )
                        # Заполнение внутри рамки (снизу вверх)
                        if fill_h > 2:
                            draw.rectangle(
                                [bar_x + 1, max(fill_y, content_y + 1), bar_x + bar_w - 2, content_y + content_h - 2],
                                fill=fill_color
                            )
                    else:
                        # Заполнение без рамки (снизу вверх)
                        if fill_h > 0:
                            draw.rectangle(
                                [bar_x, fill_y, bar_x + bar_w - 1, content_y + content_h - 1],
                                fill=fill_color
                            )

                # Переходим к следующему бару
                x += bar_width
                if i < cores_count - 1:
                    x += self.bar_margin
        else:
            # Агрегированный: один вертикальный бар на всю высоту
            fill_h = int(content_h * (self._current_usage / 100.0))
            fill_y = content_y + content_h - fill_h

            if self.bar_border:
                draw.rectangle(
                    [content_x, content_y, content_x + content_w - 1, content_y + content_h - 1],
                    outline=fill_color,
                    fill=None
                )
                # Заполнение внутри рамки (снизу вверх)
                if fill_h > 2:
                    draw.rectangle(
                        [content_x + 1, max(fill_y, content_y + 1), content_x + content_w - 2, content_y + content_h - 2],
                        fill=fill_color
                    )
            else:
                # Заполнение без рамки (снизу вверх)
                if fill_h > 0:
                    draw.rectangle(
                        [content_x, fill_y, content_x + content_w - 1, content_y + content_h - 1],
                        fill=fill_color
                    )

    def _render_graph(self, image: Image.Image) -> None:
        """Рендерит график истории загрузки."""
        if len(self._usage_history) < 2:
            # Недостаточно данных для графика
            return

        draw = ImageDraw.Draw(image)

        # Подготавливаем цвета с полной непрозрачностью для контента
        fill_color = (self.fill_color, 255) if image.mode == 'LA' else self.fill_color
        fill_color_semi = (self.fill_color, 128) if image.mode == 'LA' else (self.fill_color // 2)

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        if self.per_core:
            # Per-core: разделяем виджет на прямоугольники (горизонтальные секции)
            cores_count = len(self._current_usage)
            total_margin = self.bar_margin * (cores_count - 1)
            available_h = content_h - total_margin

            if available_h <= 0:
                return

            section_height = available_h / cores_count

            # Warn if sections are too small for readable graphs (once)
            if section_height < 8 and not self._warned_graph_height:
                logger.warning(f"Graph section height very small: {section_height:.2f}px for {cores_count} cores. "
                              f"Graph mode requires at least 8px per core. "
                              f"Consider using aggregate mode, fewer cores display, or larger widget height.")
                self._warned_graph_height = True

            y = content_y

            for core_idx in range(cores_count):
                section_y = int(y)
                section_h = int(section_height)

                if section_h > 0:
                    # Рисуем рамку секции если нужно
                    if self.bar_border:
                        draw.rectangle(
                            [content_x, section_y, content_x + content_w - 1, section_y + section_h - 1],
                            outline=fill_color,
                            fill=None
                        )

                    # Вычисляем точки графика для этого ядра
                    points = []
                    # Смещение чтобы график всегда заполнялся справа
                    offset = self.history_length - len(self._usage_history)
                    for i, sample in enumerate(self._usage_history):
                        # X координата: новые данные всегда появляются справа
                        px = content_x + int((offset + i) / max(self.history_length - 1, 1) * content_w)
                        usage = sample[core_idx] if isinstance(sample, list) else 0
                        py = section_y + section_h - int((usage / 100.0) * section_h)
                        points.append((px, py))

                    # Рисуем линию
                    if len(points) >= 2:
                        draw.line(points, fill=fill_color, width=1)

                    # Заполнение под графиком
                    if len(points) >= 2:
                        fill_points = points.copy()
                        fill_points.append((points[-1][0], section_y + section_h))
                        fill_points.append((points[0][0], section_y + section_h))
                        draw.polygon(fill_points, fill=fill_color_semi, outline=None)

                # Переходим к следующей секции
                y += section_height
                if core_idx < cores_count - 1:
                    y += self.bar_margin
        else:
            # Агрегированный график
            points = []
            # Смещение чтобы график всегда заполнялся справа
            offset = self.history_length - len(self._usage_history)
            for i, sample in enumerate(self._usage_history):
                # X координата: новые данные всегда появляются справа
                x = content_x + int((offset + i) / max(self.history_length - 1, 1) * content_w)
                usage = sample if not isinstance(sample, list) else sum(sample) / len(sample)
                y = content_y + content_h - int((usage / 100.0) * content_h)
                points.append((x, y))

            # Рисуем линию
            if len(points) >= 2:
                draw.line(points, fill=fill_color, width=1)

            # Заполнение под графиком
            if len(points) >= 2:
                # Создаём полигон для заливки
                fill_points = points.copy()
                fill_points.append((points[-1][0], content_y + content_h))
                fill_points.append((points[0][0], content_y + content_h))
                draw.polygon(fill_points, fill=fill_color_semi, outline=None)

    def get_update_interval(self) -> float:
        """Возвращает интервал обновления."""
        return self.update_interval_sec
