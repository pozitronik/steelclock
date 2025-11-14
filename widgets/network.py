"""
Network Widget - отображает скорость сети (RX/TX) в различных режимах.
"""

import logging
from typing import Optional, Tuple
from collections import deque
from PIL import Image, ImageDraw

try:
    import psutil
except ImportError:
    psutil = None

from core.widget import Widget
from utils.bitmap import create_blank_image, load_font

logger = logging.getLogger(__name__)


class NetworkWidget(Widget):
    """
    Виджет мониторинга сети с поддержкой различных режимов отображения.

    Режимы:
    - text: Текстовый вывод скорости (только цифры)
    - bar_horizontal: Две горизонтальные полосы (RX и TX)
    - bar_vertical: Два вертикальных столбца (RX и TX)
    - graph: Два наложенных графика истории (RX и TX)

    Отображает RX (download) и TX (upload) одновременно.
    Чистый примитив визуализации без текстовых меток.
    """

    def __init__(
        self,
        name: str = "Network",
        interface: str = "eth0",
        display_mode: str = "bar_horizontal",
        update_interval: float = 1.0,
        history_length: int = 30,
        max_speed_mbps: float = 100.0,
        speed_unit: str = "kbps",
        font: Optional[str] = None,
        font_size: int = 10,
        horizontal_align: str = "center",
        vertical_align: str = "center",
        background_color: int = 0,
        border: bool = False,
        border_color: int = 255,
        padding: int = 0,
        bar_border: bool = False,
        bar_margin: int = 0,
        rx_color: int = 255,
        tx_color: int = 128
    ):
        """
        Инициализирует Network Widget.

        Args:
            name: Имя виджета
            interface: Имя сетевого интерфейса (например, "eth0", "wlan0", "Ethernet")
            display_mode: Режим отображения ("text", "bar_horizontal", "bar_vertical", "graph")
            update_interval: Интервал обновления в секундах
            history_length: Количество образцов для graph режима
            max_speed_mbps: Максимальная скорость для масштабирования (Mbps), -1 = динамическое
            speed_unit: Единица измерения для text режима ("bps", "kbps", "mbps", "gbps")
            font: Шрифт для text режима (имя или путь к TTF файлу)
            font_size: Размер шрифта для text режима (в пикселях)
            horizontal_align: Горизонтальное выравнивание текста ("left", "center", "right")
            vertical_align: Вертикальное выравнивание текста ("top", "center", "bottom")
            background_color: Цвет фона (0-255)
            border: Рисовать ли рамку виджета
            border_color: Цвет рамки виджета (0-255)
            padding: Отступ от краёв виджета
            bar_border: Рисовать ли рамки вокруг баров
            bar_margin: Отступ между RX и TX барами
            rx_color: Цвет для RX (download) (0-255)
            tx_color: Цвет для TX (upload) (0-255)
        """
        super().__init__(name)

        if psutil is None:
            raise ImportError("psutil library is required for Network widget. Install: pip install psutil")

        self.interface = interface
        self.display_mode = display_mode
        self.update_interval_sec = update_interval
        self.history_length = history_length
        self.max_speed_mbps = max_speed_mbps
        self.dynamic_scaling = (max_speed_mbps < 0)
        self.max_speed_bytes = max_speed_mbps * 1024 * 1024 / 8 if max_speed_mbps > 0 else 1.0  # Mbps to bytes/sec
        self.speed_unit = speed_unit.lower()
        self.font = font
        self.font_size = font_size
        self.horizontal_align = horizontal_align
        self.vertical_align = vertical_align
        self.background_color = background_color
        self.border = border
        self.border_color = border_color
        self.padding = padding
        self.bar_border = bar_border
        self.bar_margin = bar_margin
        self.rx_color = rx_color
        self.tx_color = tx_color

        # Текущая скорость (RX, TX) в байтах/сек
        self._current_rx_speed: Optional[float] = None
        self._current_tx_speed: Optional[float] = None

        # Предыдущие значения счётчиков для вычисления дельты
        self._prev_rx_bytes: Optional[int] = None
        self._prev_tx_bytes: Optional[int] = None
        self._prev_time: Optional[float] = None

        # История для graph режима (очереди кортежей (rx_speed, tx_speed))
        self._rx_history: deque = deque(maxlen=history_length)
        self._tx_history: deque = deque(maxlen=history_length)

        # Флаг предупреждения об отсутствующем интерфейсе
        self._warned_interface = False

        scaling_mode = "dynamic" if self.dynamic_scaling else f"{max_speed_mbps}Mbps"
        logger.info(
            f"NetworkWidget initialized: {name}, interface={interface}, mode={display_mode}, "
            f"interval={update_interval}s, scaling={scaling_mode}, unit={speed_unit}"
        )

    def update(self) -> None:
        """Обновляет данные о скорости сети."""
        try:
            import time

            # Получаем статистику по всем интерфейсам
            net_io = psutil.net_io_counters(pernic=True)

            if self.interface not in net_io:
                if not self._warned_interface:
                    available = list(net_io.keys())
                    logger.error(f"Network interface '{self.interface}' not found. Available: {available}")
                    self._warned_interface = True
                self._current_rx_speed = 0.0
                self._current_tx_speed = 0.0
                return

            stats = net_io[self.interface]
            current_time = time.time()

            # Вычисляем скорость на основе дельты
            if self._prev_rx_bytes is not None and self._prev_time is not None:
                time_delta = current_time - self._prev_time
                if time_delta > 0:
                    rx_delta = stats.bytes_recv - self._prev_rx_bytes
                    tx_delta = stats.bytes_sent - self._prev_tx_bytes

                    # Скорость в байтах/сек
                    self._current_rx_speed = max(0.0, rx_delta / time_delta)
                    self._current_tx_speed = max(0.0, tx_delta / time_delta)
                else:
                    self._current_rx_speed = 0.0
                    self._current_tx_speed = 0.0
            else:
                # Первое измерение - нет предыдущих данных
                self._current_rx_speed = 0.0
                self._current_tx_speed = 0.0

            # Сохраняем текущие значения для следующей итерации
            self._prev_rx_bytes = stats.bytes_recv
            self._prev_tx_bytes = stats.bytes_sent
            self._prev_time = current_time

            # Добавляем в историю для graph режима
            if self.display_mode == "graph":
                self._rx_history.append(self._current_rx_speed)
                self._tx_history.append(self._current_tx_speed)
                logger.debug(f"Added to history: RX={self._current_rx_speed/1024:.1f}KB/s, TX={self._current_tx_speed/1024:.1f}KB/s, "
                           f"history_len={len(self._rx_history)}/{self.history_length}")

            logger.debug(f"Network updated: RX={self._current_rx_speed/1024:.1f}KB/s, TX={self._current_tx_speed/1024:.1f}KB/s")

        except Exception as e:
            logger.error(f"Failed to update Network: {e}")
            self._current_rx_speed = 0.0
            self._current_tx_speed = 0.0

    def render(self) -> Image.Image:
        """
        Рендерит виджет в зависимости от режима отображения.

        Returns:
            Image.Image: Отрендеренное изображение
        """
        # Если update() ещё не вызывался, обновляем сейчас
        if self._current_rx_speed is None:
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

    def _get_speed_percentage(self, speed_bytes: float) -> float:
        """Вычисляет процент от максимальной скорости."""
        if self.dynamic_scaling:
            # Динамическое масштабирование: находим максимум в истории
            max_rx = max(self._rx_history) if len(self._rx_history) > 0 else 1.0
            max_tx = max(self._tx_history) if len(self._tx_history) > 0 else 1.0
            max_speed = max(max_rx, max_tx, 1.0)  # Минимум 1 байт для избежания деления на 0
            return min(100.0, (speed_bytes / max_speed) * 100.0)
        else:
            # Фиксированное масштабирование
            return min(100.0, (speed_bytes / self.max_speed_bytes) * 100.0)

    def _format_speed(self, speed_bytes: float) -> str:
        """Форматирует скорость в соответствии с выбранной единицей измерения."""
        if self.speed_unit == "bps":
            # Биты в секунду
            return f"{speed_bytes * 8:.0f}"
        elif self.speed_unit == "kbps":
            # Килобиты в секунду
            return f"{speed_bytes * 8 / 1024:.0f}"
        elif self.speed_unit == "mbps":
            # Мегабиты в секунду
            return f"{speed_bytes * 8 / 1024 / 1024:.1f}"
        elif self.speed_unit == "gbps":
            # Гигабиты в секунду
            return f"{speed_bytes * 8 / 1024 / 1024 / 1024:.2f}"
        else:
            # По умолчанию kbps
            return f"{speed_bytes * 8 / 1024:.0f}"

    def _render_text(self, image: Image.Image) -> None:
        """Рендерит текстовое представление скорости (RX и TX с префиксами)."""
        draw = ImageDraw.Draw(image)

        # Загружаем шрифт
        font_obj = load_font(self.font, self.font_size)

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        # Форматируем скорость с префиксами
        rx_value = self._format_speed(self._current_rx_speed)
        tx_value = self._format_speed(self._current_tx_speed)
        rx_text = f"RX:{rx_value}"
        tx_text = f"TX:{tx_value}"

        # Вычисляем размеры каждой строки
        rx_bbox = draw.textbbox((0, 0), rx_text, font=font_obj)
        rx_w = rx_bbox[2] - rx_bbox[0]
        rx_h = rx_bbox[3] - rx_bbox[1]

        tx_bbox = draw.textbbox((0, 0), tx_text, font=font_obj)
        tx_w = tx_bbox[2] - tx_bbox[0]
        tx_h = tx_bbox[3] - tx_bbox[1]

        # Общая высота блока (две строки с небольшим промежутком)
        line_spacing = 2
        total_h = rx_h + line_spacing + tx_h

        # Вычисляем вертикальное положение блока
        if self.vertical_align == "top":
            block_y = content_y
        elif self.vertical_align == "bottom":
            block_y = content_y + content_h - total_h
        else:  # center
            block_y = content_y + (content_h - total_h) // 2

        # RX строка
        if self.horizontal_align == "left":
            rx_x = content_x
        elif self.horizontal_align == "right":
            rx_x = content_x + content_w - rx_w
        else:  # center
            rx_x = content_x + (content_w - rx_w) // 2

        rx_y = block_y
        draw.text((rx_x, rx_y), rx_text, fill=self.rx_color, font=font_obj)

        # TX строка
        if self.horizontal_align == "left":
            tx_x = content_x
        elif self.horizontal_align == "right":
            tx_x = content_x + content_w - tx_w
        else:  # center
            tx_x = content_x + (content_w - tx_w) // 2

        tx_y = block_y + rx_h + line_spacing
        draw.text((tx_x, tx_y), tx_text, fill=self.tx_color, font=font_obj)

    def _render_bar_horizontal(self, image: Image.Image) -> None:
        """Рендерит две горизонтальные полосы (RX сверху, TX снизу)."""
        draw = ImageDraw.Draw(image)

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        # Делим высоту на два бара
        available_h = content_h - self.bar_margin
        bar_h = available_h // 2

        if bar_h <= 0:
            return

        # RX бар (верхний)
        rx_y = content_y
        rx_pct = self._get_speed_percentage(self._current_rx_speed)

        if self.bar_border:
            draw.rectangle(
                [content_x, rx_y, content_x + content_w - 1, rx_y + bar_h - 1],
                outline=self.rx_color,
                fill=None
            )
            fill_w = int((content_w - 2) * (rx_pct / 100.0))
            if fill_w > 0:
                draw.rectangle(
                    [content_x + 1, rx_y + 1, content_x + fill_w, rx_y + bar_h - 2],
                    fill=self.rx_color
                )
        else:
            fill_w = int(content_w * (rx_pct / 100.0))
            if fill_w > 0:
                draw.rectangle(
                    [content_x, rx_y, content_x + fill_w - 1, rx_y + bar_h - 1],
                    fill=self.rx_color
                )

        # TX бар (нижний)
        tx_y = rx_y + bar_h + self.bar_margin
        tx_pct = self._get_speed_percentage(self._current_tx_speed)

        if self.bar_border:
            draw.rectangle(
                [content_x, tx_y, content_x + content_w - 1, tx_y + bar_h - 1],
                outline=self.tx_color,
                fill=None
            )
            fill_w = int((content_w - 2) * (tx_pct / 100.0))
            if fill_w > 0:
                draw.rectangle(
                    [content_x + 1, tx_y + 1, content_x + fill_w, tx_y + bar_h - 2],
                    fill=self.tx_color
                )
        else:
            fill_w = int(content_w * (tx_pct / 100.0))
            if fill_w > 0:
                draw.rectangle(
                    [content_x, tx_y, content_x + fill_w - 1, tx_y + bar_h - 1],
                    fill=self.tx_color
                )

    def _render_bar_vertical(self, image: Image.Image) -> None:
        """Рендерит два вертикальных столбца (RX слева, TX справа)."""
        draw = ImageDraw.Draw(image)

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        # Делим ширину на два бара
        available_w = content_w - self.bar_margin
        bar_w = available_w // 2

        if bar_w <= 0:
            return

        # RX бар (левый)
        rx_x = content_x
        rx_pct = self._get_speed_percentage(self._current_rx_speed)
        fill_h = int(content_h * (rx_pct / 100.0))
        fill_y = content_y + content_h - fill_h

        if self.bar_border:
            draw.rectangle(
                [rx_x, content_y, rx_x + bar_w - 1, content_y + content_h - 1],
                outline=self.rx_color,
                fill=None
            )
            if fill_h > 2:
                draw.rectangle(
                    [rx_x + 1, max(fill_y, content_y + 1), rx_x + bar_w - 2, content_y + content_h - 2],
                    fill=self.rx_color
                )
        else:
            if fill_h > 0:
                draw.rectangle(
                    [rx_x, fill_y, rx_x + bar_w - 1, content_y + content_h - 1],
                    fill=self.rx_color
                )

        # TX бар (правый)
        tx_x = rx_x + bar_w + self.bar_margin
        tx_pct = self._get_speed_percentage(self._current_tx_speed)
        fill_h = int(content_h * (tx_pct / 100.0))
        fill_y = content_y + content_h - fill_h

        if self.bar_border:
            draw.rectangle(
                [tx_x, content_y, tx_x + bar_w - 1, content_y + content_h - 1],
                outline=self.tx_color,
                fill=None
            )
            if fill_h > 2:
                draw.rectangle(
                    [tx_x + 1, max(fill_y, content_y + 1), tx_x + bar_w - 2, content_y + content_h - 2],
                    fill=self.tx_color
                )
        else:
            if fill_h > 0:
                draw.rectangle(
                    [tx_x, fill_y, tx_x + bar_w - 1, content_y + content_h - 1],
                    fill=self.tx_color
                )

    def _render_graph(self, image: Image.Image) -> None:
        """Рендерит два наложенных графика (RX и TX с разными цветами)."""
        if len(self._rx_history) < 2 or len(self._tx_history) < 2:
            # Недостаточно данных для графика
            logger.debug(f"Not enough history for graph: rx={len(self._rx_history)}, tx={len(self._tx_history)}, need 2+")
            return

        logger.debug(f"Rendering graph: {len(self._rx_history)} samples, "
                    f"RX range {min(self._rx_history)/1024:.1f}-{max(self._rx_history)/1024:.1f}KB/s, "
                    f"TX range {min(self._tx_history)/1024:.1f}-{max(self._tx_history)/1024:.1f}KB/s")

        draw = ImageDraw.Draw(image)

        # Вычисляем доступное пространство
        content_x = self.padding
        content_y = self.padding
        content_w = image.width - self.padding * 2
        content_h = image.height - self.padding * 2

        # RX график (первым, чтобы быть под TX)
        rx_points = []
        for i, speed in enumerate(self._rx_history):
            x = content_x + int((i / (len(self._rx_history) - 1)) * content_w)
            pct = self._get_speed_percentage(speed)
            y = content_y + content_h - int((pct / 100.0) * content_h)
            rx_points.append((x, y))

        # Рисуем RX линию
        if len(rx_points) >= 2:
            logger.debug(f"Drawing RX line with {len(rx_points)} points, first={(rx_points[0])}, last={(rx_points[-1])}")
            draw.line(rx_points, fill=self.rx_color, width=1)
        else:
            logger.debug(f"Not enough RX points: {len(rx_points)}")

        # Заполнение под RX графиком (полупрозрачное)
        if len(rx_points) >= 2:
            fill_points = rx_points.copy()
            fill_points.append((rx_points[-1][0], content_y + content_h))
            fill_points.append((rx_points[0][0], content_y + content_h))
            draw.polygon(fill_points, fill=self.rx_color // 3, outline=None)

        # TX график (поверх)
        tx_points = []
        for i, speed in enumerate(self._tx_history):
            x = content_x + int((i / (len(self._tx_history) - 1)) * content_w)
            pct = self._get_speed_percentage(speed)
            y = content_y + content_h - int((pct / 100.0) * content_h)
            tx_points.append((x, y))

        # Рисуем TX линию
        if len(tx_points) >= 2:
            draw.line(tx_points, fill=self.tx_color, width=1)

        # Заполнение под TX графиком (полупрозрачное)
        if len(tx_points) >= 2:
            fill_points = tx_points.copy()
            fill_points.append((tx_points[-1][0], content_y + content_h))
            fill_points.append((tx_points[0][0], content_y + content_h))
            draw.polygon(fill_points, fill=self.tx_color // 3, outline=None)

    def get_update_interval(self) -> float:
        """Возвращает интервал обновления."""
        return self.update_interval_sec
