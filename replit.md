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
- **Post-boss jungle music** — tribal jungle theme with congas, flute, bird chirps replaces the post-boss track
- **Beam power increase** — beam now does 4× normal damage (up from 3×); flashing "PRESS C FOR BEAM!" popup appears when fully charged
- **80% difficulty scaling** — enemies at Zone 8+ get additional 1.2× HP and ATK on top of hard mode
- **Boss slowed significantly** — FrankenBear attack intervals increased to 40-70 normal, 25-50 enraged
- **Fireball attack immunity removed** — fireballs now hit the bear regardless of attack state
- **MiniFrankenBear overhaul** — procedurally drawn green bear sprite with Frankenstein bolts/stitches; added to melee attack targets; laser now properly resets and fires repeatedly
- **ShadowShaman melee fix** — added to melee attack targets with proper 120×120 hitbox; has getDamageReceived/displayDamageOnMonster
- **Laser projectile** — laser is now a traveling green energy projectile (moves across screen) instead of a static beam; scrolls with world
- **Zone 8.5 "Shadow Ambush"** — new zone at distance 48000 with ShadowShamans, MiniFrankenBears, spikes, and mixed ground enemies
- **NG+ blue background** — New Game+ tints the background blue and randomizes starting enemy mix (mummies, witches, blobs, shamans, mini-bears)
- **FrankenBear visual details** — neck bolts, stitch marks, pulsing eyes (yellow→red when enraged) drawn on top of boss sprite
- **Fireball hitbox increased** — fireBall hitbox now 90×90 (up from 80×80) for more reliable collision
- **Beam damage display fix** — ShadowShamans and MiniFrankenBears now show correct beam damage numbers when hit
- **Silver fireball visual** — shiny silver fireball sprite at level 14+ with metallic highlights and radial sparkles
- **Silver fireball sound** — new higher-pitched energy sound (sine+sweep+noise) plays at level 10+; replaces normal fire sound
- **MiniFrankenBear stunned fix** — stunned counter now auto-resets after 20 frames; damage numbers clear properly; monster pauses while stunned
- **Beam damage display** — melee no longer overwrites beam damage number; stunned guard prevents re-hitting stunned enemies
- **Laser damage scales** — MiniFrankenBear laser now deals at least 10% of player's attack power (min 6)
- **80% zone speed boost** — green blob jump timer halved and witch fireball rate 40% faster at Zone 8+
- **NG+ extreme difficulty** — enemies get 1000% more HP, 300% more damage, 100% more XP per NG+ level; enemies also move 20% faster per NG+ level; applies to all zone-spawned enemies
- **MiniFrankenBear visual overhaul v2** — darker outlines, inner ear detail, red pupils, brown snout, teeth marks, zigzag belly stitching, arm stumps with claws, shoe-like feet, bigger shinier neck bolts
- **Laser damage scales to max HP** — laser now deals 10% of player's max HP (min 6) instead of 10% of attack power
- **Fireball damage scales to max HP** — all enemy fireballs (witch + boss) now deal 5% of player's max HP (min 4); hard mode still applies 1.8× multiplier
- **Zone spacing increased** — zones 5-9 and boss zone spread out significantly to prevent blocks from disappearing too soon (Zone 5: 34000, Zone 6: 39500, Zone 7: 45000, Zone 8: 50500, Zone 8.5: 53500, Zone 9: 56500, Boss: 60000)
- **Jungle level** — after beating FrankenBear, transitions to a jungle zone with jungle background, featuring snakes (poison), monkeys (parabolic jumps), and lions/tigers (fast runners); clearing the jungle triggers NG+
- **Lion enemy** — fast-running enemy (speed 5, charge speed 8) that dashes left and right with random charge bursts; uses tiger sprite; 140×100 hitbox
- **MonkeyMummy uses monkey sprite** — now loads monkey.png (120×140); jumps in proper parabolic arcs with horizontal velocity
- **Snake enemy** — poisonous ground enemy (120×80); poisons player on contact for 30s damage over time
- **FrankenBear hitbox bigger** — increased from 300×300 to 400×350 for easier hitting
- **FrankenBear fire rate slower** — normal: 60-100 frames (was 40-70), enraged: 40-70 (was 25-50)
- **75% difficulty scaling** — at Zone 7 (75% of level 1), all enemies get 2× HP and 2× ATK
- **Start menu** — cute title screen with floating sparkles, bear character with purple glow, "NORMAL" and "HARD" mode buttons; own spooky theme song (menu_theme.wav, 45s); no title text or descriptions
- **Hard mode** — enemies move faster (+30% speed, +1 minimum), travel longer distances before turning (1.8× rand/change_direction_timer), +50% damage pre-boss, +40% HP and damage post-mummy-boss; "HARD MODE" HUD indicator
- **All songs extended** — every music track extended to 50-60+ seconds with seamless crossfade repeats to reduce noticeable looping
- **FrankenBear fire rate decreased** — normal: 90-140 frames (was 60-100), enraged: 60-100 (was 40-70)
- **Bear stride reverted** — back to original 4-frame walk cycle using all 4 walking sprites in sequence
- **FrankenBear hitbox reverted** — back to original 300×300
- **Mummies 30% faster** — base rand changed from 1 to 2 (effectively doubles their movement speed)
- **Sound effects added** — boss_explosion_sound (2s heavy boom for bosses), enemy_hit_sound (short impact on kill), wave_warning_sound (rising tone at zone transitions), bear_hurt_sound (plays when player takes damage), enemy_spawn_sound (chime at zone spawns)
- **Boss explosions extended** — bigMummy: 60 frames with 2 fires, FrankenBear: 70 frames with 3→2 fires, both play boss_explosion_sound twice
- **Coins land on platforms** — Coin class checks blocks list; coins settle on the nearest block surface above instead of always falling to floor; re-validates if blocks are removed
- **Hard mode crash fixed** — changeDirectionX was being set to 0 causing ZeroDivisionError; now properly scaled ×1.8
- **Coyote time** — 6-frame grace period after walking off a platform edge where you can still jump (Mario/Castlevania principle)
- **Jump buffering** — pressing jump while airborne queues it; auto-jumps on landing within 8 frames (eliminates missed jumps)
- **Landing squash** — brief visual squash-and-stretch effect on landing for weight/impact feel
- **Smooth speed transitions** — combat/exploration speed change lerps gradually over ~10 frames instead of instantly snapping
- **Cinematic menu transition** — selecting Normal/Hard mode triggers a 2-second transition: white flash → mode label with outline floats up → subtitle fades in → fade-to-black with music fadeout → game starts
- **Castlevania-style walking** — bear has deliberate weighted stride with vertical bob (-2/+3/+5/+3 px cycle), slight body lean rotation (±1.5°), and slower frame cycling (10 frames per step vs 8); lean frames precomputed at init for zero runtime cost
- **Checkpoint save/restore rewrite** — saves all stats (HP, exp, level, coins, damage, lightning, big_fireball, shield, aimer, 50pct, hard mode flags); on restore: clears all entities (enemies, blocks, projectiles, doors, spikes), places bear on floor (y=300), finds the zone the save happened in via `_ZONE_THRESHOLDS`, resets that zone and all future zone flags so `deleteAndCreateObjects` re-triggers them naturally; also resets boss state, boundaries, background lock, lightning FX, water sounds, and trigger text flags
- **Jungle level overhaul** — two full zones (J1: 3 monkeys, 2 snakes, 2 lions + platforms; J2: 4 monkeys, 4 snakes, 3 lions + 6 platforms); door/key system removed; NG+ triggers after clearing zone 2; dedicated jungle_music.wav track plays throughout
- **Monkey animation** — 5-frame walk cycle (base + ±5°/±8° lean rotations), squash frame on landing (6 frames), stretch frame while airborne, vertical body bob (sin wave), screech sound effect on jump with 60-frame cooldown
- **Lion animation** — 5-frame walk cycle (base + ±3°/±5° lean rotations), charge frame (horizontally stretched), pounce attack (parabolic arc during charge), roar sound on charge start with 90-frame cooldown, body bob while walking
- **Floor clamping** — all jungle monsters enforce FLOOR_Y=400 floor boundary; lions pounce and always land on floor; monkeys jump and land on floor or platforms
- **Snake crash fix** — Snake, MonkeyMummy, and Lion were all missing `getDamageAttack()` methods; contact with any of them caused an AttributeError crash; all three now have the method
- **Snake animation** — 2-frame loop (base + 4° tilt) alternating every 20 frames for slithering look; height reduced to 60px for proper ground contact; floor-clamped to FLOOR_Y=400; `_MONSTER_SIZES` updated in both constants.py and mainGame.py
- **Two new music tracks** — "post_boss_march.wav" (triumphant victory march, 115 bpm, brass melody + spooky pad) plays after defeating the big mummy; "deep_crypt.wav" (dark driving descent, 125 bpm, minor pentatonic organ melody + tension risers) switches in at the 50% checkpoint
- **Speed variance expanded** — 15% chance ×1.5, 25% chance ×1.2, 40% chance ×1.1 (10% faster), 20% chance ×1.0 (unchanged); applies to walk_speed, speed, charge_speed, rand at spawn
- **Hard mode longer walking range** — enemies walk 1.8× longer before turning (up from halving timer); persistent via `_turn_timer_scale` attribute so timer resets in Snake/Lion/GreenBlob maintain the scale
- **Enemy health bar fix** — bar now properly shows lost health as dark red; rounding prevents bar from appearing 100% full when enemy has taken damage
- **Popup grace period** — hurtTimer frozen at 0 during popups; on popup close, hurtTimer set to -35 giving ~1 second invincibility before enemies can damage the player again
- **Silver mode speed cap** — movement speed capped at 12 in silver mode (level 14+) regardless of dead-zone boost
- **MonkeyMummy resized** — dimensions changed from 120×140 to 100×100 to match bear height; properly floor-clamped
