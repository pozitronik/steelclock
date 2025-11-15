"""
Unit tests для config_types - TypedDict определения для конфигурации.

Тестируемый модуль: core/config_types.py

Покрытие:
- PositionConfig
- StyleConfig
- DisplayConfig
- LayoutConfig
- WidgetProperties
- WidgetConfig
- SteelClockConfig
- APIResponse

Примечание: Это тесты TypedDict схем, проверяющие что они корректно
определены и могут быть использованы для валидации конфигураций.
"""

import pytest
from typing import get_type_hints

from core.config_types import (
    PositionConfig,
    StyleConfig,
    DisplayConfig,
    LayoutConfig,
    WidgetProperties,
    WidgetConfig,
    SteelClockConfig,
    APIResponse
)


# ===========================
# Тесты PositionConfig
# ===========================

def test_position_config_full():
    """Тест создания полной PositionConfig."""
    config: PositionConfig = {
        'x': 10,
        'y': 20,
        'w': 100,
        'h': 50,
        'z_order': 5
    }

    assert config['x'] == 10
    assert config['y'] == 20
    assert config['w'] == 100
    assert config['h'] == 50
    assert config['z_order'] == 5


def test_position_config_partial():
    """Тест создания частичной PositionConfig (total=False)."""
    config: PositionConfig = {
        'x': 10,
        'y': 20
    }

    assert config['x'] == 10
    assert config['y'] == 20
    assert 'w' not in config


def test_position_config_empty():
    """Edge case: пустая PositionConfig допустима (total=False)."""
    config: PositionConfig = {}

    assert len(config) == 0


# ===========================
# Тесты StyleConfig
# ===========================

def test_style_config_full():
    """Тест создания полной StyleConfig."""
    config: StyleConfig = {
        'background_color': 0,
        'background_opacity': 255,
        'border': True,
        'border_color': 255
    }

    assert config['background_color'] == 0
    assert config['border'] is True


def test_style_config_partial():
    """Тест создания частичной StyleConfig."""
    config: StyleConfig = {
        'border': False
    }

    assert config['border'] is False
    assert 'background_color' not in config


# ===========================
# Тесты DisplayConfig
# ===========================

def test_display_config_full():
    """Тест создания полной DisplayConfig."""
    config: DisplayConfig = {
        'width': 128,
        'height': 40,
        'background_color': 0
    }

    assert config['width'] == 128
    assert config['height'] == 40


def test_display_config_partial():
    """Тест создания частичной DisplayConfig."""
    config: DisplayConfig = {
        'width': 256
    }

    assert config['width'] == 256


# ===========================
# Тесты LayoutConfig
# ===========================

def test_layout_config_basic_type():
    """Тест создания LayoutConfig с basic type."""
    config: LayoutConfig = {
        'type': 'basic'
    }

    assert config['type'] == 'basic'


def test_layout_config_with_virtual_canvas():
    """Тест создания LayoutConfig с виртуальным канвасом."""
    config: LayoutConfig = {
        'type': 'viewport',
        'virtual_width': 256,
        'virtual_height': 80
    }

    assert config['virtual_width'] == 256
    assert config['virtual_height'] == 80


# ===========================
# Тесты WidgetProperties
# ===========================

def test_widget_properties_common():
    """Тест создания WidgetProperties с общими свойствами."""
    props: WidgetProperties = {
        'update_interval': 1.0,
        'font': 'Arial',
        'font_size': 12,
        'horizontal_align': 'center',
        'vertical_align': 'center',
        'padding': 5
    }

    assert props['update_interval'] == 1.0
    assert props['font'] == 'Arial'


def test_widget_properties_clock_specific():
    """Тест WidgetProperties с clock-специфичными свойствами."""
    props: WidgetProperties = {
        'format': '%H:%M:%S',
        'font_size': 14
    }

    assert props['format'] == '%H:%M:%S'


def test_widget_properties_cpu_specific():
    """Тест WidgetProperties с CPU-специфичными свойствами."""
    props: WidgetProperties = {
        'display_mode': 'bar_horizontal',
        'per_core': True,
        'max_cores': 8,
        'fill_color': 255
    }

    assert props['per_core'] is True
    assert props['max_cores'] == 8


