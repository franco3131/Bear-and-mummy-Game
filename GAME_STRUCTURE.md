# Game Code Structure

## Folder Organization

The game code is now organized into focused modules for easy navigation and maintenance:

### Game/
- **constants.py** - Global game constants, monster sizes, and font initialization
- **collision.py** - Collision detection functions (snake_case naming)
  - `is_bear_hurt()` - Check if bear collides with objects
  - `is_monster_hurt()` - Check if bear attack hits monster
  - `is_monster_forehead_hit()` - Special hit detection for big mummy's head
  - `get_position_relative_to_monster()` - Determine bear's position relative to enemy

- **graphics.py** - Image/sprite manipulation utilities
  - `scale_image_to_box()` - Scale sprites while preserving aspect ratio
  - `create_outline_surface()` - Generate sprite outlines for visual effects

- **rendering.py** - All visual rendering (HUD, damage, water, effects)
  - `render_damage_text()` - Draw damage numbers with fade-in
  - `render_enemy_health_bar()` - Display temporary health bars
  - `render_hud_panel()` - Draw HUD element containers
  - `render_hud_bar()` - Draw progress bars (health, beam charge, etc.)
  - `render_hud_text_outlined()` - Outlined text for HUD elements
  - `render_water()` - Animated water effect

- **utils.py** - Legacy compatibility layer (can be deprecated)

- **mainGame.py** - Core game loop and all entity classes (Bear, Mummy, Witch, GreenBlob, etc.)

## Function Naming Convention

All functions now follow PEP 8 snake_case naming for consistency and readability:
- ❌ `isBearHurt()` → ✅ `is_bear_hurt()`
- ❌ `positionRelativeToMonster()` → ✅ `get_position_relative_to_monster()`
- ❌ `scale_to_box()` → ✅ `scale_image_to_box()`
- ❌ `make_outline_surf()` → ✅ `create_outline_surface()`

## Features

- **Faster fade-in**: Damage numbers fade in over 8 frames (regular enemies) / 12 frames (boss)
- **Temporary health bars**: Shows enemy health when damaged, positioned below damage numbers
- **Better code organization**: Clear separation of concerns - collision, graphics, rendering, constants
- **PEP 8 compliance**: Snake_case function names for improved readability

## To Run

```bash
python3 main.py
```
