"""
Утилиты для работы с монохромными bitmap для OLED дисплея.
Конвертация PIL Image в формат GameSense API.
"""

import os
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont


def resolve_font_path(font: Optional[str]) -> Optional[str]:
    """
    Преобразует имя шрифта или путь в полный путь к файлу шрифта.

    Args:
        font: Имя шрифта (например "Arial", "Consolas") или путь к файлу шрифта

    Returns:
        Optional[str]: Полный путь к файлу шрифта или None если не найден
    """
    if not font:
        return None

    # Если это уже путь к существующему файлу, возвращаем как есть
    if os.path.isfile(font):
        return font

    # Пробуем найти шрифт в системных директориях Windows
    windows_fonts_dir = Path("C:/Windows/Fonts")

    # Словарь распространённых названий шрифтов и их файлов
    font_mappings = {  # todo: implement runtime mappings
        "arial": "arial.ttf",
        "arial bold": "arialbd.ttf",
        "arial italic": "ariali.ttf",
        "consolas": "consola.ttf",
        "consolas bold": "consolab.ttf",
        "courier new": "cour.ttf",
        "courier new bold": "courbd.ttf",
        "comic sans": "comic.ttf",
        "comic sans ms": "comic.ttf",
        "georgia": "georgia.ttf",
        "impact": "impact.ttf",
        "lucida console": "lucon.ttf",
        "tahoma": "tahoma.ttf",
        "times new roman": "times.ttf",
        "times new roman bold": "timesbd.ttf",
        "trebuchet ms": "trebuc.ttf",
        "verdana": "verdana.ttf",
        "verdana bold": "verdanab.ttf",
        "dejavu sans": "DejaVuSans.ttf",
        "dejavu sans mono": "DejaVuSansMono.ttf",
    }

    # Нормализуем имя шрифта (lowercase, убираем лишние пробелы)
    font_normalized = font.lower().strip()

    # Проверяем есть ли в маппинге
    if font_normalized in font_mappings:
        font_file = windows_fonts_dir / font_mappings[font_normalized]
        if font_file.exists():
            return str(font_file)

    # Пробуем прямое совпадение: имя.ttf
    direct_path = windows_fonts_dir / f"{font}.ttf"
    if direct_path.exists():
        return str(direct_path)

    # Пробуем lowercase версию
    direct_path = windows_fonts_dir / f"{font_normalized}.ttf"
    if direct_path.exists():
        return str(direct_path)

    # Пробуем найти файл содержащий это имя (fuzzy match)
    if windows_fonts_dir.exists():
        for font_file in windows_fonts_dir.glob("*.ttf"):
            if font_normalized in font_file.stem.lower():
                return str(font_file)

    # Не найден
    return None


# fixme: strange defaults
def load_font(font: Optional[str] = None, size: int = 10) -> ImageFont.FreeTypeFont:
    """
    Загружает шрифт по имени или пути.

    Args:
        font: Имя шрифта или путь к файлу (None = default font)
        size: Размер шрифта

    Returns:
        ImageFont: Загруженный шрифт или default font
    """
    import logging
    logger = logging.getLogger(__name__)

    if font:
        font_path = resolve_font_path(font)
        if font_path:
            try:
                loaded = ImageFont.truetype(font_path, size)
                logger.debug(f"Loaded font: {font_path} at size {size}")
                return loaded
            except Exception as e:
                logger.warning(f"Failed to load font {font_path}: {e}, falling back to default")
        else:
            logger.warning(f"Font '{font}' not found, falling back to default")

    # Default fallback
    try:
        # Пробуем DejaVuSans как запасной вариант
        loaded = ImageFont.truetype("DejaVuSans.ttf", size)
        logger.debug(f"Loaded DejaVuSans at size {size}")
        return loaded
    except Exception:
        # Финальный fallback на встроенный bitmap font
        logger.warning("DejaVuSans not found, using PIL default bitmap font (size will be ignored)")
        return ImageFont.load_default()


def image_to_bytes(image: Image.Image, width: int = 128, height: int = 40) -> List[int]:
    """
    Конвертирует PIL Image в массив байтов для GameSense API.

    Формат:
    - Monochrome (1 bit per pixel)
    - MSB first (старший бит слева)
    - Row-major order (построчно слева-направо, сверху-вниз)
    - Размер: ceil(width * height / 8) байт

    Args:
        image: PIL Image (будет конвертирован в monochrome)
        width: Ширина в пикселях (по умолчанию 128)
        height: Высота в пикселях (по умолчанию 40)

    Returns:
        List[int]: Массив байтов (640 байт для 128x40)
    """
    # Конвертируем в monochrome (режим '1' = 1 bit per pixel)
    # Используем dithering для лучшего качества
    mono = image.convert('1', dither=Image.FLOYDSTEINBERG)

    # Убедимся что размер правильный
    if mono.size != (width, height):
        mono = mono.resize((width, height), Image.LANCZOS)

    # Получаем пиксели как bytes
    pixels = mono.tobytes()

    # PIL уже упаковывает биты в байты в режиме '1'
    # Формат: MSB first, row-major (именно то что нужно для GameSense)
    byte_array = list(pixels)

    expected_size = (width * height + 7) // 8  # ceil division
    if len(byte_array) != expected_size:
        raise ValueError(
            f"Unexpected bitmap size: got {len(byte_array)}, expected {expected_size}"
        )

    return byte_array


