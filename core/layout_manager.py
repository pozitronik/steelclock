"""
Layout Manager - управляет размещением виджетов на канвасе OLED дисплея.
Реализует функционал "window manager" для композиции нескольких виджетов.

Поддерживает:
- Базовое позиционирование виджетов
- Z-order для наложения виджетов
- Виртуальный канвас (может быть больше физического дисплея)
- Viewport (scrolling)
- Zoom
- Локальный scale для каждого виджета
"""

import logging
from typing import List, Optional
from dataclasses import dataclass
from PIL import Image

from .widget import Widget
from .viewport import Viewport
from utils.bitmap import create_blank_image

logger = logging.getLogger(__name__)


@dataclass
class WidgetLayout:
    """
    Описывает позицию и размер виджета на виртуальном канвасе.

    Attributes:
        widget: Экземпляр виджета
        x: X координата левого верхнего угла на виртуальном канвасе
        y: Y координата левого верхнего угла на виртуальном канвасе
        w: Ширина виджета
        h: Высота виджета
        z_order: Порядок наложения (больше = поверх других)
        visible: Видимость виджета
        scale: Локальный масштаб виджета (1.0 = нормальный, 2.0 = увеличен вдвое)
    """
    widget: Widget
    x: int
    y: int
    w: int
    h: int
    z_order: int = 0
    visible: bool = True
    scale: float = 1.0


