"""
Утилиты для работы с монохромными bitmap для OLED дисплея.
Конвертация PIL Image в формат GameSense API.
"""

from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont


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


def create_blank_image(width: int = 128, height: int = 40, color: int = 0) -> Image.Image:
    """
    Создаёт пустое монохромное изображение.

    Args:
        width: Ширина в пикселях
        height: Высота в пикселях
        color: Цвет (0=чёрный, 255=белый)

    Returns:
        Image.Image: Пустое изображение в режиме 'L' (grayscale)
    """
    # Используем 'L' (grayscale) для удобства рисования, потом конвертируем в '1'
    return Image.new('L', (width, height), color=color)


def draw_text(
    image: Image.Image,
    text: str,
    position: Tuple[int, int] = (0, 0),
    font_size: int = 10,
    color: int = 255
) -> None:
    """
    Рисует текст на изображении.

    Args:
        image: PIL Image для рисования
        text: Текст для отображения
        position: Позиция (x, y) левого верхнего угла текста
        font_size: Размер шрифта
        color: Цвет текста (0=чёрный, 255=белый)
    """
    draw = ImageDraw.Draw(image)

    # Используем default PIL font (простой bitmap font)
    # Для более красивых шрифтов можно использовать ImageFont.truetype()
    try:
        # Попытка загрузить TrueType font (если доступен)
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except:
        # Fallback на дефолтный bitmap font
        font = ImageFont.load_default()

    draw.text(position, text, fill=color, font=font)


def draw_centered_text(
    image: Image.Image,
    text: str,
    font_size: int = 10,
    color: int = 255,
    vertical_offset: int = 0
) -> None:
    """
    Рисует текст по центру изображения.

    Args:
        image: PIL Image для рисования
        text: Текст для отображения
        font_size: Размер шрифта
        color: Цвет текста (0=чёрный, 255=белый)
        vertical_offset: Смещение по вертикали (положительное = вниз)
    """
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.truetype("DejaVuSans.ttf", font_size)
    except:
        font = ImageFont.load_default()

    # Получаем размер текста
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Вычисляем центральную позицию
    x = (image.width - text_width) // 2
    y = (image.height - text_height) // 2 + vertical_offset

    draw.text((x, y), text, fill=color, font=font)


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


def test_bitmap_conversion():
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