def test_widget_properties_network_specific():
    """Тест WidgetProperties с network-специфичными свойствами."""
    props: WidgetProperties = {
        'interface': 'eth0',
        'dynamic_scaling': True,
        'max_speed_mbps': 1000.0,
        'speed_unit': 'mbps',
        'rx_color': 200,
        'tx_color': 100
    }

    assert props['interface'] == 'eth0'
    assert props['dynamic_scaling'] is True
    assert props['rx_color'] == 200


def test_widget_properties_disk_specific():
    """Тест WidgetProperties с disk-специфичными свойствами."""
    props: WidgetProperties = {
        'disk_name': 'sda',
        'read_color': 255,
        'write_color': 128
    }

    assert props['disk_name'] == 'sda'


def test_widget_properties_keyboard_specific():
    """Тест WidgetProperties с keyboard-специфичными свойствами."""
    props: WidgetProperties = {
        'spacing': 10,
        'caps_lock_on': 'C',
        'caps_lock_off': 'c',
        'num_lock_on': 'N',
        'num_lock_off': 'n',
        'scroll_lock_on': 'S',
        'scroll_lock_off': 's',
        'indicator_color_on': 255,
        'indicator_color_off': 50
    }

    assert props['caps_lock_on'] == 'C'
    assert props['spacing'] == 10


# ===========================
# Тесты WidgetConfig
# ===========================

def test_widget_config_full():
    """Тест создания полной WidgetConfig."""
    config: WidgetConfig = {
        'type': 'clock',
        'id': 'main_clock',
        'enabled': True,
        'position': {
            'x': 0,
            'y': 0,
            'w': 128,
            'h': 20
        },
        'style': {
            'background_color': 0,
            'border': False
        },
        'properties': {
            'format': '%H:%M',
            'font_size': 14
        }
    }

    assert config['type'] == 'clock'
    assert config['id'] == 'main_clock'
    assert config['enabled'] is True
    assert config['position']['x'] == 0
    assert config['style']['border'] is False
    assert config['properties']['format'] == '%H:%M'


def test_widget_config_minimal():
    """Тест создания минимальной WidgetConfig."""
    config: WidgetConfig = {
        'type': 'cpu'
    }

    assert config['type'] == 'cpu'
    assert 'id' not in config


def test_widget_config_disabled():
    """Тест создания отключённого виджета."""
    config: WidgetConfig = {
        'type': 'network',
        'enabled': False
    }

    assert config['enabled'] is False


# ===========================
# Тесты SteelClockConfig
# ===========================

def test_steelclock_config_full():
    """Тест создания полной SteelClockConfig."""
    config: SteelClockConfig = {
        'game_name': 'STEELCLOCK',
        'game_display_name': 'SteelClock Monitor',
        'display': {
            'width': 128,
            'height': 40,
            'background_color': 0
        },
        'layout': {
            'type': 'basic'
        },
        'widgets': [
            {
                'type': 'clock',
                'id': 'main_clock'
            },
            {
                'type': 'cpu',
                'id': 'cpu_monitor'
            }
        ],
        'refresh_rate_ms': 100
    }

    assert config['game_name'] == 'STEELCLOCK'
    assert config['display']['width'] == 128
    assert len(config['widgets']) == 2
    assert config['refresh_rate_ms'] == 100


def test_steelclock_config_minimal():
    """Тест создания минимальной SteelClockConfig."""
    config: SteelClockConfig = {
        'widgets': []
    }

    assert config['widgets'] == []


def test_steelclock_config_with_multiple_widgets():
    """Integration тест: конфигурация с несколькими виджетами."""
    config: SteelClockConfig = {
        'game_name': 'TEST',
        'widgets': [
            {
                'type': 'clock',
                'id': 'clock1',
                'position': {'x': 0, 'y': 0}
            },
            {
                'type': 'cpu',
                'id': 'cpu1',
                'position': {'x': 0, 'y': 20},
                'properties': {'display_mode': 'bar_horizontal'}
            },
            {
                'type': 'memory',
                'id': 'mem1',
                'position': {'x': 64, 'y': 20}
            }
        ]
    }

    assert len(config['widgets']) == 3
    assert config['widgets'][1]['properties']['display_mode'] == 'bar_horizontal'


# ===========================
# Тесты APIResponse
# ===========================

def test_api_response_error():
    """Тест создания APIResponse с ошибкой."""
    response: APIResponse = {
        'error': 'Not found'
    }

    assert response['error'] == 'Not found'


def test_api_response_message():
    """Тест создания APIResponse с сообщением."""
    response: APIResponse = {
        'message': 'Success'
    }

    assert response['message'] == 'Success'