class LayoutManager:
    """
    Управляет размещением и композицией виджетов на OLED дисплее.

    Поддерживает два режима работы:
    1. Базовый режим: виртуальный канвас = физический дисплей (128x40)
    2. Расширенный режим: виртуальный канвас больше дисплея + viewport/zoom

    Отличия расширенного режима:
    - Виртуальный канвас может быть больше физического дисплея
    - Viewport определяет какая часть виртуального канваса видна
    - Поддержка глобального zoom
    - Поддержка локального scale для каждого виджета
    """

    def __init__(
            self,
            width: int = 128,
            height: int = 40,
            virtual_width: Optional[int] = None,
            virtual_height: Optional[int] = None,
            background_color: int = 0
    ):
        """
        Инициализирует Layout Manager.

        Args:
            width: Физическая ширина дисплея (или ширина канваса в базовом режиме)
            height: Физическая высота дисплея (или высота канваса в базовом режиме)
            virtual_width: Ширина виртуального канваса (None = равна width, базовый режим)
            virtual_height: Высота виртуального канваса (None = равна height, базовый режим)
            background_color: Цвет фона канваса (0-255, 0=чёрный, 255=белый)
        """
        # Физический дисплей
        self.display_width = width
        self.display_height = height

        # Виртуальный канвас (может быть больше физического дисплея)
        self.virtual_width = virtual_width or width
        self.virtual_height = virtual_height or height

        # Цвет фона
        self.background_color = background_color

        # Определяем режим работы
        self.viewport_mode = (
                self.virtual_width != self.display_width or
                self.virtual_height != self.display_height
        )

        # Viewport - используется только в расширенном режиме
        if self.viewport_mode:
            self.viewport = Viewport(
                width=self.display_width,
                height=self.display_height,
                offset_x=0,
                offset_y=0,
                zoom=1.0
            )
        else:
            self.viewport = None

        self.layouts: List[WidgetLayout] = []

        if self.viewport_mode:
            logger.info(
                f"LayoutManager initialized (viewport mode): "
                f"display={self.display_width}x{self.display_height}, "
                f"virtual={self.virtual_width}x{self.virtual_height}"
            )
        else:
            logger.info(
                f"LayoutManager initialized (basic mode): "
                f"{self.display_width}x{self.display_height}"
            )

    # Для обратной совместимости
    @property
    def width(self) -> int:
        """Ширина канваса (в базовом режиме) или виртуального канваса"""
        return self.virtual_width

    @property
    def height(self) -> int:
        """Высота канваса (в базовом режиме) или виртуального канваса"""
        return self.virtual_height

    def add_widget(
            self,
            widget: Widget,
            x: int = 0,
            y: int = 0,
            w: int = None,
            h: int = None,
            z_order: int = 0,
            scale: float = 1.0
    ) -> None:
        """
        Добавляет виджет в layout на виртуальном канвасе.

        Args:
            widget: Виджет для добавления
            x: X координата на виртуальном канвасе
            y: Y координата на виртуальном канвасе
            w: Ширина (None = использовать preferred size)
            h: Высота (None = использовать preferred size)
            z_order: Порядок наложения (больше = поверх)
            scale: Локальный масштаб виджета (1.0 = нормальный, используется только в viewport режиме)
        """
        # Если размер не указан, используем preferred size виджета
        if w is None or h is None:
            pref_w, pref_h = widget.get_preferred_size()
            w = w or pref_w
            h = h or pref_h

        # Устанавливаем размер виджету
        widget.set_size(w, h)

        layout = WidgetLayout(
            widget=widget,
            x=x,
            y=y,
            w=w,
            h=h,
            z_order=z_order,
            visible=True,
            scale=scale if self.viewport_mode else 1.0
        )

        self.layouts.append(layout)

        # Сортируем по z_order для правильного порядка рендеринга
        self.layouts.sort(key=lambda l: l.z_order)

        if self.viewport_mode and scale != 1.0:
            logger.info(
                f"Widget added: {widget.name} at ({x},{y}) "
                f"size ({w}x{h}) scale={scale:.2f}"
            )
        else:
            logger.info(f"Widget added: {widget.name} at ({x},{y}) size ({w}x{h})")

    def remove_widget(self, widget: Widget) -> bool:
        """
        Удаляет виджет из layout.

        Args:
            widget: Виджет для удаления

        Returns:
            bool: True если виджет был найден и удалён
        """
        initial_count = len(self.layouts)
        self.layouts = [l for l in self.layouts if l.widget != widget]
        removed = len(self.layouts) < initial_count

        if removed:
            logger.info(f"Widget removed: {widget.name}")

        return removed

    def composite(self, apply_viewport: bool = True) -> Image.Image:
        """
        Композитирует все виджеты в финальное изображение.

        Args:
            apply_viewport: Если True и viewport_mode включен, применяет viewport (zoom + crop).
                          Если False или viewport_mode отключен, возвращает полный виртуальный канвас.

        Returns:
            Image.Image: Финальное изображение

        Raises:
            Exception: При ошибке рендеринга виджета
        """
        # Шаг 1: Создаём виртуальный канвас
        virtual_canvas = create_blank_image(
            self.virtual_width,
            self.virtual_height,
            color=self.background_color
        )

        # Шаг 2: Рендерим виджеты в порядке z_order (от меньшего к большему)
        for layout in self.layouts:
            if not layout.visible:
                continue

            # Оптимизация: пропускаем виджеты вне viewport (только в viewport режиме)
            if self.viewport_mode and apply_viewport and self.viewport:
                if not self.viewport.is_rect_visible(
                        layout.x, layout.y, layout.w, layout.h
                ):
                    continue

            try:
                # Рендерим виджет
                widget_img = layout.widget.render()

                # Применяем локальный scale виджета (только в viewport режиме)
                if self.viewport_mode and layout.scale != 1.0:
                    scaled_w = int(layout.w * layout.scale)
                    scaled_h = int(layout.h * layout.scale)
                    widget_img = widget_img.resize(
                        (scaled_w, scaled_h),
                        Image.LANCZOS
                    )
                elif widget_img.size != (layout.w, layout.h):
                    # Resize если размер не совпадает
                    widget_img = widget_img.resize(
                        (layout.w, layout.h),
                        Image.LANCZOS
                    )

                # Вставляем на виртуальный канвас с поддержкой альфа-канала
                # paste() автоматически обрабатывает clipping
                if widget_img.mode in ('LA', 'RGBA'):
                    # Изображение с альфа-каналом - используем альфа-композитинг
                    virtual_canvas.paste(widget_img, (layout.x, layout.y), widget_img)
                else:
                    # Обычное изображение без прозрачности
                    virtual_canvas.paste(widget_img, (layout.x, layout.y))

            except Exception as e:
                logger.error(f"Failed to render widget {layout.widget.name}: {e}")
                # Продолжаем рендерить остальные виджеты

        # Если viewport режим отключен или не применяем viewport, возвращаем полный канвас
        if not self.viewport_mode or not apply_viewport:
            return virtual_canvas

        # Шаг 3: Применяем viewport (zoom + crop)
        return self._apply_viewport(virtual_canvas)

    def _apply_viewport(self, virtual_canvas: Image.Image) -> Image.Image:
        """
        Применяет viewport к виртуальному канвасу (zoom + crop).

        Args:
            virtual_canvas: Полный виртуальный канвас

        Returns:
            Image.Image: Финальное изображение для дисплея (display_width x display_height)
        """
        if not self.viewport:
            return virtual_canvas

        # Шаг 1: Применяем zoom (если нужно)
        if self.viewport.zoom != 1.0:
            # Масштабируем весь виртуальный канвас
            zoomed_width = int(self.virtual_width * self.viewport.zoom)
            zoomed_height = int(self.virtual_height * self.viewport.zoom)

            virtual_canvas = virtual_canvas.resize(
                (zoomed_width, zoomed_height),
                Image.LANCZOS
            )
        else:
            zoomed_width = self.virtual_width
            zoomed_height = self.virtual_height

        # Шаг 2: Crop viewport region
        left = self.viewport.offset_x
        top = self.viewport.offset_y
        right = left + self.display_width
        bottom = top + self.display_height

        # Обработка границ: если viewport выходит за пределы канваса,
        # заполняем недостающие области чёрным
        if (left < 0 or top < 0 or
                right > zoomed_width or bottom > zoomed_height):

            # Создаём канвас размером с дисплей
            display_canvas = create_blank_image(
                self.display_width,
                self.display_height,
                color=self.background_color
            )

            # Вычисляем какая часть виртуального канваса видна
            src_left = max(0, left)
            src_top = max(0, top)
            src_right = min(zoomed_width, right)
            src_bottom = min(zoomed_height, bottom)

            # Вычисляем куда вставлять на дисплей
            dst_left = src_left - left
            dst_top = src_top - top

            # Crop видимую часть
            if src_right > src_left and src_bottom > src_top:
                cropped = virtual_canvas.crop((src_left, src_top, src_right, src_bottom))
                display_canvas.paste(cropped, (dst_left, dst_top))

            return display_canvas
        else:
            # Простой crop
            return virtual_canvas.crop((left, top, right, bottom))

    def set_virtual_size(self, width: int, height: int) -> None:
        """
        Изменяет размер виртуального канваса.

        Args:
            width: Новая ширина виртуального канваса
            height: Новая высота виртуального канваса
        """
        self.virtual_width = width
        self.virtual_height = height

        # Обновляем режим
        self.viewport_mode = (
                self.virtual_width != self.display_width or
                self.virtual_height != self.display_height
        )

        # Создаём viewport если переходим в viewport режим
        if self.viewport_mode and not self.viewport:
            self.viewport = Viewport(
                width=self.display_width,
                height=self.display_height,
                offset_x=0,
                offset_y=0,
                zoom=1.0
            )

        logger.info(f"Virtual canvas resized to {width}x{height}")

    def constrain_viewport(self) -> None:
        """Ограничивает viewport границами виртуального канваса (только в viewport режиме)"""
        if not self.viewport_mode or not self.viewport:
            return

        # С учётом zoom
        zoomed_width = int(self.virtual_width * self.viewport.zoom)
        zoomed_height = int(self.virtual_height * self.viewport.zoom)

        self.viewport.constrain_to_canvas(zoomed_width, zoomed_height)

    def get_widget_at(self, x: int, y: int) -> Optional[Widget]:
        """
        Возвращает верхний виджет на указанной позиции виртуального канваса.

        Args:
            x: X координата на виртуальном канвасе
            y: Y координата на виртуальном канвасе

        Returns:
            Widget: Виджет на этой позиции или None
        """
        # Ищем в обратном порядке z_order (сверху вниз)
        for layout in reversed(self.layouts):
            if not layout.visible:
                continue

            if (layout.x <= x < layout.x + layout.w and
                    layout.y <= y < layout.y + layout.h):
                return layout.widget

        return None

    def set_widget_visibility(self, widget: Widget, visible: bool) -> None:
        """
        Устанавливает видимость виджета.

        Args:
            widget: Виджет
            visible: True для отображения, False для скрытия
        """
        for layout in self.layouts:
            if layout.widget == widget:
                layout.visible = visible
                logger.debug(f"Widget {widget.name} visibility: {visible}")
                break

    def clear(self) -> None:
        """Удаляет все виджеты из layout"""
        self.layouts.clear()
        logger.info("Layout cleared")

    def __len__(self) -> int:
        """Возвращает количество виджетов в layout"""
        return len(self.layouts)
