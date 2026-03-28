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
  mainGame.py    - Main game file (~4000 lines) containing all game logic:
                   mainGame class, Bear (player), Mummy, Witch, GreenBlob,
                   FrankenBear (boss), ShadowShaman, MiniFrankenBear,
                   Block, Background, Door, SpikeBlock, Waterfall,
                   KeyItem, HealthPowerItem entities
  Images/        - All graphical assets (PNG sprites organized by category)
  Sounds/        - Audio assets: spooky_peaceful.wav (normal music),
                   halfway_intense.wav (halfway music),
                   boss_spooky.wav (boss music), fireball.wav,
                   blob_jump.wav, jump_yell.wav, thud.wav,
                   water_ambient.wav, footstep.wav, door_open.wav,
                   key_pickup.wav, level_up.wav, boss_entrance.wav,
                   deflect.wav, spike_hit.wav, mummy_groan.wav,
                   laser_zap.wav, boss_hit.wav,
                   post_boss_normal.wav (post-first-boss music with harp)
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

### Gameplay Features
- **4-frame walk cycle** — bearWalking4.png created as composite (walk3 upper + walk2 lower) for proper transition pose with correct foot direction; sequence: [walk1, walk2, walk4, walk3]
- **Explosion sound redesign** — replaced noise-slap with deep rumbling boom using 45/30/60Hz bass sine waves, short crackle, and 20Hz sub-rumble with 0.55s envelope
- **Post-boss music** — after first boss (bigMummy) defeat, music switches to post_boss_normal.wav which adds a plucked harp arpeggio layer over the base Egyptian theme
- **Silver mode (level 14)** — all bear sprites tinted silver via BLEND_RGB_MULT + BLEND_RGB_ADD; permanent 50% speed increase (STEP 8→12); "SILVER MODE ACTIVATED!" notification
- **Dead zone speed boost** — dynamic STEP each frame: when no alive enemies within visible range (-150 to 950 px), movement speed boosted by 50%; returns to normal when enemies are on screen
- **Dynamic STEP** — `STEP` is now a mutable global modified per frame based on silver mode + dead zone state (base 8/12 × 1.0/1.5)
- **Critical hits** — 20% chance on both melee attacks and fireballs for 2× damage; plays a distinct heavy crit sound
- **Fireball speed boost** — at level 12+, fireball speed gets a 3× multiplier (100% faster than previous 1.5× boost)
- **Mid-game difficulty scaling** — at Zone 4 (25500+ distance, ~50% mark), all new enemies get +50% HP, +50% attack; enemies tinted red; experience gain boosted by 75%
- **Beam super attack** — charge bar fills slowly (0.1/frame); press C when full to fire a piercing beam dealing 5× damage; charge bar shown in HUD with "BEAM" label; "C:READY" text when fully charged
- **Explosion sound redesign v3** — 0.55s punchy mid-frequency boom (50-180Hz range) with blast crack, rumble, and high volume; audible and impactful
- **Boss fireball collision fix** — fireball hitbox increased from 60×60 to 80×80 for better collision detection with the bear
- **Red floor at 50% mark** — floor texture tinted red when hard mode activates at Zone 4; difficulty increased to 1.7× HP and ATK (up from 1.5×)
- **Boss fireball rate slowed** — boss throws fireballs less frequently (normal: 18-35 frame intervals, enraged: 12-25)
- **Fireball speed at level 12+** — reduced from 3× to 2.5× boost (75% increase instead of 100%)
- **Attack immunity to fireballs** — bear is immune to all fireball damage while in melee attack animation
- **MiniFrankenBear sprite fix** — now uses boss1.png scaled to 80×80 with green tint instead of placeholder circle; proper hurt/destruction animations; collision hitbox added to `_MONSTER_SIZES`
- **ShadowShaman collision fix** — added 120×120 hitbox to `_MONSTER_SIZES` so contact damage works
- **Beam damage reduced** — beam super attack now does 3× normal damage (down from 5×)
- **Fireball damage reduced** — all fireballs (witch and boss) deal 20% less damage (4 base instead of 5)
- **80% music track** — exciting fast-paced "final push" music (Am-F-G-Em progression, 160 BPM) triggers at Zone 8 (46000 distance)