def test_api_response_empty():
    """Edge case: пустой APIResponse."""
    response: APIResponse = {}

    assert len(response) == 0


# ===========================
# Integration тесты
# ===========================

def test_realistic_config_example():
    """Integration тест: реалистичный пример полной конфигурации."""
    config: SteelClockConfig = {
        'game_name': 'STEELCLOCK',
        'game_display_name': 'SteelClock System Monitor',
        'display': {
            'width': 128,
            'height': 40,
            'background_color': 0
        },
        'layout': {
            'type': 'basic'
        },
        'refresh_rate_ms': 100,
        'widgets': [
            {
                'type': 'clock',
                'id': 'main_clock',
                'enabled': True,
                'position': {
                    'x': 0,
                    'y': 0,
                    'w': 128,
                    'h': 12,
                    'z_order': 1
                },
                'style': {
                    'background_color': 0,
                    'border': False
                },
                'properties': {
                    'format': '%H:%M:%S',
                    'font_size': 10,
                    'horizontal_align': 'center'
                }
            },
            {
                'type': 'cpu',
                'id': 'cpu_bar',
                'enabled': True,
                'position': {
                    'x': 0,
                    'y': 14,
                    'w': 64,
                    'h': 12,
                    'z_order': 2
                },
                'properties': {
                    'display_mode': 'bar_horizontal',
                    'per_core': False,
                    'fill_color': 255,
                    'update_interval': 1.0
                }
            },
            {
                'type': 'memory',
                'id': 'mem_bar',
                'enabled': True,
                'position': {
                    'x': 64,
                    'y': 14,
                    'w': 64,
                    'h': 12,
                    'z_order': 2
                },
                'properties': {
                    'display_mode': 'bar_horizontal',
                    'fill_color': 200
                }
            },
            {
                'type': 'network',
                'id': 'network_monitor',
                'enabled': True,
                'position': {
                    'x': 0,
                    'y': 28,
                    'w': 128,
                    'h': 12,
                    'z_order': 3
                },
                'properties': {
                    'interface': 'eth0',
                    'display_mode': 'text',
                    'dynamic_scaling': True,
                    'rx_color': 200,
                    'tx_color': 100
                }
            }
        ]
    }

    # Проверяем основные параметры
    assert config['game_name'] == 'STEELCLOCK'
    assert config['display']['width'] == 128
    assert len(config['widgets']) == 4

    # Проверяем каждый виджет
    assert config['widgets'][0]['type'] == 'clock'
    assert config['widgets'][1]['type'] == 'cpu'
    assert config['widgets'][2]['type'] == 'memory'
    assert config['widgets'][3]['type'] == 'network'

    # Проверяем позиции
    assert config['widgets'][0]['position']['z_order'] == 1
    assert config['widgets'][3]['position']['y'] == 28


def test_viewport_mode_config_example():
    """Integration тест: конфигурация с viewport режимом."""
    config: SteelClockConfig = {
        'game_name': 'STEELCLOCK',
        'display': {
            'width': 128,
            'height': 40
        },
        'layout': {
            'type': 'viewport',
            'virtual_width': 256,
            'virtual_height': 80
        },
        'widgets': [
            {
                'type': 'clock',
                'id': 'clock1',
                'position': {
                    'x': 0,
                    'y': 0,
                    'w': 128,
                    'h': 20
                }
            },
            {
                'type': 'cpu',
                'id': 'cpu1',
                'position': {
                    'x': 128,
                    'y': 0,
                    'w': 128,
                    'h': 20
                }
            }
        ]
    }

    assert config['layout']['type'] == 'viewport'
    assert config['layout']['virtual_width'] == 256
    assert config['widgets'][1]['position']['x'] == 128


def test_all_widget_types_config():
    """Integration тест: конфигурация со всеми типами виджетов."""
    config: SteelClockConfig = {
        'widgets': [
            {'type': 'clock', 'id': 'w1'},
            {'type': 'cpu', 'id': 'w2'},
            {'type': 'memory', 'id': 'w3'},
            {'type': 'network', 'id': 'w4'},
            {'type': 'disk', 'id': 'w5'},
            {'type': 'keyboard', 'id': 'w6'}
        ]
    }

    widget_types = [w['type'] for w in config['widgets']]
    assert 'clock' in widget_types
    assert 'cpu' in widget_types
    assert 'memory' in widget_types
    assert 'network' in widget_types
    assert 'disk' in widget_types
    assert 'keyboard' in widget_types
