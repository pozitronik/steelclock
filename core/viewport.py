"""
Viewport - управление "окном" просмотра на виртуальном канвасе.
Реализует scrolling и zooming.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Viewport:
    """
    Описывает видимую область (окно просмотра) на виртуальном канвасе.

    Attributes:
        width: Ширина viewport в пикселях (физический размер дисплея, обычно 128)
        height: Высота viewport в пикселях (физический размер дисплея, обычно 40)
        offset_x: X смещение viewport на виртуальном канвасе (scrolling)
        offset_y: Y смещение viewport на виртуальном канвасе (scrolling)
        zoom: Коэффициент масштабирования (1.0 = 100%, 2.0 = 200%, 0.5 = 50%)
    """
    width: int = 128
    height: int = 40
    offset_x: int = 0
    offset_y: int = 0
    zoom: float = 1.0

    def scroll_to(self, x: int, y: int) -> None:
        """
        Перемещает viewport в указанную позицию на виртуальном канвасе.

        Args:
            x: X координата левого верхнего угла viewport
            y: Y координата левого верхнего угла viewport
        """
        self.offset_x = x
        self.offset_y = y

    def scroll_by(self, dx: int, dy: int) -> None:
        """
        Смещает viewport на указанное количество пикселей.

        Args:
            dx: Смещение по X (положительное = вправо)
            dy: Смещение по Y (положительное = вниз)
        """
        self.offset_x += dx
        self.offset_y += dy

    def center_on(self, x: int, y: int) -> None:
        """
        Центрирует viewport на указанной точке виртуального канваса.

        Args:
            x: X координата точки центрирования
            y: Y координата точки центрирования
        """
        self.offset_x = x - self.width // 2
        self.offset_y = y - self.height // 2

    def set_zoom(self, zoom: float) -> None:
        """
        Устанавливает коэффициент масштабирования.

        Args:
            zoom: Коэффициент масштабирования (1.0 = 100%, 2.0 = 200%, etc.)
                 Значение < 0.1 будет ограничено до 0.1
                 Значение > 10.0 будет ограничено до 10.0
        """
        # Ограничиваем zoom разумными пределами
        self.zoom = max(0.1, min(10.0, zoom))

    def zoom_in(self, step: float = 0.1) -> None:
        """
        Увеличивает масштаб.

        Args:
            step: Шаг увеличения (по умолчанию 0.1 = +10%)
        """
        self.set_zoom(self.zoom + step)

    def zoom_out(self, step: float = 0.1) -> None:
        """
        Уменьшает масштаб.

        Args:
            step: Шаг уменьшения (по умолчанию 0.1 = -10%)
        """
        self.set_zoom(self.zoom - step)

    def reset(self) -> None:
        """Сбрасывает viewport в начальное положение (0, 0) с zoom 1.0"""
        self.offset_x = 0
        self.offset_y = 0
        self.zoom = 1.0

    def get_visible_region(self) -> Tuple[int, int, int, int]:
        """
        Возвращает координаты видимой области на виртуальном канвасе.

        Returns:
            Tuple[int, int, int, int]: (left, top, right, bottom)
        """
        return (
            self.offset_x,
            self.offset_y,
            self.offset_x + self.width,
            self.offset_y + self.height
        )

    def constrain_to_canvas(self, canvas_width: int, canvas_height: int) -> None:
        """
        Ограничивает viewport границами виртуального канваса.
        Полезно для предотвращения прокрутки за пределы содержимого.

        Args:
            canvas_width: Ширина виртуального канваса
            canvas_height: Высота виртуального канваса
        """
        # Ограничиваем offset чтобы viewport не выходил за границы
        max_offset_x = max(0, canvas_width - self.width)
        max_offset_y = max(0, canvas_height - self.height)

        self.offset_x = max(0, min(self.offset_x, max_offset_x))
        self.offset_y = max(0, min(self.offset_y, max_offset_y))

    def is_point_visible(self, x: int, y: int) -> bool:
        """
        Проверяет видна ли точка в текущем viewport.

        Args:
            x: X координата на виртуальном канвасе
            y: Y координата на виртуальном канвасе

        Returns:
            bool: True если точка видна
        """
        left, top, right, bottom = self.get_visible_region()
        return left <= x < right and top <= y < bottom

    def is_rect_visible(self, x: int, y: int, w: int, h: int) -> bool:
        """
        Проверяет пересекается ли прямоугольник с viewport.

        Args:
            x: X координата левого верхнего угла прямоугольника
            y: Y координата левого верхнего угла прямоугольника
            w: Ширина прямоугольника
            h: Высота прямоугольника

        Returns:
            bool: True если прямоугольник хотя бы частично виден
        """
        left, top, right, bottom = self.get_visible_region()

        # Проверяем пересечение прямоугольников
        return not (x + w <= left or x >= right or y + h <= top or y >= bottom)

    def __repr__(self) -> str:
        return (f"Viewport(size={self.width}x{self.height}, "
                f"offset=({self.offset_x},{self.offset_y}), "
                f"zoom={self.zoom:.2f})")
