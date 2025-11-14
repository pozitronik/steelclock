"""
Определения типов для конфигурации SteelClock.
TypedDict схемы соответствуют JSON Schema из configs/config.schema.json
"""

from typing import List, TypedDict


class PositionConfig(TypedDict, total=False):
    """Конфигурация позиции виджета"""
    x: int
    y: int
    w: int
    h: int
    z_order: int


class StyleConfig(TypedDict, total=False):
    """Конфигурация стиля виджета"""
    background_color: int
    background_opacity: int
    border: bool
    border_color: int


class DisplayConfig(TypedDict, total=False):
    """Конфигурация дисплея"""
    width: int
    height: int
    background_color: int


class LayoutConfig(TypedDict, total=False):
    """Конфигурация layout (виртуальный канвас)"""
    type: str  # "basic" или другие режимы
    virtual_width: int
    virtual_height: int


class WidgetProperties(TypedDict, total=False):
    """Базовые свойства виджета (общие для всех типов)"""
    update_interval: float
    font: str
    font_size: int
    horizontal_align: str
    vertical_align: str
    padding: int

    # Clock специфичные
    format: str

    # CPU/Memory/Network/Disk специфичные
    display_mode: str
    fill_color: int
    bar_border: bool
    bar_margin: int
    history_length: int

    # CPU специфичные
    per_core: bool
    max_cores: int

    # Memory специфичные
    # (нет дополнительных)

    # Network специфичные
    interface: str
    dynamic_scaling: bool
    max_speed_mbps: float
    speed_unit: str
    rx_color: int
    tx_color: int

    # Disk специфичные
    disk_name: str
    read_color: int
    write_color: int

    # Keyboard специфичные
    spacing: int
    caps_lock_on: str
    caps_lock_off: str
    num_lock_on: str
    num_lock_off: str
    scroll_lock_on: str
    scroll_lock_off: str
    indicator_color_on: int
    indicator_color_off: int


class WidgetConfig(TypedDict, total=False):
    """Конфигурация виджета"""
    type: str
    id: str
    enabled: bool
    position: PositionConfig
    style: StyleConfig
    properties: WidgetProperties


class SteelClockConfig(TypedDict, total=False):
    """Главная конфигурация приложения"""
    game_name: str
    game_display_name: str
    display: DisplayConfig
    layout: LayoutConfig
    widgets: List[WidgetConfig]
    refresh_rate_ms: int


class APIResponse(TypedDict, total=False):
    """Типовой ответ от GameSense API"""
    # API возвращает различные структуры, но обычно это простые словари
    # Оставляем гибким через total=False
    error: str
    message: str
    # Другие поля зависят от endpoint
