"""
Layout Manager - управляет размещением виджетов на канвасе OLED дисплея.
Реализует функционал "window manager" для композиции нескольких виджетов.
"""

import logging
from typing import List, Tuple
from dataclasses import dataclass
from PIL import Image

from .widget import Widget
from utils.bitmap import create_blank_image

logger = logging.getLogger(__name__)


@dataclass
class WidgetLayout:
    """
    Описывает позицию и размер виджета на канвасе.

    Attributes:
        widget: Экземпляр виджета
        x: X координата левого верхнего угла
        y: Y координата левого верхнего угла
        w: Ширина виджета
        h: Высота виджета
        z_order: Порядок наложения (больше = поверх других)
        visible: Видимость виджета
    """
    widget: Widget
    x: int
    y: int
    w: int
    h: int
    z_order: int = 0
    visible: bool = True


class LayoutManager:
    """
    Управляет размещением и композицией виджетов на OLED дисплее.

    Реализует простой window manager который позиционирует виджеты
    на канвасе 128x40 и композитирует их в финальное изображение.
    """

    def __init__(self, width: int = 128, height: int = 40):
        """
        Инициализирует Layout Manager.

        Args:
            width: Ширина канваса в пикселях
            height: Высота канваса в пикселях
        """
        self.width = width
        self.height = height
        self.layouts: List[WidgetLayout] = []

        logger.info(f"LayoutManager initialized: {width}x{height}")

    def add_widget(
        self,
        widget: Widget,
        x: int = 0,
        y: int = 0,
        w: int = None,
        h: int = None,
        z_order: int = 0
    ) -> None:
        """
        Добавляет виджет в layout.

        Args:
            widget: Виджет для добавления
            x: X координата позиции
            y: Y координата позиции
            w: Ширина (None = использовать preferred size)
            h: Высота (None = использовать preferred size)
            z_order: Порядок наложения (больше = поверх)
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
            visible=True
        )

        self.layouts.append(layout)

        # Сортируем по z_order для правильного порядка рендеринга
        self.layouts.sort(key=lambda l: l.z_order)

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

    def composite(self) -> Image.Image:
        """
        Композитирует все виджеты в финальное изображение.

        Рендерит каждый видимый виджет и размещает его на канвасе
        согласно позиции и z-order.

        Returns:
            Image.Image: Финальное изображение размером (width, height)

        Raises:
            Exception: При ошибке рендеринга виджета
        """
        # Создаём чистый канвас (чёрный фон)
        canvas = create_blank_image(self.width, self.height, color=0)

        # Рендерим виджеты в порядке z_order (от меньшего к большему)
        for layout in self.layouts:
            if not layout.visible:
                continue

            try:
                # Запрашиваем рендеринг у виджета
                widget_img = layout.widget.render()

                # Убедимся что размер соответствует layout
                if widget_img.size != (layout.w, layout.h):
                    widget_img = widget_img.resize(
                        (layout.w, layout.h),
                        Image.LANCZOS
                    )

                # Вставляем на канвас на нужную позицию
                # paste() автоматически обрабатывает clipping
                canvas.paste(widget_img, (layout.x, layout.y))

            except Exception as e:
                logger.error(f"Failed to render widget {layout.widget.name}: {e}")
                # Продолжаем рендерить остальные виджеты

        return canvas

    def get_widget_at(self, x: int, y: int) -> Widget:
        """
        Возвращает верхний виджет на указанной позиции.

        Args:
            x: X координата
            y: Y координата

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
