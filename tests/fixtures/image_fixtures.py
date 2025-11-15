"""
Фикстуры с тестовыми изображениями для тестов виджетов и bitmap utilities.

Содержит:
- Пустые изображения различных размеров
- Изображения с контентом (text, patterns)
- Изображения разных цветовых режимов (L, LA, RGB, RGBA)
"""

import pytest
from PIL import Image, ImageDraw


@pytest.fixture
def image_1x1():
    """Минимальное изображение 1x1."""
    return Image.new('L', (1, 1), color=0)


@pytest.fixture
def image_128x40():
    """Стандартное изображение для OLED дисплея."""
    return Image.new('L', (128, 40), color=0)


@pytest.fixture
def image_256x80():
    """Изображение удвоенного размера (для viewport тестов)."""
    return Image.new('L', (256, 80), color=0)


@pytest.fixture
def image_with_text():
    """Изображение 128x40 с текстом 'TEST'."""
    img = Image.new('L', (128, 40), color=0)
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "TEST", fill=255)
    return img


@pytest.fixture
def image_with_alpha():
    """Изображение с альфа-каналом (LA mode)."""
    return Image.new('LA', (128, 40), color=(128, 200))


@pytest.fixture
def image_rgb():
    """Цветное RGB изображение."""
    return Image.new('RGB', (128, 40), color=(255, 128, 0))


@pytest.fixture
def image_rgba():
    """Цветное RGBA изображение с прозрачностью."""
    return Image.new('RGBA', (128, 40), color=(255, 128, 0, 200))


@pytest.fixture
def image_all_black():
    """Полностью чёрное изображение."""
    return Image.new('L', (128, 40), color=0)


@pytest.fixture
def image_all_white():
    """Полностью белое изображение."""
    return Image.new('L', (128, 40), color=255)


@pytest.fixture
def image_gradient():
    """Изображение с горизонтальным градиентом от чёрного к белому."""
    img = Image.new('L', (128, 40))
    pixels = img.load()
    for x in range(128):
        gray_value = int(x / 127 * 255)
        for y in range(40):
            pixels[x, y] = gray_value
    return img


@pytest.fixture
def image_checkerboard():
    """Изображение с шахматным паттерном (8x8 клетки)."""
    img = Image.new('L', (128, 40))
    pixels = img.load()
    for x in range(128):
        for y in range(40):
            # Шахматная доска 8x8 пикселей
            if ((x // 8) + (y // 8)) % 2 == 0:
                pixels[x, y] = 255
            else:
                pixels[x, y] = 0
    return img


@pytest.fixture
def image_with_rect():
    """Изображение с белым прямоугольником в центре."""
    img = Image.new('L', (128, 40), color=0)
    draw = ImageDraw.Draw(img)
    draw.rectangle([32, 10, 96, 30], fill=255)
    return img


@pytest.fixture
def image_with_border():
    """Изображение с рамкой."""
    img = Image.new('L', (128, 40), color=0)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 127, 39], outline=255, fill=None)
    return img
