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

## Code Review Improvements (applied)

### Bug Fixes
- `Bear.leftJump()` — was referencing `self.blocks` (undefined attribute); fixed to use the `blocks` parameter → prevented crash on left-jumps
- `FireBall.setHealth()` — was returning `self.health` instead of assigning; fixed
- `SpikeBlock.setHealth()` — same broken setter pattern; fixed
- `FrankenBear.drawMonster()` — `self.attacked` was never reset to `False` after an attack cycle; boss could only attack once per life
- Witch appending bugs — several zones were appending the wrong witch instance variable, causing duplicate enemies and missing ones; all corrected
- Witch `setHurtTimer`/`getHurtTimer` defined twice — second definition silently overrode first; duplicate removed
- `pygame.QUIT` event handling — closing the window now exits cleanly from both the main loop and the text-box event pump

### Performance Fixes
- **Font caching** — `pygame.font.SysFont()` was called inside every `displayDamageOnMonster`, `displayBearHp`, and `displayBearExp` call (dozens of times per frame). Fonts are now created once at startup via `_init_fonts()` and shared as module-level constants.
- **FireBall scale** — `pygame.transform.scale()` was called every frame inside `drawFireBall()`. Image is now pre-scaled in `FireBall.__init__()`.
- **Background black image** — `pygame.image.load()` was called from disk inside `Background.update()` when switching to the boss-room black background. Image is now pre-loaded in `__init__()` and only the reference is swapped.
- **Frame timing** — replaced `time.sleep(0.010)` with `pygame.time.Clock.tick(60)` for accurate 60 FPS capping.

### Collision Detection
- Module-level `isBearHurt()` and `Bear.isBearHurt()` had three nearly-identical AABB checks (redundant), plus an unreachable fourth condition. Both replaced with a single `pygame.Rect.colliderect()` call using a centralised `_MONSTER_SIZES` dict.
- `isMonsterHurt()` simplified to use two clean attack hitboxes (facing-right and facing-left) matching the actual attack sprite widths (190px / 180px).
- `KeyItem.isKeyGrabbed()` replaced with `pygame.Rect.colliderect()`.

### Code Quality
- Extracted `_render_damage_text()` helper — the outlined damage-number drawing was copy-pasted identically into Mummy, Witch, GreenBlob, FrankenBear, and Bear.
- Removed all debug `print()` calls left in production paths (boss health per frame, `totalDistance` on key press, destructor `print` statements).
- Removed `moveObjects = []` assignments immediately overwritten on the next line (dead code).
- Removed `del monster` calls after `list.remove()` (del on a local variable is a no-op and misleading).
- `Background.update()` logic simplified and de-nested.
