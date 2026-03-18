# Bear Game

A 2D side-scrolling action platformer game built with Python and Pygame.

## Project Overview

The player controls a bear character navigating through levels, defeating enemies (mummies, witches, green blobs), collecting keys, and ultimately facing a final "frankenbear" boss.

## Tech Stack

- **Language:** Python 3.8
- **Game Library:** Pygame 2.x
- **Package Manager:** Poetry

## Project Structure

```
main.py          - Entry point, creates and runs the game
Game/
  mainGame.py    - Main game file (~3500 lines) containing all game logic:
                   mainGame class, Bear (player), Mummy, Witch, GreenBlob,
                   FrankenBear (boss), Block, Background, Door, SpikeBlock,
                   KeyItem, HealthPowerItem entities
  Images/        - All graphical assets (PNG sprites organized by category)
  __init__.py    - Package init
pyproject.toml   - Poetry dependency config
poetry.lock      - Locked dependencies
```

## Running the Game

```bash
python main.py
```

## Workflow

- **Start application**: `python main.py` (VNC output for desktop GUI)

## Deployment

- Target: VM (always-running process)
- Command: `python main.py`
