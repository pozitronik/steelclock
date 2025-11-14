"""
Disk Widget - отображает загрузку дисков в различных режимах.
"""

import logging
from typing import Optional, Dict
from collections import deque
from PIL import Image, ImageDraw
import time

try:
    import psutil
except ImportError:
    psutil = None

from core.widget import Widget
from utils.bitmap import create_blank_image
from utils.text_renderer import render_multi_line_text

logger = logging.getLogger(__name__)


class DiskWidget(Widget):
    """
    Виджет мониторинга дисков с поддержкой различных режимов отображения.

    Режимы:
    - text: Текстовый вывод скоростей чтения и записи
    - bar_horizontal: Две горизонтальные полосы (READ/WRITE)
    - bar_vertical: Два вертикальных столбца (READ/WRITE)
    - graph: График истории скоростей

    Отслеживает скорость чтения и записи для выбранного диска.
    """

    def __init__(
        self,
        name: str = "Disk",
        disk_name: str = None,
        display_mode: str = "bar_horizontal",
        update_interval: float = 1.0,
        history_length: int = 30,
        max_speed_mbps: float = -1,
        font: str = None,
        font_size: int = 10,
        horizontal_align: str = "center",
        vertical_align: str = "center",
        background_color: int = 0,
        background_opacity: int = 255,
        border: bool = False,
        border_color: int = 255,
        padding: int = 0,
        bar_border: bool = False,
        read_color: int = 255,
        write_color: int = 200
    ):
        """
        Инициализирует Disk Widget.

        Args:
            name: Имя виджета
            disk_name: Имя диска для мониторинга
                Windows: "PhysicalDrive0", "PhysicalDrive1", ...
                Linux: "sda", "sdb", "nvme0n1", ...
                None = автовыбор первого доступного
            display_mode: Режим отображения ("text", "bar_horizontal", "bar_vertical", "graph")
            update_interval: Интервал обновления в секундах
            history_length: Количество образцов для graph режима
            max_speed_mbps: Максимальная скорость для масштабирования (MB/s, -1=auto)
            font: Шрифт для text режима (имя или путь к TTF файлу)
            font_size: Размер шрифта для text режима (в пикселях)
            horizontal_align: Горизонтальное выравнивание текста ("left", "center", "right")
            vertical_align: Вертикальное выравнивание текста ("top", "center", "bottom")
            background_color: Цвет фона (0-255)
            background_opacity: Прозрачность фона (0=полностью прозрачный, 255=непрозрачный)
            border: Рисовать ли рамку виджета
            border_color: Цвет рамки виджета (0-255)
            padding: Отступ от краёв виджета
            bar_border: Рисовать ли рамку вокруг баров
            read_color: Цвет для скорости чтения (0-255)
            write_color: Цвет для скорости записи (0-255)
        """
        super().__init__(name)

        if psutil is None:
            raise ImportError("psutil library is required for Disk widget. Install: pip install psutil")

        self.disk_name = disk_name
        self.display_mode = display_mode
        self.update_interval_sec = update_interval
        self.history_length = history_length
        self.max_speed_mbps = max_speed_mbps
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
        self.read_color = read_color
        self.write_color = write_color

        # Текущие скорости (байты/сек)
        self._current_read_speed: float = 0.0
        self._current_write_speed: float = 0.0

        # История для graph режима
        self._read_history: deque = deque(maxlen=history_length)
        self._write_history: deque = deque(maxlen=history_length)

        # Для вычисления скорости
        self._last_read_bytes: Optional[int] = None
        self._last_write_bytes: Optional[int] = None
        self._last_update_time: Optional[float] = None

        # Автоопределение максимальной скорости для динамического масштабирования
        self._peak_read_speed: float = 1.0  # MB/s
        self._peak_write_speed: float = 1.0  # MB/s

        # Логируем доступные диски при инициализации
        try:
            available_disks = psutil.disk_io_counters(perdisk=True)
            if available_disks:
                disk_list = ", ".join(available_disks.keys())
                logger.info(f"Available disks: {disk_list}")
            else:
                logger.warning("No disks found by psutil")
        except Exception as e:
            logger.warning(f"Could not enumerate disks: {e}")

        logger.info(
            f"DiskWidget initialized: {name}, disk={disk_name or 'auto'}, mode={display_mode}, "
            f"interval={update_interval}s, max_speed={max_speed_mbps} MB/s"
        )

    def _get_disk_io_counters(self) -> Optional[Dict]:
        """Получает счётчики I/O для выбранного диска."""
        try:
            counters = psutil.disk_io_counters(perdisk=True)

            if not counters:
                return None

            # Если диск не указан, берём первый доступный
            if self.disk_name is None:
                self.disk_name = next(iter(counters.keys()))
                logger.info(f"Auto-selected disk: {self.disk_name}")

            return counters.get(self.disk_name)
        except Exception as e:
            logger.error(f"Failed to get disk I/O counters: {e}")
            return None

    def update(self) -> None:
        """Обновляет данные о загрузке диска."""
        try:
            current_time = time.time()
            counters = self._get_disk_io_counters()

            if counters is None:
                logger.warning(f"No disk counters available for {self.disk_name}")
                self._current_read_speed = 0.0
                self._current_write_speed = 0.0
                return

            current_read_bytes = counters.read_bytes
            current_write_bytes = counters.write_bytes

            # Вычисляем скорость на основе изменения за интервал
            if self._last_read_bytes is not None and self._last_update_time is not None:
                time_delta = current_time - self._last_update_time

                if time_delta > 0:
                    read_delta = current_read_bytes - self._last_read_bytes
                    write_delta = current_write_bytes - self._last_write_bytes

                    # Скорость в байтах/сек
                    self._current_read_speed = max(0.0, read_delta / time_delta)
                    self._current_write_speed = max(0.0, write_delta / time_delta)

                    # Обновляем пиковые значения для автомасштабирования
                    read_mbps = self._current_read_speed / (1024 * 1024)
                    write_mbps = self._current_write_speed / (1024 * 1024)

                    if read_mbps > self._peak_read_speed:
                        self._peak_read_speed = read_mbps
                    if write_mbps > self._peak_write_speed:
                        self._peak_write_speed = write_mbps

                    logger.debug(
                        f"Disk {self.disk_name}: READ={read_mbps:.2f} MB/s, "
                        f"WRITE={write_mbps:.2f} MB/s"
                    )

            # Сохраняем текущие значения для следующей итерации
            self._last_read_bytes = current_read_bytes
            self._last_write_bytes = current_write_bytes
            self._last_update_time = current_time

            # Добавляем в историю для graph режима
            if self.display_mode == "graph":
                self._read_history.append(self._current_read_speed)
                self._write_history.append(self._current_write_speed)

        except Exception as e:
            logger.error(f"Failed to update Disk: {e}")
            self._current_read_speed = 0.0
            self._current_write_speed = 0.0

    def render(self) -> Image.Image:
        """
        Рендерит виджет в зависимости от режима отображения.

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

    def _format_speed(self, bytes_per_sec: float) -> str:
        """Форматирует скорость в удобочитаемый формат."""
        mbps = bytes_per_sec / (1024 * 1024)

        if mbps >= 1000:
            return f"{mbps/1024:.1f}G"
        elif mbps >= 1:
            return f"{mbps:.1f}M"
        else:
            kbps = bytes_per_sec / 1024
            return f"{kbps:.0f}K"

    def _get_speed_percentage(self, bytes_per_sec: float, is_read: bool = True) -> float:
        """
        Вычисляет процент от максимальной скорости.

        Args:
            bytes_per_sec: Скорость в байтах/сек
            is_read: True для чтения, False для записи

        Returns:
            Процент от 0 до 100
        """
        mbps = bytes_per_sec / (1024 * 1024)

        if self.max_speed_mbps > 0:
            # Фиксированное масштабирование
            max_speed = self.max_speed_mbps
        else:
            # Динамическое масштабирование
            max_speed = self._peak_read_speed if is_read else self._peak_write_speed
            max_speed = max(1.0, max_speed)  # Минимум 1 MB/s

        return min(100.0, (mbps / max_speed) * 100.0)

    def _render_text(self, image: Image.Image) -> None:
        """Рендерит текстовое представление скоростей."""
        read_value = self._format_speed(self._current_read_speed)
        write_value = self._format_speed(self._current_write_speed)

        read_text = f"R:{read_value}"
        write_text = f"W:{write_value}"

        lines = [
            (read_text, self.read_color),
            (write_text, self.write_color)
        ]

        render_multi_line_text(
            image, lines,
            font=self.font,
            font_size=self.font_size,
            horizontal_align=self.horizontal_align,
            vertical_align=self.vertical_align,
            padding=self.padding,
            line_spacing=2
        )

    def _render_bar_horizontal(self, image: Image.Image) -> None:
        """Рендерит две горизонтальные полосы (READ вверху, WRITE внизу)."""
        draw = ImageDraw.Draw(image)

        # Подготавливаем цвета с полной непрозрачностью для контента
        read_color = (self.read_color, 255) if image.mode == 'LA' else self.read_color
        write_color = (self.write_color, 255) if image.mode == 'LA' else self.write_color

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        # Две полосы: верхняя для READ, нижняя для WRITE
        bar_h = content_h // 2
        spacing = 1 if content_h > 10 else 0

        # READ бар (верхний)
        read_y = content_y
        read_pct = self._get_speed_percentage(self._current_read_speed, is_read=True)

        if self.bar_border:
            draw.rectangle(
                [content_x, read_y, content_x + content_w - 1, read_y + bar_h - spacing - 1],
                outline=read_color,
                fill=None
            )
            fill_w = int((content_w - 2) * (read_pct / 100.0))
            if fill_w > 0:
                draw.rectangle(
                    [content_x + 1, read_y + 1, content_x + fill_w, read_y + bar_h - spacing - 2],
                    fill=read_color
                )
        else:
            fill_w = int(content_w * (read_pct / 100.0))
            if fill_w > 0:
                draw.rectangle(
                    [content_x, read_y, content_x + fill_w - 1, read_y + bar_h - spacing - 1],
                    fill=read_color
                )

        # WRITE бар (нижний)
        write_y = content_y + bar_h + spacing
        write_pct = self._get_speed_percentage(self._current_write_speed, is_read=False)

        if self.bar_border:
            draw.rectangle(
                [content_x, write_y, content_x + content_w - 1, write_y + bar_h - 1],
                outline=write_color,
                fill=None
            )
            fill_w = int((content_w - 2) * (write_pct / 100.0))
            if fill_w > 0:
                draw.rectangle(
                    [content_x + 1, write_y + 1, content_x + fill_w, write_y + bar_h - 2],
                    fill=write_color
                )
        else:
            fill_w = int(content_w * (write_pct / 100.0))
            if fill_w > 0:
                draw.rectangle(
                    [content_x, write_y, content_x + fill_w - 1, write_y + bar_h - 1],
                    fill=write_color
                )

    def _render_bar_vertical(self, image: Image.Image) -> None:
        """Рендерит два вертикальных столбца (READ слева, WRITE справа)."""
        draw = ImageDraw.Draw(image)

        # Подготавливаем цвета с полной непрозрачностью для контента
        read_color = (self.read_color, 255) if image.mode == 'LA' else self.read_color
        write_color = (self.write_color, 255) if image.mode == 'LA' else self.write_color

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        # Два столбца: левый для READ, правый для WRITE
        bar_w = content_w // 2
        spacing = 1 if content_w > 10 else 0

        # READ столбец (левый)
        read_x = content_x
        read_pct = self._get_speed_percentage(self._current_read_speed, is_read=True)
        fill_h = int(content_h * (read_pct / 100.0))
        fill_y = content_y + content_h - fill_h

        if self.bar_border:
            draw.rectangle(
                [read_x, content_y, read_x + bar_w - spacing - 1, content_y + content_h - 1],
                outline=read_color,
                fill=None
            )
            if fill_h > 2:
                draw.rectangle(
                    [read_x + 1, max(fill_y, content_y + 1), read_x + bar_w - spacing - 2, content_y + content_h - 2],
                    fill=read_color
                )
        else:
            if fill_h > 0:
                draw.rectangle(
                    [read_x, fill_y, read_x + bar_w - spacing - 1, content_y + content_h - 1],
                    fill=read_color
                )

        # WRITE столбец (правый)
        write_x = content_x + bar_w + spacing
        write_pct = self._get_speed_percentage(self._current_write_speed, is_read=False)
        fill_h = int(content_h * (write_pct / 100.0))
        fill_y = content_y + content_h - fill_h

        if self.bar_border:
            draw.rectangle(
                [write_x, content_y, write_x + bar_w - 1, content_y + content_h - 1],
                outline=write_color,
                fill=None
            )
            if fill_h > 2:
                draw.rectangle(
                    [write_x + 1, max(fill_y, content_y + 1), write_x + bar_w - 2, content_y + content_h - 2],
                    fill=write_color
                )
        else:
            if fill_h > 0:
                draw.rectangle(
                    [write_x, fill_y, write_x + bar_w - 1, content_y + content_h - 1],
                    fill=write_color
                )

    def _render_graph(self, image: Image.Image) -> None:
        """Рендерит график истории скоростей (READ и WRITE)."""
        if len(self._read_history) < 2 or len(self._write_history) < 2:
            # Недостаточно данных для графика
            return

        draw = ImageDraw.Draw(image)

        # Подготавливаем цвета с полной непрозрачностью для контента
        read_color = (self.read_color, 255) if image.mode == 'LA' else self.read_color
        write_color = (self.write_color, 255) if image.mode == 'LA' else self.write_color
        read_color_semi = (self.read_color, 85) if image.mode == 'LA' else (self.read_color // 3)
        write_color_semi = (self.write_color, 85) if image.mode == 'LA' else (self.write_color // 3)

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        # READ график
        read_points = []
        # Смещение чтобы график всегда заполнялся справа
        offset = self.history_length - len(self._read_history)
        for i, speed in enumerate(self._read_history):
            # X координата: новые данные всегда появляются справа
            x = content_x + int((offset + i) / max(self.history_length - 1, 1) * content_w)
            pct = self._get_speed_percentage(speed, is_read=True)
            y = content_y + content_h - int((pct / 100.0) * content_h)
            read_points.append((x, y))

        # WRITE график
        write_points = []
        offset = self.history_length - len(self._write_history)
        for i, speed in enumerate(self._write_history):
            x = content_x + int((offset + i) / max(self.history_length - 1, 1) * content_w)
            pct = self._get_speed_percentage(speed, is_read=False)
            y = content_y + content_h - int((pct / 100.0) * content_h)
            write_points.append((x, y))

        # Рисуем заполнение под графиками (сначала заполнение, потом линии)
        if len(write_points) >= 2:
            fill_points = write_points.copy()
            fill_points.append((write_points[-1][0], content_y + content_h))
            fill_points.append((write_points[0][0], content_y + content_h))
            draw.polygon(fill_points, fill=write_color_semi, outline=None)

        if len(read_points) >= 2:
            fill_points = read_points.copy()
            fill_points.append((read_points[-1][0], content_y + content_h))
            fill_points.append((read_points[0][0], content_y + content_h))
            draw.polygon(fill_points, fill=read_color_semi, outline=None)

        # Рисуем линии графиков
        if len(write_points) >= 2:
            draw.line(write_points, fill=write_color, width=1)

        if len(read_points) >= 2:
            draw.line(read_points, fill=read_color, width=1)

    def get_update_interval(self) -> float:
        """Возвращает интервал обновления."""
        return self.update_interval_sec
