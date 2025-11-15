# SteelClock

[![CI](https://github.com/pozitronik/steelclock/actions/workflows/ci.yml/badge.svg)](https://github.com/pozitronik/steelclock/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pozitonik/steelclock/branch/main/graph/badge.svg)](https://codecov.io/gh/pozitonik/steelclock)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Customizable display manager for SteelSeries devices.

Transform your SteelSeries OLED display into a powerful real-time system monitoring dashboard with fully customizable widgets, layouts, and styling.

## Features

- **6 Built-in Widgets**: Clock, CPU, Memory, Network, Disk I/O, Keyboard Indicators
- **Multiple Display Modes**: Text, horizontal bars, vertical bars, animated graphs
- **Flexible Layout System**: Position and size widgets anywhere on the display
- **Layer Support**: Stack widgets with z-order and transparency
- **Customizable Styling**: Fonts, colors, borders, alignment, opacity
- **Real-time Monitoring**: Independent update rates for each widget
- **JSON Configuration**: Validated configuration with IDE autocomplete support

## Hardware Compatibility

SteelClock works with SteelSeries devices that have OLED displays and support the GameSense SDK:

- **Tested**: SteelSeries Apex 7 (128x40 monochrome display)
- **Should work**: Any SteelSeries device with OLED screen support

The default configuration targets 128x40 displays but can be adjusted for different resolutions.

## Requirements

- **Hardware**: SteelSeries device with OLED display
- **Software**:
  - Python 3.12 or higher
  - SteelSeries Engine 3 (must be running)
  - Windows (SteelSeries Engine requirement)

## Installation

1. Clone this repository:

```bash
git clone https://github.com/pozitonik/steelclock.git
```

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Quick Start

1. Ensure SteelSeries Engine 3 is installed and running

2. Run SteelClock with the default configuration:

```bash
python main.py
```

Or specify a custom configuration:

```bash
python main.py config.json
```

3. Stop SteelClock: Press `Ctrl+C`

## Configuration

SteelClock uses JSON configuration files with JSON Schema support for validation and IDE autocomplete.

### Basic Configuration Structure

```json
{
  "$schema": "./configs/config.schema.json",
  "game_name": "STEELCLOCK",
  "game_display_name": "SteelClock",
  "refresh_rate_ms": 100,

  "display": {
    "width": 128,
    "height": 40,
    "background_color": 0
  },

  "widgets": [
    {
      "type": "clock",
      "id": "main_clock",
      "enabled": true,
      "position": {"x": 0, "y": 0, "w": 128, "h": 40, "z_order": 0},
      "style": {"background_color": 0, "border": false},
      "properties": {
        "format": "%H:%M:%S",
        "font_size": 12
      }
    }
  ]
}
```

For detailed configuration documentation, see [CONFIG_GUIDE.md](configs/CONFIG_GUIDE.md).

## Available Widgets

### Clock Widget
Displays current time with customizable format.

**Display Modes**: Text only
**Key Options**: `format` (strftime), `font`, `font_size`, alignment

**Example**:
```json
{
  "type": "clock",
  "properties": {
    "format": "%H:%M:%S",
    "font_size": 12
  }
}
```

### CPU Widget
Monitors CPU usage with per-core support.

**Display Modes**: text, bar_horizontal, bar_vertical, graph
**Key Options**: `per_core`, `display_mode`, `fill_color`

**Example**:
```json
{
  "type": "cpu",
  "properties": {
    "display_mode": "graph",
    "per_core": false,
    "history_length": 30
  }
}
```

### Memory Widget
Monitors RAM usage.

**Display Modes**: text, bar_horizontal, bar_vertical, graph
**Key Options**: `display_mode`, `fill_color`, `history_length`

**Example**:
```json
{
  "type": "memory",
  "properties": {
    "display_mode": "bar_horizontal"
  }
}
```

### Network Widget
Monitors network I/O (RX/TX).

**Display Modes**: text, bar_horizontal, bar_vertical, graph
**Key Options**: `interface`, `max_speed_mbps`, `rx_color`, `tx_color`

**Example**:
```json
{
  "type": "network",
  "properties": {
    "interface": "Ethernet",
    "display_mode": "graph",
    "max_speed_mbps": -1
  }
}
```

### Disk Widget
Monitors disk I/O (read/write).

**Display Modes**: text, bar_horizontal, bar_vertical, graph
**Key Options**: `disk_name`, `max_speed_mbps`, `read_color`, `write_color`

**Disk Names**:
- **Windows**: `PhysicalDrive0`, `PhysicalDrive1`, ...
- Use `null` for auto-selection

**Example**:
```json
{
  "type": "disk",
  "properties": {
    "disk_name": "PhysicalDrive0",
    "display_mode": "bar_horizontal",
    "max_speed_mbps": -1
  }
}
```

### Keyboard Widget
Shows Caps Lock, Num Lock, Scroll Lock status.

**Display Modes**: Text only (customizable symbols)
**Key Options**: Symbol customization for ON/OFF states, colors

**Example**:
```json
{
  "type": "keyboard",
  "properties": {
    "font": "Segoe UI Emoji",
    "caps_lock_on": "⬆",
    "num_lock_on": "🔒",
    "scroll_lock_on": "⬇",
    "caps_lock_off": "",
    "indicator_color_on": 255,
    "indicator_color_off": 100
  }
}
```

## Fonts

The application automatically downloads a bundled TrueType font (Fixedsys Excelsior) on first use for cross-platform compatibility.

Supported system fonts include:
- **Standard**: Arial, Consolas, Courier New, Times New Roman, Verdana
- **Emoji**: Segoe UI Emoji (Windows)
- **Custom**: Specify path to any TTF file

## Troubleshooting

### SteelSeries Engine Not Found

**Error**: "Cannot find coreProps.json"

**Solution**:
- Ensure SteelSeries Engine 3 is installed and running
- Check Task Manager for "SteelSeries Engine" process
- Default path: `C:\ProgramData\SteelSeries\SteelSeries Engine 3\coreProps.json`

### Display Not Updating

**Possible causes**:
- Device not connected or not recognized
- SteelSeries Engine not running
- Device doesn't support GameSense SDK

**Solution**:
- Reconnect device
- Restart SteelSeries Engine
- Check logs for errors

### Module Import Errors

**Error**: "No module named 'psutil'" or similar

**Solution**:
```bash
pip install -r requirements.txt
```

### Network Interface Not Found

**Windows**: Use interface name from Network Connections (e.g., "Ethernet", "Wi-Fi")

**Auto-detect**: Set `"interface": null`

### Disk Not Found

Run SteelClock once to see available disks in logs:
```
Available disks: PhysicalDrive0, PhysicalDrive1
```

Use the disk name from logs in config:
```json
"disk_name": "PhysicalDrive0"
```

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=. --cov-report=html

# Run specific test file
python -m pytest tests/unit/widgets/test_cpu.py
```

### Type Checking

```bash
python -m mypy .
```

### Code Style

```bash
flake8 .
```

## Performance Notes

- Refresh rate is capped at 10Hz (100ms) per SteelSeries SDK recommendations
- Each widget runs in its own thread with independent update intervals
- Graph modes store history (default 30 samples)
- Lower `update_interval` values increase CPU usage

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [SteelSeries GameSense SDK](https://github.com/SteelSeries/gamesense-sdk) for device communication
- [Pillow](https://python-pillow.org/) for image processing
- [psutil](https://github.com/giampaolo/psutil) for system monitoring
- [Fixedsys Excelsior](https://github.com/kika/fixedsys) for bundled font
