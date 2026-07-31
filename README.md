# StickNav

StickNav is a lightweight Windows utility that turns a game controller into a precise mouse and keyboard input device. It can move the cursor, click, scroll, and trigger shortcuts with a controller, making it useful for presentations, media control, accessibility, and relaxed desktop use.

## Features
- Left stick for cursor movement
- Right stick for scrolling
- Controller buttons for mouse clicks and keyboard actions
- Adjustable sensitivity and dead-zone settings

## Requirements
- Python 3.9 or newer
- Windows
- pygame

## Installation
1. Clone this repository.
2. If you already use Conda, create or update the environment with:
   ```bash
   conda env create -f environment.yml
   conda activate controller
   ```
3. Or install the Python dependencies directly:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
Run the controller app with:

```bash
python sticknav.py
```

Open the settings editor GUI with:

```bash
python sticknav.py --gui
```

The GUI saves your changes to a JSON file named sticknav_settings.json in the repository root.

## Development
To run the repository smoke tests:

```bash
pytest
```
