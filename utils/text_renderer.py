"""
Утилиты для рендеринга текста с поддержкой шрифтов и выравнивания.

Общий модуль для всех виджетов с текстовым режимом отображения.
"""

import logging
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw

from utils.bitmap import Color, load_font, to_pil_color

logger = logging.getLogger(__name__)


def render_single_line_text(
    image: Image.Image,
    text: str,
    font: Optional[str] = None,
    font_size: int = 10,
    color: int = 255,
    horizontal_align: str = "center",
    vertical_align: str = "center",
    padding: int = 0
) -> None:
    """
    Рендерит одну строку текста с заданным выравниванием.

    Args:
        image: PIL Image для рисования
        text: Текст для отображения
        font: Имя шрифта или путь к файлу (None = default)
        font_size: Размер шрифта
        color: Цвет текста (0-255)
        horizontal_align: Горизонтальное выравнивание ("left", "center", "right")
        vertical_align: Вертикальное выравнивание ("top", "center", "bottom")
        padding: Отступ от краёв в пикселях
    """
    draw = ImageDraw.Draw(image)
    font_obj = load_font(font, font_size)

    # Вычисляем доступное пространство
    content_x = padding
    content_y = padding
    content_w = image.width - padding * 2
    content_h = image.height - padding * 2

    # Получаем размер текста
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Вычисляем X координату
    if horizontal_align == "left":
        x = content_x
    elif horizontal_align == "right":
        x = content_x + content_w - text_w
    else:  # center
        x = content_x + (content_w - text_w) // 2

    # Вычисляем Y координату
    if vertical_align == "top":
        y = content_y
    elif vertical_align == "bottom":
        y = content_y + content_h - text_h
    else:  # center
        y = content_y + (content_h - text_h) // 2

    # Текст всегда непрозрачный (полная видимость)
    text_color: Color = (color, 255) if image.mode == 'LA' else color
    draw.text((x, y), text, fill=to_pil_color(text_color), font=font_obj)


def render_multi_line_text(
    image: Image.Image,
    lines: List[Tuple[str, int]],
    font: Optional[str] = None,
    font_size: int = 10,
    horizontal_align: str = "center",
    vertical_align: str = "center",
    padding: int = 0,
    line_spacing: int = 2
) -> None:
    """
    Рендерит несколько строк текста как единый блок с заданным выравниванием.

    Блок из N строк выравнивается как единое целое (block-based alignment).
    Каждая строка может иметь свой цвет.

    Args:
        image: PIL Image для рисования
        lines: Список кортежей (текст, цвет) для каждой строки
        font: Имя шрифта или путь к файлу (None = default)
        font_size: Размер шрифта
        horizontal_align: Горизонтальное выравнивание ("left", "center", "right")
        vertical_align: Вертикальное выравнивание блока ("top", "center", "bottom")
        padding: Отступ от краёв в пикселях
        line_spacing: Промежуток между строками в пикселях
    """
    if not lines:
        return

    draw = ImageDraw.Draw(image)
    font_obj = load_font(font, font_size)

    # Вычисляем доступное пространство
    content_x = padding
    content_y = padding
    content_w = image.width - padding * 2
    content_h = image.height - padding * 2

    # Вычисляем размеры каждой строки
    line_metrics = []
    max_width = 0
    total_height = 0

    for i, (text, _) in enumerate(lines):
        bbox = draw.textbbox((0, 0), text, font=font_obj)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        line_metrics.append((width, height))
        max_width = max(max_width, width)
        total_height += height
        if i < len(lines) - 1:
            total_height += line_spacing

    # Вычисляем вертикальное положение блока
    if vertical_align == "top":
        block_y = content_y
    elif vertical_align == "bottom":
        block_y = content_y + content_h - total_height
    else:  # center
        block_y = content_y + (content_h - total_height) // 2

    # Рендерим каждую строку
    current_y = block_y
    for (text, color), (width, height) in zip(lines, line_metrics):
        # Вычисляем горизонтальное положение строки
        if horizontal_align == "left":
            x = content_x
        elif horizontal_align == "right":
            x = content_x + content_w - width
        else:  # center
            x = content_x + (content_w - width) // 2

        # Текст всегда непрозрачный (полная видимость)
        text_color: Color = (color, 255) if image.mode == 'LA' else color
        draw.text((x, current_y), text, fill=to_pil_color(text_color), font=font_obj)
        current_y += height + line_spacing


def render_grid_text(
    image: Image.Image,
    values: List[float],
    font: Optional[str] = None,
    font_size: int = 10,
    color: int = 255,
    padding: int = 0,
    decimal_places: int = 0
) -> None:
    """
    Рендерит сетку чисел (для per-core режима CPU и подобных виджетов).

    Автоматически определяет оптимальное количество строк и столбцов.

    Args:
        image: PIL Image для рисования
        values: Список значений для отображения
        font: Имя шрифта или путь к файлу (None = default)
        font_size: Размер шрифта
        color: Цвет текста (0-255)
        padding: Отступ от краёв в пикселях
        decimal_places: Количество знаков после запятой (0 = целое число)
    """
    if not values:
        return

    draw = ImageDraw.Draw(image)
    font_obj = load_font(font, font_size)

    # Вычисляем доступное пространство
    content_x = padding
    content_y = padding
    content_w = image.width - padding * 2
    content_h = image.height - padding * 2

    # Определяем количество строк и столбцов для оптимального размещения
    count = len(values)
    cols = int((count ** 0.5) + 0.5)
    rows = (count + cols - 1) // cols

    cell_w = content_w // cols
    cell_h = content_h // rows

    # Рендерим каждое значение
    for i, value in enumerate(values):
        col = i % cols
        row = i // cols

        # Форматируем текст
        if decimal_places == 0:
            text = f"{value:.0f}"
        else:
            text = f"{value:.{decimal_places}f}"

        cell_x = content_x + col * cell_w
        cell_y = content_y + row * cell_h

        # Центрируем текст в ячейке
        bbox = draw.textbbox((0, 0), text, font=font_obj)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = cell_x + (cell_w - text_w) // 2
        y = cell_y + (cell_h - text_h) // 2

        # Текст всегда непрозрачный (полная видимость)
        text_color: Color = (color, 255) if image.mode == 'LA' else color
        draw.text((x, y), text, fill=to_pil_color(text_color), font=font_obj)


def measure_text_size(
    text: str,
    font: Optional[str] = None,
    font_size: int = 10
) -> Tuple[int, int]:
    """
    Вычисляет размер текста без рендеринга.

    Args:
        text: Текст для измерения
        font: Имя шрифта или путь к файлу (None = default)
        font_size: Размер шрифта

    Returns:
        Tuple[int, int]: (ширина, высота) текста в пикселях
    """
    from PIL import Image, ImageDraw

    # Создаём временное изображение для измерения
    temp_img = Image.new('L', (1, 1))
    draw = ImageDraw.Draw(temp_img)
    font_obj = load_font(font, font_size)

    bbox = draw.textbbox((0, 0), text, font=font_obj)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]

    return (width, height)
