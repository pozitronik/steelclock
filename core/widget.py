"""
Базовый класс для виджетов OLED дисплея.
Определяет интерфейс который должны реализовать все виджеты.
"""

from abc import ABC, abstractmethod
from typing import Tuple
from PIL import Image


class Widget(ABC):
    """
    Абстрактный базовый класс для виджетов.

    Каждый виджет отвечает за:
    - Сбор своих данных (update)
    - Рендеринг в bitmap (render)
    - Определение размера и частоты обновления
    """

    def __init__(self, name: str):
        """
        Инициализирует виджет.

        Args:
            name: Имя виджета для логирования и отладки
        """
        self.name = name
        self._width = 128
        self._height = 40

    @abstractmethod
    def update(self) -> None:
        """
        Обновляет данные виджета.

        Этот метод вызывается периодически согласно get_update_interval().
        Должен получить актуальные данные (время, CPU usage, и т.д.)
        и сохранить их во внутреннее состояние виджета.

        Raises:
            Exception: При ошибке получения данных
        """
        pass

    @abstractmethod
    def render(self) -> Image.Image:
        """
        Рендерит содержимое виджета в PIL Image.

        Возвращает изображение размером get_preferred_size().
        Изображение должно быть в grayscale режиме ('L').

        Returns:
            Image.Image: Отрендеренное изображение виджета

        Raises:
            Exception: При ошибке рендеринга
        """
        pass

    @abstractmethod
    def get_update_interval(self) -> float:
        """
        Возвращает интервал обновления данных в секундах.

        Returns:
            float: Интервал в секундах (например, 1.0 для ежесекундного обновления)
        """
        pass

    def get_preferred_size(self) -> Tuple[int, int]:
        """
        Возвращает предпочтительный размер виджета.

        Returns:
            Tuple[int, int]: (width, height) в пикселях
        """
        return (self._width, self._height)

    def set_size(self, width: int, height: int) -> None:
        """
        Устанавливает размер виджета.

        Args:
            width: Ширина в пикселях
            height: Высота в пикселях
        """
        self._width = width
        self._height = height

    def __repr__(self) -> str:
        """Строковое представление виджета"""
        return f"{self.__class__.__name__}(name='{self.name}')"
