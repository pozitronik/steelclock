# SteelClock Configuration Guide

## Overview

SteelClock V2 supports comprehensive JSON configuration for all display aspects:
- Widget positioning, sizing, and z-order
- Multiple instances of same widget type
- Widget styling (background, borders)
- Display background
- Virtual canvas / viewport (scrolling)

## Configuration Structure

```json
{
  "game_name": "STEELCLOCK",
  "game_display_name": "SteelClock",
  "refresh_rate_ms": 100,

  "display": { ... },
  "layout": { ... },
  "widgets": [ ... ]
}
```

## Display Configuration

```json
"display": {
  "width": 128,           // Physical display width
  "height": 40,           // Physical display height
  "background_color": 0   // 0=black, 255=white, 0-255=gray
}
```

## Layout Configuration

### Basic Layout (Fixed Size)

```json
"layout": {
  "type": "basic"
}
```

### Advanced Layout (Virtual Canvas / Scrolling)

```json
"layout": {
  "type": "viewport",
  "virtual_width": 256,   // Virtual canvas can be larger
  "virtual_height": 80    // than physical display
}
```

## Widget Configuration

Each widget in the `widgets` array has this structure:

```json
{
  "type": "clock",           // Widget type
  "id": "unique_id",         // Unique identifier
  "enabled": true,           // Enable/disable widget

  "position": { ... },       // Position and size
  "style": { ... },          // Visual styling
  "properties": { ... }      // Widget-specific settings
}
```

### Position Configuration

```json
"position": {
  "x": 0,          // X coordinate on canvas
  "y": 0,          // Y coordinate on canvas
  "w": 128,        // Width in pixels
  "h": 40,         // Height in pixels
  "z_order": 0     // Stacking order (higher = on top)
}
```

### Style Configuration

```json
"style": {
  "background_color": 0,    // 0-255 (0=black, 255=white)
  "border": false,          // Draw border?
  "border_color": 255       // Border color (0-255)
}
```

### Clock Widget Properties

```json
"properties": {
  "format": "%H:%M:%S",         // strftime format string
  "font_size": 12,              // Font size in points
  "font": "Arial",              // Font name or path (optional)
  "horizontal_align": "center", // Horizontal alignment: "left", "center", "right"
  "vertical_align": "center",   // Vertical alignment: "top", "center", "bottom"
  "padding": 0,                 // Padding from edges in pixels
  "update_interval": 1.0        // Update frequency in seconds
}
```

#### Font Property

The `font` property can be:
- **Font name** (e.g., `"Arial"`, `"Consolas"`, `"Courier New"`)
  - Automatically resolved from Windows fonts directory
  - Case-insensitive
- **Full path** to a TTF file (e.g., `"C:/Windows/Fonts/arial.ttf"`)
- **Omitted** (uses default font)

Supported font names:
- `Arial`, `Arial Bold`, `Arial Italic`
- `Consolas`, `Consolas Bold`
- `Courier New`, `Courier New Bold`
- `Comic Sans`, `Comic Sans MS`
- `Georgia`, `Impact`, `Tahoma`
- `Times New Roman`, `Times New Roman Bold`
- `Trebuchet MS`, `Verdana`, `Verdana Bold`
- `Lucida Console`
- `DejaVu Sans`, `DejaVu Sans Mono`

**Examples:**
```json
"font": "Arial"
"font": "Consolas"
"font": "C:/Windows/Fonts/comic.ttf"
```

#### Content Alignment

Control where content appears within the widget:

**`horizontal_align`** - Horizontal alignment:
- `"left"` - Align to left edge (with padding)
- `"center"` - Center horizontally (default)
- `"right"` - Align to right edge (with padding)

**`vertical_align`** - Vertical alignment:
- `"top"` - Align to top edge (with padding)
- `"center"` - Center vertically (default)
- `"bottom"` - Align to bottom edge (with padding)

**`padding`** - Space from edges in pixels (applies to aligned edges)

**Examples:**
```json
// Top-left corner with 5px padding
"horizontal_align": "left",
"vertical_align": "top",
"padding": 5

// Bottom-right corner
"horizontal_align": "right",
"vertical_align": "bottom",
"padding": 3

// Centered (default)
"horizontal_align": "center",
"vertical_align": "center"
```

#### Common Time Format Examples:

| Format | Example Output | Description |
|--------|---------------|-------------|
| `%H:%M:%S` | 15:43:27 | 24-hour with seconds |
| `%H:%M` | 15:43 | 24-hour without seconds |
| `%I:%M:%S %p` | 03:43:27 PM | 12-hour with AM/PM |
| `%Y-%m-%d` | 2025-11-14 | ISO date |
| `%d.%m.%Y` | 14.11.2025 | European date |
| `%A, %B %d` | Thursday, November 14 | Full date |
| `%a %H:%M` | Thu 15:43 | Short day + time |

Full format codes: https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior

## Complete Examples

### Example 1: Simple Clock (Full Screen)

```json
{
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
      "enabled": true,
      "position": {
        "x": 0,
        "y": 0,
        "w": 128,
        "h": 40,
        "z_order": 0
      },
      "style": {
        "background_color": 0,
        "border": false
      },
      "properties": {
        "format": "%H:%M:%S",
        "font_size": 12,
        "update_interval": 1.0
      }
    }
  ]
}
```

### Example 2: Two Clocks (Time + Date)

