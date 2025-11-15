"""
Фикстуры с примерами конфигураций для тестов.

Содержит готовые конфигурационные данные для:
- Полные конфигурации приложения
- Конфигурации отдельных виджетов всех типов
- Невалидные конфигурации для negative tests
"""

import pytest
from typing import Dict, Any


# =============================================================================
# Полные конфигурации приложения
# =============================================================================

@pytest.fixture
def minimal_app_config() -> Dict[str, Any]:
    """Минимальная валидная конфигурация приложения."""
    return {
        "game_name": "STEELCLOCK",
        "game_display_name": "SteelClock",
        "widgets": []
    }


@pytest.fixture
def full_app_config() -> Dict[str, Any]:
    """Полная конфигурация приложения со всеми опциями."""
    return {
        "game_name": "STEELCLOCK",
        "game_display_name": "SteelClock",
        "refresh_rate_ms": 100,
        "display": {
            "width": 128,
            "height": 40,
            "background_color": 0
        },
        "layout": {
            "type": "basic"
        },
        "widgets": [
            {
                "type": "clock",
                "id": "main_clock",
                "enabled": True,
                "position": {"x": 0, "y": 0, "w": 128, "h": 20, "z_order": 0},
                "properties": {"format": "%H:%M:%S"},
                "style": {"background_color": 0}
            }
        ]
    }


@pytest.fixture
def viewport_config() -> Dict[str, Any]:
    """Конфигурация с виртуальным канвасом и viewport."""
    return {
        "game_name": "STEELCLOCK",
        "display": {
            "width": 128,
            "height": 40
        },
        "layout": {
            "virtual_width": 256,
            "virtual_height": 80
        },
        "widgets": []
    }


# =============================================================================
# Widget-специфичные конфигурации
# =============================================================================

@pytest.fixture
def all_widget_types_config() -> Dict[str, Any]:
    """Конфигурация с по одному виджету каждого типа."""
    return {
        "game_name": "TEST",
        "widgets": [
            {
                "type": "clock",
                "id": "clock1",
                "position": {"x": 0, "y": 0, "w": 128, "h": 10},
                "properties": {"format": "%H:%M"}
            },
            {
                "type": "cpu",
                "id": "cpu1",
                "position": {"x": 0, "y": 10, "w": 128, "h": 10},
                "properties": {"display_mode": "bar_horizontal"}
            },
            {
                "type": "memory",
                "id": "mem1",
                "position": {"x": 0, "y": 20, "w": 128, "h": 10},
                "properties": {"display_mode": "text"}
            },
            {
                "type": "network",
                "id": "net1",
                "position": {"x": 0, "y": 30, "w": 64, "h": 10},
                "properties": {"interface": "Ethernet"}
            },
            {
                "type": "disk",
                "id": "disk1",
                "position": {"x": 64, "y": 30, "w": 64, "h": 10},
                "properties": {"disk_name": "PhysicalDrive0"}
            },
            {
                "type": "keyboard",
                "id": "kbd1",
                "position": {"x": 0, "y": 35, "w": 128, "h": 5},
                "properties": {}
            }
        ]
    }


# =============================================================================
# Невалидные конфигурации
# =============================================================================

@pytest.fixture
def invalid_config_not_dict() -> str:
    """Невалидная конфигурация - не словарь, а строка."""
    return "not a dictionary"


@pytest.fixture
def invalid_config_missing_game_name() -> Dict[str, Any]:
    """Конфигурация без обязательного game_name (но TypedDict не требует)."""
    return {
        "widgets": []
    }


@pytest.fixture
def invalid_config_malformed_widget() -> Dict[str, Any]:
    """Конфигурация с невалидным виджетом."""
    return {
        "game_name": "TEST",
        "widgets": [
            {
                "type": "unknown_type",  # Неизвестный тип виджета
                "id": "bad_widget"
            }
        ]
    }


@pytest.fixture
def invalid_config_negative_dimensions() -> Dict[str, Any]:
    """Конфигурация с отрицательными размерами."""
    return {
        "game_name": "TEST",
        "display": {
            "width": -128,
            "height": -40
        },
        "widgets": []
    }