def create_blank_image(
        width: int = 128,
        height: int = 40,
        color: int = 0,
        opacity: int = 255
) -> Image.Image:
    """
    Создаёт пустое монохромное изображение.

    Args:
        width: Ширина в пикселях
        height: Высота в пикселях
        color: Цвет (0=чёрный, 255=белый)
        opacity: Прозрачность фона (0=полностью прозрачный, 255=непрозрачный)

    Returns:
        Image.Image: Пустое изображение в режиме 'L' (grayscale) или 'LA' (с альфа-каналом)
    """
    if opacity < 255:
        # Создаём изображение с альфа-каналом
        image = Image.new('LA', (width, height), color=(color, opacity))
        return image
    else:
        # Стандартное grayscale изображение без альфа-канала
        return Image.new('L', (width, height), color=color)


def draw_text(
        image: Image.Image,
        text: str,
        position: Tuple[int, int] = (0, 0),
        font_size: int = 10,
        color: int = 255,
        font: Optional[str] = None
) -> None:
    """
    Рисует текст на изображении.

    Args:
        image: PIL Image для рисования
        text: Текст для отображения
        position: Позиция (x, y) левого верхнего угла текста
        font_size: Размер шрифта
        color: Цвет текста (0=чёрный, 255=белый)
        font: Имя шрифта или путь к файлу (None = default)
    """
    draw = ImageDraw.Draw(image)
    font_obj = load_font(font, font_size)
    draw.text(position, text, fill=color, font=font_obj)


def draw_centered_text(
        image: Image.Image,
        text: str,
        font_size: int = 10,
        color: int = 255,
        vertical_offset: int = 0,
        font: Optional[str] = None
) -> None:
    """
    Рисует текст по центру изображения.

    Args:
        image: PIL Image для рисования
        text: Текст для отображения
        font_size: Размер шрифта
        color: Цвет текста (0=чёрный, 255=белый)
        vertical_offset: Смещение по вертикали (положительное = вниз)
        font: Имя шрифта или путь к файлу (None = default)
    """
    draw = ImageDraw.Draw(image)
    font_obj = load_font(font, font_size)

    # Получаем размер текста
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Вычисляем центральную позицию
    x = (image.width - text_width) // 2
    y = (image.height - text_height) // 2 + vertical_offset

    draw.text((x, y), text, fill=color, font=font_obj)


def draw_aligned_text(
        image: Image.Image,
        text: str,
        font_size: int = 10,
        color: int = 255,
        font: Optional[str] = None,
        horizontal_align: str = "center",
        vertical_align: str = "center",
        padding: int = 0
) -> None:
    """
    Рисует текст с заданным выравниванием.

    Args:
        image: PIL Image для рисования
        text: Текст для отображения
        font_size: Размер шрифта
        color: Цвет текста (0=чёрный, 255=белый)
        font: Имя шрифта или путь к файлу (None = default)
        horizontal_align: Горизонтальное выравнивание ("left", "center", "right")
        vertical_align: Вертикальное выравнивание ("top", "center", "bottom")
        padding: Отступ от краёв в пикселях
    """
    draw = ImageDraw.Draw(image)
    font_obj = load_font(font, font_size)

    # Получаем размер текста
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Вычисляем X координату
    if horizontal_align == "left":
        x = padding
    elif horizontal_align == "right":
        x = image.width - text_width - padding
    else:  # center
        x = (image.width - text_width) // 2

    # Вычисляем Y координату
    if vertical_align == "top":
        y = padding
    elif vertical_align == "bottom":
        y = image.height - text_height - padding
    else:  # center
        y = (image.height - text_height) // 2

    draw.text((x, y), text, fill=color, font=font_obj)


def draw_progress_bar(
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        height: int,
        percentage: float,
        border: bool = True
) -> None:
    """
    Рисует progress bar на изображении.

    Args:
        image: PIL Image для рисования
        x: X координата левого верхнего угла
        y: Y координата левого верхнего угла
        width: Ширина progress bar
        height: Высота progress bar
        percentage: Процент заполнения (0.0 - 1.0)
        border: Рисовать ли рамку
    """
    draw = ImageDraw.Draw(image)

    # Рамка
    if border:
        draw.rectangle([x, y, x + width - 1, y + height - 1], outline=255, fill=0)

    # Заполнение
    if percentage > 0:
        fill_width = int((width - 4) * min(percentage, 1.0))
        if fill_width > 0:
            draw.rectangle(
                [x + 2, y + 2, x + 2 + fill_width, y + height - 3],
                fill=255
            )


def test_bitmap_conversion() -> List[int]:
    """
    Тестовая функция для проверки конвертации bitmap.
    Создаёт простой паттерн и конвертирует в байты.
    """
    # Создаём тестовое изображение
    img = create_blank_image()
    draw_centered_text(img, "STEELCLOCK", font_size=12)

    # Конвертируем в байты
    byte_array = image_to_bytes(img)

    print(f"Bitmap converted: {len(byte_array)} bytes")
    print(f"First 10 bytes: {byte_array[:10]}")

    # Сохраняем для визуальной проверки
    img.save('/tmp/test_bitmap.png')
    print("Test bitmap saved to /tmp/test_bitmap.png")

    return byte_array


if __name__ == '__main__':
    # Запуск теста если модуль запущен напрямую
    test_bitmap_conversion()