```json
{
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
      "id": "time_display",
      "enabled": true,
      "position": {
        "x": 0,
        "y": 0,
        "w": 128,
        "h": 20,
        "z_order": 1
      },
      "style": {
        "background_color": 0,
        "border": false
      },
      "properties": {
        "format": "%H:%M:%S",
        "font_size": 12,
        "update_interval": 1.0
      }
    },
    {
      "type": "clock",
      "id": "date_display",
      "enabled": true,
      "position": {
        "x": 0,
        "y": 20,
        "w": 128,
        "h": 20,
        "z_order": 0
      },
      "style": {
        "background_color": 0,
        "border": true,
        "border_color": 128
      },
      "properties": {
        "format": "%Y-%m-%d %A",
        "font_size": 8,
        "update_interval": 60.0
      }
    }
  ]
}
```

### Example 3: Split Screen (Two Times)

```json
{
  "widgets": [
    {
      "type": "clock",
      "id": "local_time",
      "enabled": true,
      "position": {
        "x": 0,
        "y": 0,
        "w": 64,
        "h": 40,
        "z_order": 0
      },
      "style": {
        "background_color": 0,
        "border": true,
        "border_color": 255
      },
      "properties": {
        "format": "%H:%M\nLOCAL",
        "font_size": 10,
        "update_interval": 1.0
      }
    },
    {
      "type": "clock",
      "id": "utc_time",
      "enabled": true,
      "position": {
        "x": 64,
        "y": 0,
        "w": 64,
        "h": 40,
        "z_order": 0
      },
      "style": {
        "background_color": 50,
        "border": true,
        "border_color": 255
      },
      "properties": {
        "format": "%H:%M\nUTC",
        "font_size": 10,
        "update_interval": 1.0
      }
    }
  ]
}
```

### Example 4: Multi-Section Dashboard (with borders)

```json
{
  "widgets": [
    {
      "type": "clock",
      "id": "header_clock",
      "enabled": true,
      "position": {"x": 0, "y": 0, "w": 128, "h": 13, "z_order": 10},
      "style": {"background_color": 255, "border": true, "border_color": 0},
      "properties": {"format": "%H:%M:%S", "font_size": 8, "update_interval": 1.0}
    },
    {
      "type": "clock",
      "id": "section1",
      "enabled": true,
      "position": {"x": 0, "y": 13, "w": 42, "h": 27, "z_order": 0},
      "style": {"background_color": 0, "border": true, "border_color": 128},
      "properties": {"format": "%d", "font_size": 10, "update_interval": 60.0}
    },
    {
      "type": "clock",
      "id": "section2",
      "enabled": true,
      "position": {"x": 43, "y": 13, "w": 42, "h": 27, "z_order": 0},
      "style": {"background_color": 0, "border": true, "border_color": 128},
      "properties": {"format": "%b", "font_size": 8, "update_interval": 60.0}
    },
    {
      "type": "clock",
      "id": "section3",
      "enabled": true,
      "position": {"x": 86, "y": 13, "w": 42, "h": 27, "z_order": 0},
      "style": {"background_color": 0, "border": true, "border_color": 128},
      "properties": {"format": "%a", "font_size": 8, "update_interval": 60.0}
    }
  ]
}
```

## Running with Custom Config

```bash
# Use default config (config_advanced.json)
python main_v2.py

# Use custom config file
python main_v2.py my_config.json

# Use original simple config
python main.py
```

## Widget Layering (Z-Order)

Widgets with higher `z_order` appear on top:

```json
{
  "widgets": [
    {"id": "background", "position": {"z_order": 0}},  // Bottom
    {"id": "content", "position": {"z_order": 1}},     // Middle
    {"id": "overlay", "position": {"z_order": 10}}     // Top
  ]
}
```

## Enabling/Disabling Widgets

Temporarily disable widgets without removing them:

```json
{
  "type": "clock",
  "id": "optional_clock",
  "enabled": false,  // Widget will not be loaded
  ...
}
```

## Tips and Tricks

### High Contrast Display

```json
"style": {
  "background_color": 255,  // White background
  "border": true,
  "border_color": 0         // Black border
}
```

Text automatically inverts to black on white background.

### Subtle Borders

```json
"style": {
  "background_color": 0,
  "border": true,
  "border_color": 64   // Dark gray border
}
```

### Update Intervals

- `1.0` - Update every second (for clocks with seconds)
- `60.0` - Update every minute (for date displays)
- `0.5` - Update twice per second (for animations)

### Font Sizing

- Small display (128x40) works best with fonts 6-14
- Font 6-8: For dense information (dates, small labels)
- Font 10-12: For main content (time displays)
- Font 14+: For emphasis (only a few characters fit)

## Troubleshooting

### Widget not appearing?

- Check `"enabled": true`
- Verify position is within display bounds
- Check z_order isn't hidden behind other widgets

### Text not visible?

- Ensure background_color and text contrast
- Text auto-inverts: white on dark, black on light
- Check font_size isn't too large for widget height

### Widgets overlapping incorrectly?

- Review z_order values
- Higher z_order = appears on top

## Future Widget Types

The config system is designed to support additional widget types:

- CPU usage widget
- Memory widget
- Network stats widget
- GPU monitor widget
- Custom text widget
- Progress bar widget
- Graph widget

Each will have its own `properties` section specific to that widget type.
