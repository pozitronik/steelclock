# SteelClock

OLED display manager for SteelSeries APEX 7 keyboard (128x40 monochrome display).

Transform your keyboard's OLED into a powerful system monitoring dashboard with customizable widgets, layouts, and real-time updates.

## Features

- **6 Built-in Widgets**: Clock, CPU, Memory, Network, Disk I/O, Keyboard Indicators
- **Multiple Display Modes**: Text, horizontal bars, vertical bars, animated graphs
- **Flexible Layout System**: Position and size widgets anywhere on the display
- **Layer Support**: Stack widgets with z-order and transparency
- **Customizable Styling**: Fonts, colors, borders, alignment, opacity
- **Real-time Monitoring**: Independent update rates for each widget
- **JSON Configuration**: Validated configuration with IDE autocomplete support

## Requirements

- **Hardware**: SteelSeries APEX 7 keyboard with OLED display
- **Software**:
  - Python 3.8 or higher
  - SteelSeries Engine 3 (must be running)
  - Windows (SteelSeries Engine requirement)

## Installation

1. Clone or download this repository

2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install requests Pillow psutil
```

## Quick Start

1. **Choose a configuration** from the `configs/` folder or create your own:
   - `config_complete_dashboard.json` - Full system monitoring dashboard
   - `config_keyboard_demo.json` - Keyboard indicator example
   - `config_network_demo.json` - Network monitoring
   - See `configs/` folder for more examples

2. **Run SteelClock**:

```bash
python main.py configs/config_complete_dashboard.json
```

Or use the default config:

```bash
python main.py
```

3. **Stop SteelClock**: Press `Ctrl+C`

## Configuration

SteelClock uses JSON configuration files. The configuration includes a **JSON Schema** for validation and IDE autocomplete.

### Using JSON Schema in Your IDE

To enable autocomplete and validation, add this line at the top of your config file:

```json
{
  "$schema": "./config.schema.json",
  "game_name": "STEELCLOCK",
  ...
}
```

Supported IDEs: VS Code, JetBrains IDEs, Visual Studio, and any editor with JSON Schema support.

### Basic Configuration Structure

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
    "interface": "eth0",
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
- **Linux**: `sda`, `sdb`, `nvme0n1`, ...
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

## Common Configuration Patterns

### Dashboard Layout

Split the display into sections for different widgets:

```json
"widgets": [
  {"type": "clock", "position": {"x": 0, "y": 0, "w": 96, "h": 8}},
  {"type": "keyboard", "position": {"x": 96, "y": 0, "w": 32, "h": 8}},
  {"type": "cpu", "position": {"x": 0, "y": 8, "w": 32, "h": 8}},
  {"type": "memory", "position": {"x": 32, "y": 8, "w": 32, "h": 8}},
  {"type": "disk", "position": {"x": 64, "y": 8, "w": 64, "h": 8}},
  {"type": "network", "position": {"x": 0, "y": 16, "w": 128, "h": 24}}
]
```

### Transparent Overlays

Use `background_opacity` to blend widgets:

```json
"style": {
  "background_color": 0,
  "background_opacity": 128
}
```

### Dynamic Scaling

Use `-1` for auto-scaling graphs:

```json
"properties": {
  "display_mode": "graph",
  "max_speed_mbps": -1
}
```

### Emoji Support

Use emoji-compatible fonts for special characters:

```json
"properties": {
  "font": "Segoe UI Emoji",
  "caps_lock_on": "🔼"
}
```

## Fonts

Supported fonts include:
- **Standard**: Arial, Consolas, Courier New, Times New Roman, Verdana
- **Emoji**: Segoe UI Emoji (Windows), Noto Color Emoji (Linux)
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
- Keyboard not connected or not recognized
- SteelSeries Engine not running
- Wrong keyboard model (must be APEX 7)

**Solution**:
- Reconnect keyboard
- Restart SteelSeries Engine
- Check logs for errors

### Module Import Errors

**Error**: "No module named 'psutil'" or similar

**Solution**:
```bash
pip install -r requirements.txt
```

### Emoji Not Displaying

**Problem**: Emojis show as empty boxes

**Solution**: Use emoji-compatible font:
```json
"properties": {
  "font": "Segoe UI Emoji"
}
```

### Network Interface Not Found

**Windows**: Use interface name from Network Connections (e.g., "Ethernet", "Wi-Fi")
**Linux**: Use interface name from `ip addr` (e.g., "eth0", "wlan0")

**Auto-detect**: Set `"interface": null`

### Disk Not Found

**Windows**: Run SteelClock once to see available disks in logs:
```
Available disks: PhysicalDrive0, PhysicalDrive1
```

Use the disk name from logs in config:
```json
"disk_name": "PhysicalDrive0"
```

### Virtual Canvas (Scrolling)

Create a larger virtual canvas:

```json
"layout": {
  "type": "viewport",
  "virtual_width": 256,
  "virtual_height": 80
}
```

### Z-Order Layering

Stack widgets with `z_order`:

```json
"position": {
  "x": 0, "y": 0, "w": 128, "h": 40,
  "z_order": 10
}
```

### Multiple Instances

Run multiple instances of the same widget:

```json
"widgets": [
  {"type": "disk", "id": "disk_c", "properties": {"disk_name": "PhysicalDrive0"}},
  {"type": "disk", "id": "disk_d", "properties": {"disk_name": "PhysicalDrive1"}}
]
```

## Logging

Logs are written to stdout. To increase verbosity, edit `main.py`:

```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## Performance Notes

- Refresh rate is capped at 10Hz (100ms) per SteelSeries SDK recommendations
- Each widget runs in its own thread with independent update intervals
- Graph modes store history (default 30 samples)
- Lower `update_interval` increases CPU usage

## Project Structure

```
python/
├── configs/
│   ├── config.schema.json       # JSON Schema for validation
│   ├── CONFIG_GUIDE.md          # Detailed configuration guide
│   └── *.json                   # Example configurations
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── gamesense/                   # SteelSeries API client
├── core/                        # Core application logic
├── widgets/                     # Widget implementations
└── utils/                       # Utility functions
```

## Support

For issues, questions, or feature requests, see:
- Configuration guide: [configs/CONFIG_GUIDE.md](configs/CONFIG_GUIDE.md)
- Development notes: [NOTES.md](NOTES.md)
- JSON Schema: [configs/config.schema.json](configs/config.schema.json)

## License

GNU GPL 3.0
