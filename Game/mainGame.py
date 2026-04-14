# -*- coding: utf-8 -*-
"""Main game class and game loop."""
import pygame
import random
import json
import os
import math
from Game.constants import (
    STEP, JUMP_STEP, _MONSTER_SIZES, BEAR_W, BEAR_H,
    init_fonts, get_font
)
from Game.collision import (
    get_position_relative_to_monster,
    is_bear_hurt, is_monster_hurt, is_monster_forehead_hit
)
from Game.rendering import (
    render_damage_text, render_enemy_health_bar,
    render_hud_panel, render_hud_bar, render_hud_text_outlined,
    render_water
)
from Game.graphics import (
    scale_image_to_box, create_outline_surface
)

# ---------------------------------------------------------------------------
# Module-level font cache – created once after pygame.init(), reused every frame
# ---------------------------------------------------------------------------
_FONT_DAMAGE = None
_FONT_HUD = None
_FONT_BOSS_DAMAGE = None
_FONT_POPUP = None
_FONT_HUD_LABEL = None
_FONT_HUD_VAL = None
_FONT_HUD_LVL = None
_FONT_HP_BAR = None


def init_fonts():
    global _FONT_DAMAGE, _FONT_HUD, _FONT_BOSS_DAMAGE, _FONT_POPUP
    global _FONT_HUD_LABEL, _FONT_HUD_VAL, _FONT_HUD_LVL, _FONT_HP_BAR
    _FONT_DAMAGE = pygame.font.SysFont("Italic", 40)
    _FONT_HUD = pygame.font.SysFont("Italic", 40)
    _FONT_BOSS_DAMAGE = pygame.font.SysFont("Italic", 60)
    _FONT_POPUP = pygame.font.SysFont("Italic", 26)
    _FONT_HUD_LABEL = pygame.font.SysFont(None, 26, bold=True)
    _FONT_HUD_VAL = pygame.font.SysFont(None, 20, bold=True)
    _FONT_HUD_LVL = pygame.font.SysFont(None, 38, bold=True)
    _FONT_HP_BAR = pygame.font.SysFont(None, 16, bold=True)


def render_hud_panel(screen, x, y, w, h, border_color, border=3):
    inner = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, (18, 14, 26), inner, border_radius=6)
    pygame.draw.rect(screen, border_color, inner, border, border_radius=6)


def render_hud_bar(screen, x, y, w, h, ratio, fill_color):
    track = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, (40, 30, 40), track, border_radius=4)
    fill_w = max(0, int(w * ratio))
    if fill_w > 0:
        fill = pygame.Rect(x, y, fill_w, h)
        pygame.draw.rect(screen, fill_color, fill, border_radius=4)
    pygame.draw.rect(screen, (200, 200, 200), track, 1, border_radius=4)


def render_hud_text_outlined(screen, font, text, x, y, color, outline=(0, 0, 0)):
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        screen.blit(font.render(text, True, outline), (x + dx, y + dy))
    screen.blit(font.render(text, True, color), (x, y))


def _apply_defense(monster, dmg):
    """Reduce damage by monster's defense percentage (1-10%)."""
    defense = getattr(monster, '_defense', 0.0)
    return max(1, int(dmg * (1.0 - defense)))


def render_enemy_health_bar(screen, x, y, health, max_health, w=120, h=12):
    """Percentage-based health bar: health/max_health = fill%.
    Example: 50/100 hp → bar is exactly 50% filled."""
    try:
        max_health = int(max_health) if max_health else 0
        health = int(health) if health else 0
        if max_health <= 0:
            return
        if health >= max_health:
            return
        if health < 0:
            health = 0
        pct = health / max_health
    except Exception:
        return
    bar_x = x + 10
    bar_y = y + 36
    pygame.draw.rect(screen, (30, 20, 30), (bar_x, bar_y, w, h), border_radius=3)
    pygame.draw.rect(screen, (120, 20, 20), (bar_x, bar_y, w, h), border_radius=3)
    fill_w = int(w * pct)
    if fill_w > 0:
        if pct > 0.6:
            c = (60, 200, 60)
        elif pct > 0.3:
            c = (220, 200, 60)
        else:
            c = (220, 60, 60)
        pygame.draw.rect(screen, c, (bar_x, bar_y, fill_w, h), border_radius=3)
    pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, w, h), 1, border_radius=3)
    if _FONT_HP_BAR and h >= 12:
        pct_text = f"{int(pct * 100)}%"
        _ts = _FONT_HP_BAR.render(pct_text, True, (255, 255, 255))
        screen.blit(_ts, (bar_x + w // 2 - _ts.get_width() // 2, bar_y + h // 2 - _ts.get_height() // 2))


# ---------------------------------------------------------------------------
# Collision helpers (using pygame.Rect for clean, accurate AABB detection)
# ---------------------------------------------------------------------------
_MONSTER_SIZES = {
    "mummy":          (100, 100),
    "bigMummy":       (200, 300),
    "fireBall":       (90,  90),
    "witch":          (100, 100),
    "greenBlob":      (100, 100),
    "bigGreenBlob":   (300, 400),
    "spikes":         (600, 60),
    "frankenbears":   (300, 300),
    "shadowShaman":   (120, 120),
    "miniFrankenBear": (80,  80),
    "snake":          (220, 100),
    "monkeyMummy":    (180, 180),
    "lion":           (250, 170),
}

BEAR_W = 80
BEAR_H = 100


def scale_image_to_box(img, target_w, target_h):
    """Scale img so height == target_h preserving aspect ratio,
    then crop (centred) or pad width to target_w.
    Returns a surface of exactly (target_w, target_h)."""
    iw, ih = img.get_size()
    scale = target_h / ih
    nw = max(1, int(iw * scale))
    scaled = pygame.transform.scale(img, (nw, target_h))
    surf = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
    if nw >= target_w:
        ox = (nw - target_w) // 2
        surf.blit(scaled, (0, 0), (ox, 0, target_w, target_h))
    else:
        ox = (target_w - nw) // 2
        surf.blit(scaled, (ox, 0))
    return surf


def create_outline_surface(sprite, color=(255, 255, 255, 220)):
    """Return a surface with a white outline matching the sprite's silhouette."""
    mask = pygame.mask.from_surface(sprite)
    w, h = sprite.get_size()
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    white_fill = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2),
                   (-2, -2), (2, -2), (-2, 2), (2, 2)):
        out.blit(white_fill, (dx, dy))
    return out


def get_position_relative_to_monster(bearXPosition, bearYPosition, mummyXPosition,
                              mummyYPosition):
    if ((bearXPosition > mummyXPosition
         and bearXPosition < mummyXPosition + 100)
            and bearYPosition < mummyYPosition):
        return "TOP"
    elif (bearXPosition < mummyXPosition and bearYPosition <= mummyYPosition):
        return "LEFT"
    elif (bearXPosition > mummyXPosition and bearYPosition <= mummyYPosition):
        return "RIGHT"


def is_bear_hurt(positionRelative, bearXPosition, bearYPosition,
               objectXPosition, objectYPosition, objectName):
    """Return True if the bear's hitbox overlaps with the named object."""
    if objectName not in _MONSTER_SIZES:
        return False
    width, height = _MONSTER_SIZES[objectName]
    bear_rect = pygame.Rect(bearXPosition + 5, bearYPosition + 5,
                            BEAR_W - 10, BEAR_H - 10)
    obj_rect = pygame.Rect(objectXPosition, objectYPosition, width, height)
    return bear_rect.colliderect(obj_rect)


def is_monster_hurt(bearXPosition, bearYPosition, mummyXPosition, mummyYPosition,
                  facingLeft, monsterType):
    """Return True if the bear's attack hitbox overlaps with the monster."""
    if monsterType == "frankenbears":
        m_w, m_h = 300, 300
    elif monsterType == "bigMummy":
        m_w, m_h = 200, 300
    elif monsterType == "miniFrankenBear":
        m_w, m_h = 80, 80
    elif monsterType == "shadowShaman":
        m_w, m_h = 120, 120
    else:
        m_w, m_h = 100, 100

    monster_rect = pygame.Rect(mummyXPosition, mummyYPosition, m_w, m_h)

    # Attack reach mirrors the attack-sprite widths (190 right / 180 left)
    if not facingLeft:
        attack_rect = pygame.Rect(bearXPosition, bearYPosition + 10, 190, 80)
    else:
        attack_rect = pygame.Rect(bearXPosition - 180, bearYPosition + 10,
                                  180, 80)
    return attack_rect.colliderect(monster_rect)


def is_monster_forehead_hit(bearXPosition, bearYPosition, mummyXPosition,
                         mummyYPosition, facingLeft):
    """Return True only if the attack hits the big mummy's forehead (top 30%)."""
    # Forehead zone scaled for 260x360 sprite: 52px inset, 156px wide, 108px tall
    forehead_rect = pygame.Rect(mummyXPosition + 52, mummyYPosition, 156, 108)
    if not facingLeft:
        attack_rect = pygame.Rect(bearXPosition, bearYPosition + 10, 190, 80)
    else:
        attack_rect = pygame.Rect(bearXPosition - 180, bearYPosition + 10,
                                  180, 80)
    return attack_rect.colliderect(forehead_rect)


# ---------------------------------------------------------------------------
# Damage text helper – drawn once instead of duplicated across every class
# ---------------------------------------------------------------------------
def render_damage_text(screen, font, damage, x, y, alpha=255):
    """Render damage text with an outlined style and optional alpha fade.
    Uses italic fonts (set in _init_fonts) for cursive look.
    alpha: 0-255 for transparency.
    """
    txt = str(damage)
    # base surfaces
    col_black = (0, 0, 0)
    col_white = (255, 255, 255)
    # Create a temp surface sized for outline offsets
    w, h = font.size(txt)
    pad = 6
    surf = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    # draw outline by blitting black text at offsets
    outline_surf = font.render(txt, True, col_black)
    ox = pad
    oy = pad
    for dx, dy in ((-2, -2), (2, -2), (2, 2), (-2, 2)):
        surf.blit(outline_surf, (ox + dx, oy + dy))
    # draw main white text
    main_surf = font.render(txt, True, col_white)
    surf.blit(main_surf, (ox, oy))
    # apply alpha
    if alpha < 255:
        surf.set_alpha(alpha)
    # blit at provided x,y (use x,y as top-left of original text)
    screen.blit(surf, (x - pad, y - pad))


def render_water(screen, offset):
    """Animated scrolling stream drawn just below the floor (y=400)."""
    pygame.draw.rect(screen, (15, 70, 190), (0, 534, 900, 166))
    bands = [
        (520, (15,  70, 190)),
        (532, (35, 115, 225)),
        (544, (70, 165, 255)),
        (556, (110, 190, 255)),
    ]
    for band_idx, (y_base, color) in enumerate(bands):
        scroll = (offset * (band_idx + 1)) % 60
        for x_start in range(-60 + scroll, 960, 60):
            pygame.draw.ellipse(screen, color, (x_start - 30, y_base, 60, 14))
    pygame.draw.line(screen, (130, 200, 255), (0, 518), (900, 518), 2)


# ---------------------------------------------------------------------------
# Main game class
# ---------------------------------------------------------------------------

class mainGame:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.thud_sound = pygame.mixer.Sound("Game/Sounds/thud.wav")
            self.thud_sound.set_volume(1.0)
            self.jump_scream_sound = pygame.mixer.Sound("Game/Sounds/jump_yell.wav")
            self.jump_scream_sound.set_volume(0.85)
            self.water_sound = pygame.mixer.Sound("Game/Sounds/water_ambient.wav")
            self.water_sound.set_volume(0.30)
            pygame.mixer.music.load("Game/Sounds/spooky_peaceful.wav")
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)   # loop forever
            import array as _arr, random as _rnd
            _RATE = 44100
            _n = int(_RATE * 0.18)
            _buf = _arr.array('h')
            for _i in range(_n):
                _env = (1.0 - _i / _n) ** 0.6
                _val = int(_env * _rnd.randint(-32767, 32767) * 0.55)
                _val = max(-32767, min(32767, _val))
                _buf.append(_val)
                _buf.append(_val)
            self.fire_sound = pygame.mixer.Sound(buffer=_buf)
            self.fire_sound.set_volume(0.35)
            _RATE2 = 44100
            _n2 = int(_RATE2 * 0.25)
            _buf2 = _arr.array('h')
            import math as _fsm
            for _i2 in range(_n2):
                _t2 = _i2 / _RATE2
                _env2 = (1.0 - _i2 / _n2) ** 0.4
                _wave = _fsm.sin(2 * _fsm.pi * 600 * _t2) * 0.3
                _wave += _fsm.sin(2 * _fsm.pi * 1200 * _t2 * (1 - _t2)) * 0.25
                _wave += _rnd.randint(-32767, 32767) / 32767.0 * 0.45
                _val2 = int(_env2 * _wave * 32000)
                _val2 = max(-32767, min(32767, _val2))
                _buf2.append(_val2)
                _buf2.append(_val2)
            self.fire_sound_silver = pygame.mixer.Sound(buffer=_buf2)
            self.fire_sound_silver.set_volume(0.40)

            def _make_snd(samples):
                _b = _arr.array('h')
                for _s in samples:
                    _v = max(-32767, min(32767, int(_s * 32767)))
                    _b.append(_v); _b.append(_v)
                return pygame.mixer.Sound(buffer=_b)

            import math as _math

            # ── Attack yell: rising then falling voiced "YAH!" ──────────
            _n = int(_RATE * 0.21)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _f = (350 + 200*(_t/0.05)) if _t < 0.05 else (550 - 270*((_t-0.05)/0.16))
                _s = (_math.sin(2*_math.pi*_f*_t)*0.50
                      + _math.sin(2*_math.pi*_f*2*_t)*0.20
                      + _math.sin(2*_math.pi*_f*3*_t)*0.10
                      + _rnd.gauss(0, 0.12))
                _env = min(_i/(_RATE*0.018), 1.0, (_n-_i)/(_RATE*0.055))
                _smp.append(_s * _env * 0.48)
            self.attack_sound = _make_snd(_smp)
            self.attack_sound.set_volume(0.60)

            # ── Grunt: descending voiced "UGH!" when player is hit ──────
            _n = int(_RATE * 0.24)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _f = 310 - 130*(_t/0.24)
                _s = (_math.sin(2*_math.pi*_f*_t)*0.55
                      + _math.sin(2*_math.pi*_f*2*_t)*0.28
                      + _rnd.gauss(0, 0.18))
                _env = min(_i/(_RATE*0.015), 1.0, (_n-_i)/(_RATE*0.08))
                _smp.append(_s * _env * 0.45)
            self.grunt_sound = _make_snd(_smp)
            self.grunt_sound.set_volume(0.70)

            # ── Hit thwack: sharp percussive impact on enemy ─────────────
            _n = int(_RATE * 0.11)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _env = (1.0 - _i/_n)**1.8
                _s = (_rnd.gauss(0, 1)*0.75
                      + _math.sin(2*_math.pi*180*_t)*0.35
                      + _math.sin(2*_math.pi*360*_t)*0.15)
                _smp.append(_s * _env * 0.65)
            self.hit_sound = _make_snd(_smp)
            self.hit_sound.set_volume(0.75)

            _n = int(_RATE * 0.9)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _env = max(0.0, (1.0 - _t / 0.9) ** 0.8)
                _initial_blast = max(0.0, 1.0 - _t * 10) * _rnd.gauss(0, 1) * 1.0
                _boom = (_math.sin(2*_math.pi*35*_t) * 1.0
                         + _math.sin(2*_math.pi*55*_t) * 0.7
                         + _math.sin(2*_math.pi*25*_t + _math.sin(2*_math.pi*5*_t)*5) * 0.6
                         + _math.sin(2*_math.pi*90*_t) * 0.4
                         + _math.sin(2*_math.pi*15*_t) * 0.5)
                _crackle = _rnd.gauss(0, 0.7) * max(0.0, 1.0 - _t * 3) * 0.7
                _rumble_env = min(1.0, _t * 5) * max(0.0, 1.0 - (_t - 0.25) * 1.5)
                _rumble = _math.sin(2*_math.pi*20*_t) * _rumble_env * 1.0
                _s = (_initial_blast + _boom * _env + _crackle + _rumble)
                _smp.append(max(-1.0, min(1.0, _s)))
            self.explosion_sound = _make_snd(_smp)
            self.explosion_sound.set_volume(0.85)
            
            self.fireball_sound = pygame.mixer.Sound("Game/Sounds/fireball.wav")
            self.fireball_sound.set_volume(0.50)
            self.blob_jump_sound = pygame.mixer.Sound("Game/Sounds/blob_jump.wav")
            self.blob_jump_sound.set_volume(0.50)
            self.footstep_sound = pygame.mixer.Sound("Game/Sounds/footstep.wav")
            self.footstep_sound.set_volume(0.55)
            self.door_open_sound = pygame.mixer.Sound("Game/Sounds/door_open.wav")
            self.door_open_sound.set_volume(0.60)
            self.key_pickup_sound = pygame.mixer.Sound("Game/Sounds/key_pickup.wav")
            self.key_pickup_sound.set_volume(0.65)
            self.level_up_sound = pygame.mixer.Sound("Game/Sounds/level_up.wav")
            self.level_up_sound.set_volume(0.70)
            self.shop_open_sound = pygame.mixer.Sound("Game/Sounds/shop_open.wav")
            self.shop_open_sound.set_volume(0.65)
            self.shop_close_sound = pygame.mixer.Sound("Game/Sounds/shop_close.wav")
            self.shop_close_sound.set_volume(0.60)
            self.shop_navigate_sound = pygame.mixer.Sound("Game/Sounds/shop_navigate.wav")
            self.shop_navigate_sound.set_volume(0.50)
            self.shop_buy_sound = pygame.mixer.Sound("Game/Sounds/shop_buy.wav")
            self.shop_buy_sound.set_volume(0.75)
            self.shop_error_sound = pygame.mixer.Sound("Game/Sounds/shop_error.wav")
            self.shop_error_sound.set_volume(0.60)
            self.boss_entrance_sound = pygame.mixer.Sound("Game/Sounds/boss_entrance.wav")
            self.boss_entrance_sound.set_volume(0.55)
            self.deflect_sound = pygame.mixer.Sound("Game/Sounds/deflect.wav")
            self.deflect_sound.set_volume(0.55)
            self.spike_hit_sound = pygame.mixer.Sound("Game/Sounds/spike_hit.wav")
            self.spike_hit_sound.set_volume(0.50)
            self.mummy_groan_sound = pygame.mixer.Sound("Game/Sounds/mummy_groan.wav")
            self.mummy_groan_sound.set_volume(0.25)
            self.laser_zap_sound = pygame.mixer.Sound("Game/Sounds/laser_zap.wav")
            self.laser_zap_sound.set_volume(0.45)
            self.boss_hit_sound = pygame.mixer.Sound("Game/Sounds/boss_hit.wav")
            self.boss_hit_sound.set_volume(0.65)

            self.monkey_screech_sound = pygame.mixer.Sound("Game/Sounds/monkey_screech.wav")
            self.monkey_screech_sound.set_volume(0.35)
            self.lion_roar_sound = pygame.mixer.Sound("Game/Sounds/lion_roar.wav")
            self.lion_roar_sound.set_volume(0.45)

            _n = int(_RATE * 0.30)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _env = max(0.0, (1.0 - _t/0.30)**1.5)
                _s = (_math.sin(2*_math.pi*180*_t) * 0.5
                      + _math.sin(2*_math.pi*360*_t) * 0.3
                      + _math.sin(2*_math.pi*90*_t) * 0.4
                      + _rnd.gauss(0, 0.15) * max(0, 1.0 - _t*8))
                _smp.append(max(-1.0, min(1.0, _s * _env * 0.90)))
            self.crit_sound = _make_snd(_smp)
            self.crit_sound.set_volume(0.85)

            _n = int(_RATE * 0.45)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _env = max(0.0, (1.0 - _t/0.45)**1.2)
                _s = (_math.sin(2*_math.pi*200*_t) * 0.6
                      + _math.sin(2*_math.pi*400*_t) * 0.3
                      + _math.sin(2*_math.pi*100*_t) * 0.35
                      + _math.sin(2*_math.pi*800*_t) * 0.15 * max(0, 1.0 - _t*5))
                _smp.append(max(-1.0, min(1.0, _s * _env * 0.85)))
            self.beam_sound = _make_snd(_smp)
            self.beam_sound.set_volume(0.80)

            # ── Coin collect: bright two-tone metallic ding ────────────────
            _n = int(_RATE * 0.38)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                # Two tones: root + fifth (880 Hz + 1320 Hz)
                _tone1 = _math.sin(2 * _math.pi * 880 * _t)
                _tone2 = _math.sin(2 * _math.pi * 1320 * _t) * 0.65
                # Add shimmer harmonics
                _tone3 = _math.sin(2 * _math.pi * 1760 * _t) * 0.25
                _tone4 = _math.sin(2 * _math.pi * 2640 * _t) * 0.12
                # Sharp attack, exponential decay
                _env = (min(1.0, _i / (_RATE * 0.003))  # 3 ms attack
                        * _math.exp(-_t * 7.5))           # decay
                _smp.append(max(-1.0, min(1.0, (_tone1 + _tone2 + _tone3 + _tone4) * _env * 0.55)))
            self.coin_sound = _make_snd(_smp)
            self.coin_sound.set_volume(0.70)

            _n = int(_RATE * 2.0)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _env = max(0.0, (1.0 - _t / 2.0) ** 0.5)
                _initial_blast = max(0.0, 1.0 - _t * 6) * _rnd.gauss(0, 1) * 1.2
                _boom = (_math.sin(2*_math.pi*28*_t) * 1.2
                         + _math.sin(2*_math.pi*45*_t) * 0.9
                         + _math.sin(2*_math.pi*18*_t + _math.sin(2*_math.pi*3*_t)*6) * 0.8
                         + _math.sin(2*_math.pi*70*_t) * 0.5
                         + _math.sin(2*_math.pi*12*_t) * 0.7)
                _crackle = _rnd.gauss(0, 0.8) * max(0.0, 1.0 - _t * 2) * 0.8
                _rumble_env = min(1.0, _t * 3) * max(0.0, 1.0 - (_t - 0.5) * 1.0)
                _rumble = _math.sin(2*_math.pi*15*_t) * _rumble_env * 1.2
                _s = (_initial_blast + _boom * _env + _crackle + _rumble)
                _smp.append(max(-1.0, min(1.0, _s)))
            self.boss_explosion_sound = _make_snd(_smp)
            self.boss_explosion_sound.set_volume(1.0)

            _n = int(_RATE * 0.15)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _env = max(0.0, (1.0 - _t/0.15)**2.0)
                _s = _math.sin(2*_math.pi*600*_t) * 0.4 + _rnd.gauss(0, 0.3)
                _smp.append(max(-1.0, min(1.0, _s * _env * 0.6)))
            self.enemy_hit_sound = _make_snd(_smp)
            self.enemy_hit_sound.set_volume(0.45)

            _n = int(_RATE * 0.6)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _env = min(1.0, _i / (_RATE * 0.01)) * max(0.0, (1.0 - _t/0.6)**1.0)
                _freq = 300 + 500 * _t
                _s = _math.sin(2*_math.pi*_freq*_t) * 0.5 + _math.sin(2*_math.pi*(_freq*1.5)*_t) * 0.25
                _smp.append(max(-1.0, min(1.0, _s * _env * 0.5)))
            self.wave_warning_sound = _make_snd(_smp)
            self.wave_warning_sound.set_volume(0.55)

            _n = int(_RATE * 0.25)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _env = max(0.0, (1.0 - _t/0.25)**1.5)
                _s = (_math.sin(2*_math.pi*120*_t) * 0.6
                      + _math.sin(2*_math.pi*240*_t) * 0.3
                      + _rnd.gauss(0, 0.2))
                _smp.append(max(-1.0, min(1.0, _s * _env * 0.7)))
            self.bear_hurt_sound = _make_snd(_smp)
            self.bear_hurt_sound.set_volume(0.55)

            _n = int(_RATE * 0.35)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _env = min(1.0, _i / (_RATE * 0.005)) * max(0.0, (1.0 - _t/0.35)**1.2)
                _f1 = 523.25
                _f2 = 659.25
                _s = (_math.sin(2*_math.pi*_f1*_t) * 0.5
                      + _math.sin(2*_math.pi*_f2*_t) * 0.35
                      + _math.sin(2*_math.pi*_f1*2*_t) * 0.15)
                _smp.append(max(-1.0, min(1.0, _s * _env * 0.5)))
            self.enemy_spawn_sound = _make_snd(_smp)
            self.enemy_spawn_sound.set_volume(0.35)

            _n = int(_RATE * 0.18)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _f = 180 - 80 * (_t / 0.18)
                _s = (_math.sin(2*_math.pi*_f*_t) * 0.4
                      + _math.sin(2*_math.pi*_f*1.5*_t) * 0.2
                      + _rnd.gauss(0, 0.08))
                _env = min(_i/(_RATE*0.01), 1.0) * ((1.0 - _t/0.18) ** 1.5)
                _smp.append(max(-1.0, min(1.0, _s * _env * 0.5)))
            self.mummy_jump_sound = _make_snd(_smp)
            self.mummy_jump_sound.set_volume(0.20)

            _n = int(_RATE * 0.22)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _f = 500 + 300 * _math.sin(2*_math.pi*8*_t)
                _s = (_math.sin(2*_math.pi*_f*_t) * 0.35
                      + _math.sin(2*_math.pi*_f*2*_t) * 0.15
                      + _rnd.gauss(0, 0.15))
                _env = min(_i/(_RATE*0.01), 1.0) * ((1.0 - _t/0.22) ** 1.2)
                _smp.append(max(-1.0, min(1.0, _s * _env * 0.5)))
            self.witch_cast_sound = _make_snd(_smp)
            self.witch_cast_sound.set_volume(0.25)

            _n = int(_RATE * 0.45)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _f = 800 - 600 * (_t / 0.45)
                _s = (_math.sin(2*_math.pi*_f*_t) * 0.3
                      + _math.sin(2*_math.pi*_f*1.5*_t) * 0.15
                      + _math.sin(2*_math.pi*_f*0.5*_t) * 0.1)
                _env = min(_i/(_RATE*0.02), 1.0) * max(0.0, 1.0 - _t/0.45) ** 0.8
                _crackle = _rnd.gauss(0, 0.08) * (1.0 - _t/0.45)
                _smp.append(max(-1.0, min(1.0, (_s + _crackle) * _env * 0.6)))
            self.witch_beam_sound = _make_snd(_smp)
            self.witch_beam_sound.set_volume(0.30)

            _n = int(_RATE * 0.12)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _f = 250 + 150 * _t / 0.12
                _s = (_math.sin(2*_math.pi*_f*_t) * 0.3
                      + _rnd.gauss(0, 0.2))
                _env = min(_i/(_RATE*0.005), 1.0) * ((1.0 - _t/0.12) ** 2.0)
                _smp.append(max(-1.0, min(1.0, _s * _env * 0.45)))
            self.fireball_bounce_sound = _make_snd(_smp)
            self.fireball_bounce_sound.set_volume(0.18)

            pygame.mixer.set_num_channels(20)

            try:
                self._ambient_sound = pygame.mixer.Sound("Game/Sounds/spooky_peaceful.wav")
                self._ambient_channel = pygame.mixer.Channel(18)
            except Exception:
                self._ambient_sound = None
                self._ambient_channel = None

            _LOOP_LEN = 4.0
            _LN = int(_RATE * _LOOP_LEN)

            _smp = []
            for _i in range(_LN):
                _t = _i / _RATE
                _beat = _math.fmod(_t, 0.55)
                _pulse = _math.exp(-_beat * 12) * _math.sin(2*_math.pi*42*_t) * 0.7
                _pulse += _math.exp(-_beat * 8) * _math.sin(2*_math.pi*63*_t) * 0.3
                _smp.append(max(-1.0, min(1.0, _pulse)))
            self._layer_heartbeat = _make_snd(_smp)

            _smp = []
            for _i in range(_LN):
                _t = _i / _RATE
                _vib = _math.sin(2*_math.pi*5.5*_t) * 8
                _s = (_math.sin(2*_math.pi*(196+_vib)*_t) * 0.35
                      + _math.sin(2*_math.pi*(294+_vib)*_t) * 0.25
                      + _math.sin(2*_math.pi*(370+_vib)*_t) * 0.15
                      + _rnd.gauss(0, 0.04))
                _fade = min(1.0, _i/(_RATE*0.3)) * min(1.0, (_LN-_i)/(_RATE*0.3))
                _smp.append(max(-1.0, min(1.0, _s * _fade * 0.5)))
            self._layer_strings = _make_snd(_smp)

            _smp = []
            for _i in range(_LN):
                _t = _i / _RATE
                _beat_pos = _math.fmod(_t, 0.4)
                _sub = _math.fmod(_t, 0.2)
                _kick = _math.exp(-_beat_pos*18) * _math.sin(2*_math.pi*55*_t) * 0.6
                _snare = _math.exp(-max(0,_sub-0.1)*30) * _rnd.gauss(0, 0.4) * (1 if _sub > 0.1 else 0)
                _tom = _math.exp(-_beat_pos*10) * _math.sin(2*_math.pi*90*_t) * 0.3
                _smp.append(max(-1.0, min(1.0, _kick + _snare + _tom)))
            self._layer_drums = _make_snd(_smp)

            _smp = []
            for _i in range(_LN):
                _t = _i / _RATE
                _slow = _math.sin(2*_math.pi*0.25*_t)
                _s = (_math.sin(2*_math.pi*220*_t) * 0.25
                      + _math.sin(2*_math.pi*330*_t) * 0.20
                      + _math.sin(2*_math.pi*440*_t) * 0.12
                      + _math.sin(2*_math.pi*277*_t) * 0.15)
                _fade = min(1.0, _i/(_RATE*0.5)) * min(1.0, (_LN-_i)/(_RATE*0.5))
                _smp.append(max(-1.0, min(1.0, _s * _fade * (0.4 + 0.15*_slow))))
            self._layer_choir = _make_snd(_smp)

            _smp = []
            _bell_freqs = [523, 659, 784, 1047]
            for _i in range(_LN):
                _t = _i / _RATE
                _beat = _math.fmod(_t, 1.0)
                _bell_idx = int(_t) % len(_bell_freqs)
                _f = _bell_freqs[_bell_idx]
                _strike = _math.exp(-_beat * 6.0)
                _s = (_math.sin(2*_math.pi*_f*_t) * 0.35 * _strike
                      + _math.sin(2*_math.pi*_f*2.0*_t) * 0.15 * _strike
                      + _math.sin(2*_math.pi*_f*3.0*_t) * 0.08 * _strike)
                _fade = min(1.0, _i/(_RATE*0.3)) * min(1.0, (_LN-_i)/(_RATE*0.3))
                _smp.append(max(-1.0, min(1.0, _s * _fade * 0.45)))
            self._layer_bells = _make_snd(_smp)

            _smp = []
            for _i in range(_LN):
                _t = _i / _RATE
                _vib = 5.5 * _math.sin(2*_math.pi*5.8*_t)
                _bow = min(1.0, _i/(_RATE*0.08)) * (0.7 + 0.3*_math.sin(2*_math.pi*0.4*_t))
                _s = (_math.sin(2*_math.pi*(440+_vib)*_t) * 0.30
                      + _math.sin(2*_math.pi*(880+_vib*2)*_t) * 0.18
                      + _math.sin(2*_math.pi*(1320+_vib*3)*_t) * 0.10
                      + _math.sin(2*_math.pi*(1760+_vib*4)*_t) * 0.05
                      + _rnd.gauss(0, 0.015))
                _fade = min(1.0, _i/(_RATE*0.4)) * min(1.0, (_LN-_i)/(_RATE*0.4))
                _smp.append(max(-1.0, min(1.0, _s * _fade * _bow * 0.55)))
            self._layer_violin = _make_snd(_smp)

            self._tension_layers = [
                {'sound': self._layer_heartbeat, 'channel': pygame.mixer.Channel(12),
                 'threshold': 500,  'max_vol': 0.18, 'current_vol': 0.0, 'active': False},
                {'sound': self._layer_strings,   'channel': pygame.mixer.Channel(13),
                 'threshold': 2000, 'max_vol': 0.14, 'current_vol': 0.0, 'active': False},
                {'sound': self._layer_drums,     'channel': pygame.mixer.Channel(14),
                 'threshold': 4000, 'max_vol': 0.16, 'current_vol': 0.0, 'active': False},
                {'sound': self._layer_choir,     'channel': pygame.mixer.Channel(15),
                 'threshold': 8000, 'max_vol': 0.13, 'current_vol': 0.0, 'active': False},
                {'sound': self._layer_violin,    'channel': pygame.mixer.Channel(17),
                 'threshold': 36000, 'max_vol': 0.15, 'current_vol': 0.0, 'active': False},
                {'sound': self._layer_bells,     'channel': pygame.mixer.Channel(16),
                 'threshold': 30000, 'max_vol': 0.12, 'current_vol': 0.0, 'active': False},
            ]
            self._tension_layers_ready = True

        except Exception:
            self.thud_sound = None
            self.fire_sound = None
            self.fire_sound_silver = None
            self.attack_sound = None
            self.grunt_sound  = None
            self.hit_sound    = None
            self.explosion_sound = None
            self.fireball_sound = None
            self.blob_jump_sound = None
            self.water_sound = None
            self.footstep_sound = None
            self.door_open_sound = None
            self.key_pickup_sound = None
            self.level_up_sound = None
            self.shop_open_sound = None
            self.shop_close_sound = None
            self.shop_navigate_sound = None
            self.shop_buy_sound = None
            self.shop_error_sound = None
            self.boss_entrance_sound = None
            self.deflect_sound = None
            self.spike_hit_sound = None
            self.mummy_groan_sound = None
            self.laser_zap_sound = None
            self.boss_hit_sound = None
            self.crit_sound = None
            self.beam_sound = None
            self.coin_sound = None
            self.boss_explosion_sound = None
            self.enemy_hit_sound = None
            self.wave_warning_sound = None
            self.bear_hurt_sound = None
            self.enemy_spawn_sound = None
            self.monkey_screech_sound = None
            self.lion_roar_sound = None
            self.mummy_jump_sound = None
            self.witch_cast_sound = None
            self.witch_beam_sound = None
            self.fireball_bounce_sound = None
            self._tension_layers = []
            self._tension_layers_ready = False
        init_fonts()

        self.screen = pygame.display.set_mode((900, 700), pygame.DOUBLEBUF)
        self.clock = pygame.time.Clock()

        self.standingBear = pygame.image.load("Game/Images/Bear/standBear2.png")
        self.standingBear = pygame.transform.scale(self.standingBear, (105, 100))
        self.standingBearLeft = pygame.transform.flip(self.standingBear, True, False)
        self.standingBearBlink = self.standingBear.copy()
        pygame.draw.rect(self.standingBearBlink, (40, 30, 20), (28, 22, 50, 8), border_radius=4)
        self.standingBearLeftBlink = self.standingBearLeft.copy()
        pygame.draw.rect(self.standingBearLeftBlink, (40, 30, 20), (28, 22, 50, 8), border_radius=4)

        # Create crouch sprite by scaling standing bear to crouch pose
        self.crouchBear = pygame.transform.scale(self.standingBear, (105, 65))
        self.crouchBearLeft = pygame.transform.flip(self.crouchBear, True, False)

        self.bearWalking1 = pygame.image.load("Game/Images/Bear/bearWalking1.png")
        self.bearWalking1 = pygame.transform.scale(self.bearWalking1, (120, 115))
        self.bearWalking2 = pygame.image.load("Game/Images/Bear/bearWalking2.png")
        self.bearWalking2 = pygame.transform.scale(self.bearWalking2, (120, 115))
        self.bearWalking3 = pygame.image.load("Game/Images/Bear/bearWalking3.png")
        self.bearWalking3 = pygame.transform.scale(self.bearWalking3, (120, 115))
        self.bearWalking4 = pygame.image.load("Game/Images/Bear/bearWalking4.png")
        self.bearWalking4 = pygame.transform.scale(self.bearWalking4, (120, 115))

        self.screen.fill((255, 255, 255))
        pygame.display.update()

        self.bearWalkingLeft1 = pygame.transform.flip(self.bearWalking1, True, False)
        self.bearWalkingLeft2 = pygame.transform.flip(self.bearWalking2, True, False)
        self.bearWalkingLeft3 = pygame.transform.flip(self.bearWalking3, True, False)
        self.bearWalkingLeft4 = pygame.transform.flip(self.bearWalking4, True, False)

        self._precompute_walk_lean()

        self.bearAttacking = pygame.image.load("Game/Images/Bear/bearAttacking.png")
        self.bearAttacking = pygame.transform.scale(self.bearAttacking, (210, 105))
        self.bearAttackingLeft = pygame.transform.flip(
            pygame.image.load("Game/Images/Bear/bearAttacking.png"), True, False)
        self.bearAttackingLeft = pygame.transform.scale(self.bearAttackingLeft, (200, 105))

        self.hurtBear = pygame.image.load("Game/Images/Bear/hurtBear.png")
        self.hurtBear = pygame.transform.scale(self.hurtBear, (150, 105))

        self.mummy1 = pygame.image.load("Game/Images/Mummy/mummy1.png")
        self.mummy2 = pygame.image.load("Game/Images/Mummy/mummy2.png")
        self.deflectIcon = pygame.image.load("Game/Images/deflect.png")
        self.deflectIcon = pygame.transform.scale(self.deflectIcon, (60, 60))
        self.witch = pygame.image.load("Game/Images/Bear/witch.png")
        self.witch2 = pygame.image.load("Game/Images/Bear/witch2.png")
        self.pillar = pygame.image.load('Game/Images/cobstone.png')
        self.pillar = pygame.transform.scale(self.pillar, (100, 900))

        self.bossFires = []
        self.mummys = []
        self.fires = []
        self.playerFires = []
        self.greenBlobs = []
        self.witches = []
        self.shadowShamans = []
        self.blocks = []
        self.frankenbear = []
        self.miniFrankenBears = []
        self.lasers = []
        self.waterfalls = []
        self.snakes = []
        self.venom_balls = []
        self.lions = []
        self.coins = []
        self.destroyable_blocks = []
        self.active_weapon = None
        self.weapon_cooldown = 0
        self._secret_attack_unlocked = False
        self.lightning_cooldown = 0
        self.lightning_charge = 0.0
        self.lightning_anim = 0
        self.lightning_x = 0
        self.lightning2_targets = []
        self.lightning2_cooldown = 0
        self.monkey_mummies = []
        self.bombs = []
        self._bomb_spawn_timer = 0
        self.heart_drops = []
        self.shaman_orbs = []
        self._shaman_orb_timer = 0
        self.witch_beams = []

        self.fireBall = pygame.image.load("Game/Images/fire3.png")
        self.fireBossBall = pygame.image.load("Game/Images/fire4.png")

        # Distinct player-fireball surfaces for each level tier
        def _fireball_surf(outer, mid, core=(255, 255, 255), size=50):
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            c = size // 2
            pygame.draw.circle(s, outer + (240,), (c, c), size // 2 - 1)
            pygame.draw.circle(s, mid + (255,), (c, c), size // 3)
            pygame.draw.circle(s, core + (220,), (c, c), size // 6)
            return s
        self.fireballYellow = _fireball_surf((220, 200,   0), (255, 255,  80))
        self.fireballGreen  = _fireball_surf((  0, 160,  30), ( 80, 255, 100))
        self.fireballBlue   = _fireball_surf((  0,  80, 220), ( 80, 180, 255))
        self.fireballGold   = _fireball_surf((255, 215,   0), (255, 255, 100))
        import math as _math
        _rb = pygame.Surface((50, 50), pygame.SRCALPHA)
        _cx, _cy = 25, 25
        for _ang in range(360):
            _rad = _math.radians(_ang)
            _r = int(127.5 * (1 + _math.sin(_rad)))
            _g = int(127.5 * (1 + _math.sin(_rad + 2.094)))
            _b = int(127.5 * (1 + _math.sin(_rad + 4.189)))
            _px = _cx + int(20 * _math.cos(_rad))
            _py = _cy + int(20 * _math.sin(_rad))
            pygame.draw.circle(_rb, (_r, _g, _b, 255), (_px, _py), 7)
        pygame.draw.circle(_rb, (255, 255, 255, 220), (_cx, _cy), 8)
        self.fireballRainbow = _rb

        _sv = pygame.Surface((50, 50), pygame.SRCALPHA)
        pygame.draw.circle(_sv, (180, 190, 210, 200), (25, 25), 24)
        pygame.draw.circle(_sv, (210, 220, 235, 240), (25, 25), 18)
        pygame.draw.circle(_sv, (240, 245, 255, 255), (25, 25), 12)
        pygame.draw.circle(_sv, (255, 255, 255, 255), (25, 25), 6)
        pygame.draw.circle(_sv, (255, 255, 255, 120), (18, 14), 8)
        pygame.draw.circle(_sv, (255, 255, 255, 80), (33, 20), 5)
        for _sa in range(0, 360, 45):
            _sr = _math.radians(_sa)
            _sx = 25 + int(21 * _math.cos(_sr))
            _sy = 25 + int(21 * _math.sin(_sr))
            pygame.draw.circle(_sv, (255, 255, 255, 100), (_sx, _sy), 4)
        self.fireballSilver = _sv

        self.screen.fill((255, 255, 255))
        pygame.display.update()

        self.showBoss = True
        self.triggerText1 = False
        self.triggerText2 = False
        self.triggerText3 = False
        self.triggerText4 = False
        self.triggerText5 = False
        self.createdBoss = False
        self.doorPopupTriggered = False
        self.leftBoundary = 180
        self.rightBoundary = 300
        self.isFinalBossDestroyed = False
        self.newGamePlusLevel = 0
        self._water_playing = False
        self._silver_applied = False
        self._bigMummyDefeated = False
        self._ambient_channel = None
        self._ambient_sound = None
        self._ambient_playing = False
        self._hard_mode_selected = False
        self._hms_pre_boss_applied = False
        self._hms_post_boss_applied = False
        self._hardMode = False
        self._hardMode75 = False
        self.beamProjectiles = []
        self.checkpoint_file = os.path.join('Game', 'checkpoint.json')
        self._checkpoint_saved = False
        self._checkpoint_used = False
        self._checkpoint_data = None
        self._easter_egg_42 = False
        self._easter_egg_13 = False
        self._easter_egg_5555 = False
        self._jungle_unlocked = False
        self._monkey_level_active = False
        self._jungle_zone2_active = False
        self._triggerJungleTransition = False
        self._triggerNewGamePlus = False
        self._intro_shown = False
        self._100_coin_milestone = False
        self._last_coin_milestone = 0
        self._first_coin_popup_shown = False
        self._critical_hp_popup_shown = False
        self._beam_ever_shown = False
        self._post_boss_platform_popup_shown = False
        self._boss_door_passed = False
        self._poison_floats = []   # [{x, y, timer}] floating "-2" numbers while poisoned

    # -----------------------------------------------------------------------
    def _clear_poison(self, bear):
        bear.poison_timer = 0
        bear.poison_damage_tick = 0
        self._poison_floats = []

    _ZONE_THRESHOLDS = [
        (2500,  11),
        (5000,   1),
        (8000,  14),
        (11000, 10),
        (14500,  3),
        (18500,  2),
        (22000, 13),
        (25500,  4),
        (29000, 12),
        (34000,  5),
        (36500, -1),
        (39500,  6),
        (45000,  7),
        (50500,  8),
        (53500, -2),
        (56500, 15),
        (60000,  9),
    ]

    def _find_zone_restart(self, dist):
        restart_at = 0
        for threshold, _ in self._ZONE_THRESHOLDS:
            if dist >= threshold:
                restart_at = threshold
            else:
                break
        return restart_at

    def _save_checkpoint(self, backgroundScrollX, totalDistance, bear):
        self._checkpoint_saved = True
        self._checkpoint_used = False
        self._checkpoint_data = {
            'hp': bear.getHp(),
            'max_hp': bear.getMaxHp(),
            'exp': bear.getCurrentExp(),
            'level': bear.getLevel(),
            'coins': bear.getCoins(),
            'damageAttack': bear.getDamageAttack(),
            'has_shield': getattr(bear, 'has_shield', False),
            'has_aimer': getattr(bear, 'has_aimer', False),
            'has_50pct_protection': getattr(bear, 'has_50pct_protection', False),
            'has_lightning': getattr(bear, 'has_lightning', False),
            'has_lightning_2': getattr(bear, 'has_lightning_2', False),
            'has_big_fireball': getattr(bear, 'has_big_fireball', False),
            'totalDistance': totalDistance,
            'backgroundScrollX': backgroundScrollX,
            'hardMode': getattr(self, '_hardMode', False),
            'hardMode75': getattr(self, '_hardMode75', False),
            'hardMode80': getattr(self, '_hardMode80', False),
        }
        try:
            with open(self.checkpoint_file, 'w') as _cf:
                json.dump(self._checkpoint_data, _cf)
        except Exception:
            pass

    def _restore_checkpoint(self, bear, background, totalDistance):
        if not getattr(self, '_checkpoint_saved', False) or not self._checkpoint_data:
            return totalDistance, background.getBackgroundX()
        checkpoint = self._checkpoint_data
        saved_distance = checkpoint.get('totalDistance', totalDistance)

        zone_start = self._find_zone_restart(saved_distance)
        restart_dist = max(0, zone_start - 100)

        self.mummys = []; self.witches = []; self.greenBlobs = []
        self.fires = []; self.playerFires = []; self.bossFires = []
        self.shadowShamans = []; self.miniFrankenBears = []; self.lasers = []
        self.snakes = []; self.monkey_mummies = []; self.lions = []
        self.coins = []; self.blocks = []; self.destroyable_blocks = []
        self.beamProjectiles = []; self.waterfalls = []
        self.spikes = []; self.door = []; self.keys = []
        self.frankenbear = []; self.bombs = []; self._bomb_spawn_timer = 0
        self.heart_drops = []; self.shaman_orbs = []; self._shaman_orb_timer = 0
        self.witch_beams = []

        for i, (threshold, flag_idx) in enumerate(self._ZONE_THRESHOLDS):
            if threshold >= zone_start:
                if flag_idx >= 0 and flag_idx < len(self.activeMonsters):
                    self.activeMonsters[flag_idx] = False
                elif flag_idx == -1:
                    self._zone55_active = False
                elif flag_idx == -2:
                    self._zone85_active = False
        self._monkey_level_active = False
        self._jungle_zone2_active = False
        self._secret_box_spawned = False
        self.isDoor1Open = False
        self.doorPopupTriggered = False
        self._bigMummyDefeated = False
        self._stop_ambient_loop()
        self._boss_door_passed = False
        self.showBoss = True
        self.createdBoss = False
        self.bossTimerAnimation = 0
        self.leftBoundary = 180
        self.rightBoundary = 300
        if restart_dist > 5000:
            self.triggerText1 = True
            self.triggerText2 = True
            self.triggerText3 = True
        else:
            self.triggerText1 = (restart_dist > 2300)
            self.triggerText2 = False
            self.triggerText3 = False
        self.lightning_anim = 0
        self.lightning_cooldown = 0
        self.lightning2_targets = []
        if hasattr(self, '_bg_ref') and self._bg_ref:
            self._bg_ref.setStopBackground(False)
            self._bg_ref.setBlackBackground(False)
        if self.water_sound and getattr(self, '_water_playing', False):
            self.water_sound.stop()
            self._water_playing = False

        self.isFinalBossDestroyed = False
        self._triggerNewGamePlus = False
        self._triggerJungleTransition = False

        if hasattr(self, '_bg_ref') and self._bg_ref:
            self._bg_ref._jungle_mode = False
            self._bg_ref._black_latched = False

        self._current_music = None
        if restart_dist < 34000:
            self._switch_music("deep_crypt")
        elif restart_dist < 45000:
            self._switch_music("halfway")
        elif restart_dist < 56500:
            self._switch_music("final_push")
        else:
            self._switch_music("final_push")

        bear.setXPosition(150)
        bear.setYPosition(300)
        bear.initialHeight = 300
        bear.setJumpStatus(False)
        bear.setLeftJumpStatus(False)
        bear.jumpVelocity = 0.0
        bear.sourceBlock = None
        bear.setHp(checkpoint.get('hp', bear.getHp()))
        bear.setMaxHp(checkpoint.get('max_hp', bear.getMaxHp()))
        bear.setCurrentExp(checkpoint.get('exp', bear.getCurrentExp()))
        bear.setLevel(checkpoint.get('level', bear.getLevel()))
        bear.setCoins(checkpoint.get('coins', bear.getCoins()))
        bear.setDamageAttack(checkpoint.get('damageAttack', bear.getDamageAttack()))
        bear.has_shield = checkpoint.get('has_shield', False)
        bear.has_aimer = checkpoint.get('has_aimer', False)
        bear.has_50pct_protection = checkpoint.get('has_50pct_protection', False)
        bear.has_lightning = checkpoint.get('has_lightning', False)
        bear.has_lightning_2 = checkpoint.get('has_lightning_2', False)
        bear.has_big_fireball = checkpoint.get('has_big_fireball', False)
        self._clear_poison(bear)

        self._hardMode = checkpoint.get('hardMode', False)
        self._hardMode75 = checkpoint.get('hardMode75', False)
        self._hardMode80 = checkpoint.get('hardMode80', False)

        totalDistance = restart_dist
        backgroundScrollX = restart_dist
        background.setXPosition(backgroundScrollX)
        return totalDistance, backgroundScrollX

    # -----------------------------------------------------------------------
    # Helper: draw the bear idle sprite (used to fill animation gaps)
    # -----------------------------------------------------------------------
    _idle_blink_timer = 0
    _idle_blink_interval = 120
    _idle_blink_frames = 0
    _idle_hair_timer = 0

    def _draw_idle_bear(self, bear):
        if bear.get_crouch():
            if not bear.getLeftDirection():
                if bear.crouch_sprite:
                    offset_y = self.standingBear.get_height() - bear.crouch_sprite.get_height()
                    self.screen.blit(bear.crouch_sprite,
                                     (bear.getXPosition(), bear.getYPosition() + offset_y))
            else:
                if bear.crouch_sprite_left:
                    offset_y = self.standingBearLeft.get_height() - bear.crouch_sprite_left.get_height()
                    self.screen.blit(bear.crouch_sprite_left,
                                     (bear.getXPosition(), bear.getYPosition() + offset_y))
        else:
            self._idle_blink_timer += 1
            self._idle_hair_timer += 1
            is_blinking = False
            if self._idle_blink_timer >= self._idle_blink_interval:
                self._idle_blink_frames += 1
                is_blinking = True
                if self._idle_blink_frames >= 8:
                    self._idle_blink_frames = 0
                    self._idle_blink_timer = 0
                    self._idle_blink_interval = random.randint(90, 200)
                    is_blinking = False

            if is_blinking:
                if not bear.getLeftDirection():
                    sprite = self.standingBearBlink
                else:
                    sprite = self.standingBearLeftBlink
            else:
                if not bear.getLeftDirection():
                    sprite = self.standingBear
                else:
                    sprite = self.standingBearLeft

            hair_sway = math.sin(self._idle_hair_timer * 0.06) * 2.0
            sw, sh = sprite.get_size()
            hair_h = sh // 4
            body_h = sh - hair_h
            ws, hs = bear.get_land_squash_scale()
            bx = bear.getXPosition()
            by = bear.getYPosition()
            if ws != 1.0 or hs != 1.0:
                ssw = int(sw * ws)
                ssh = int(sh * hs)
                squashed = pygame.transform.scale(sprite, (ssw, ssh))
                ox = (sw - ssw) // 2
                oy = sh - ssh
                self.screen.blit(squashed, (bx + ox, by + oy))
            else:
                hair_part = sprite.subsurface((0, 0, sw, hair_h))
                body_part = sprite.subsurface((0, hair_h, sw, body_h))
                self.screen.blit(body_part, (bx, by + hair_h))
                self.screen.blit(hair_part, (bx + hair_sway, by))

    def _draw_grace_indicator(self, bear, hurtTimer):
        if hurtTimer > 60 or hurtTimer < 0:
            return
        bx = bear.getXPosition()
        by = bear.getYPosition()

        if (hurtTimer // 4) % 2 == 0:
            _flash = pygame.Surface((100, 100), pygame.SRCALPHA)
            _flash.fill((255, 255, 255, 60))
            self.screen.blit(_flash, (bx, by))

        _remaining = 60 - hurtTimer
        _bar_w = int(40 * (_remaining / 60.0))
        if _bar_w > 0:
            _bar_x = bx + 30
            _bar_y = by - 14
            pygame.draw.rect(self.screen, (40, 40, 40, 180), (_bar_x - 1, _bar_y - 1, 42, 7))
            _col = (100, 200, 255) if _remaining > 20 else (255, 180, 60)
            pygame.draw.rect(self.screen, _col, (_bar_x, _bar_y, _bar_w, 5))

        if hurtTimer < 30:
            _shield = pygame.Surface((28, 32), pygame.SRCALPHA)
            _alpha = int(200 * (1 - hurtTimer / 30.0))
            pygame.draw.polygon(_shield, (100, 180, 255, _alpha), [
                (14, 0), (0, 6), (0, 18), (14, 32), (28, 18), (28, 6)])
            pygame.draw.polygon(_shield, (180, 220, 255, _alpha), [
                (14, 0), (0, 6), (0, 18), (14, 32), (28, 18), (28, 6)], 2)
            pygame.draw.polygon(_shield, (220, 240, 255, min(255, _alpha + 30)), [
                (14, 4), (4, 8), (4, 16), (14, 28), (24, 16), (24, 8)])
            self.screen.blit(_shield, (bx + 36, by - 18))

    _WALK_BOB = (2, -1, 2, -1)
    _WALK_LEAN = (1.2, 0.0, -1.2, 0.0)

    def _precompute_walk_lean(self):
        lean_angles = self._WALK_LEAN
        self._walk_right_leaned = []
        self._walk_left_leaned = []
        self._walk_right_offsets = []
        self._walk_left_offsets = []
        right_frames = (self.bearWalking1, self.bearWalking2,
                        self.bearWalking3, self.bearWalking4)
        left_frames = (self.bearWalkingLeft1, self.bearWalkingLeft2,
                       self.bearWalkingLeft3, self.bearWalkingLeft4)
        for i in range(4):
            angle_r = lean_angles[i]
            angle_l = -lean_angles[i]
            ow = right_frames[i].get_width()
            oh = right_frames[i].get_height()
            if angle_r != 0.0:
                rotated = pygame.transform.rotate(right_frames[i], angle_r)
                dx = (rotated.get_width() - ow) // 2
                dy = (rotated.get_height() - oh) // 2
                self._walk_right_leaned.append(rotated)
                self._walk_right_offsets.append((-dx, -dy))
            else:
                self._walk_right_leaned.append(right_frames[i])
                self._walk_right_offsets.append((0, 0))
            ow_l = left_frames[i].get_width()
            oh_l = left_frames[i].get_height()
            if angle_l != 0.0:
                rotated_l = pygame.transform.rotate(left_frames[i], angle_l)
                dx_l = (rotated_l.get_width() - ow_l) // 2
                dy_l = (rotated_l.get_height() - oh_l) // 2
                self._walk_left_leaned.append(rotated_l)
                self._walk_left_offsets.append((-dx_l, -dy_l))
            else:
                self._walk_left_leaned.append(left_frames[i])
                self._walk_left_offsets.append((0, 0))

    def _get_bear_walk_frame(self, animation_counter, facing_left=False):
        walk_index = (animation_counter // 10) % 4
        if facing_left:
            return self._walk_left_leaned[walk_index]
        return self._walk_right_leaned[walk_index]

    def _get_walk_offset(self, animation_counter, facing_left=False):
        walk_index = (animation_counter // 10) % 4
        if facing_left:
            return self._walk_left_offsets[walk_index]
        return self._walk_right_offsets[walk_index]

    def _get_walk_bob(self, animation_counter):
        walk_index = (animation_counter // 10) % 4
        return self._WALK_BOB[walk_index]

    def _runTestRoom(self):
        clock = pygame.time.Clock()
        bear = Bear(150, 300, self.screen, self.thud_sound)
        bear.grunt_sound = self.grunt_sound
        bear.jump_scream_sound = getattr(self, 'jump_scream_sound', None)
        bear.level_up_sound = getattr(self, 'level_up_sound', None)
        bear.spike_hit_sound = getattr(self, 'spike_hit_sound', None)
        bear.has_lightning = True
        bear.has_lightning_2 = True
        bear.crouch_sprite = self.crouchBear
        bear.crouch_sprite_left = self.crouchBearLeft
        bear.setJumpStatus(False)
        bear.setLeftJumpStatus(False)
        bear.setDamageAttack(50)

        _ms = getattr(self, 'monkey_screech_sound', None)
        _lr = getattr(self, 'lion_roar_sound', None)
        monkey = MonkeyMummy(500, 220, 180, 180, self.mummy1, self.mummy2, self.screen, _ms)
        lion = Lion(700, 230, self.screen, _lr)

        background = Background(self.screen)
        background._jungle_mode = True
        background._black_latched = False

        hurtTimer = 61
        attackingAnimationCounter = 0
        attackingLeftAnimtationCounter = 0
        attackCounterReady = 30
        test_font = pygame.font.SysFont(None, 28, bold=True)
        info_font = pygame.font.SysFont(None, 20)

        try:
            pygame.mixer.music.load("Game/Sounds/spooky_peaceful.wav")
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

            keys = pygame.key.get_pressed()
            attackCounterReady += 1
            hurtTimer += 1

            if keys[pygame.K_RIGHT]:
                bear.setLeftDirection(False)
                bear.setXPosition(bear.getXPosition() + STEP)
                if bear.getXPosition() > 800:
                    bear.setXPosition(800)
            if keys[pygame.K_LEFT]:
                bear.setLeftDirection(True)
                bear.setXPosition(bear.getXPosition() - STEP)
                if bear.getXPosition() < 0:
                    bear.setXPosition(0)

            if keys[pygame.K_z] and not bear.getJumpStatus() and not bear.getLeftJumpStatus():
                bear.startJump()
                bear.setJumpStatus(True)

            if bear.getJumpStatus() or bear.getLeftJumpStatus():
                bear._jumpPhysics([])

            if keys[pygame.K_a] and attackCounterReady > 20:
                attackingAnimationCounter = 1
                attackCounterReady = 0
                if self.thud_sound: self.thud_sound.play()
                for enemy in [monkey, lion]:
                    if enemy.getHealth() > 0:
                        if is_monster_hurt(bear.getXPosition(), bear.getYPosition(),
                                         enemy.getXPosition(), enemy.getYPosition(),
                                         bear.getLeftDirection(), enemy.getName()):
                            _dmg = bear.getDamageAttack()
                            enemy.setDamageReceived(_dmg)
                            enemy.setStunned(1)
                            enemy.setHealth(enemy.getHealth() - _apply_defense(enemy, _dmg))

            for enemy in [monkey, lion]:
                if hasattr(enemy, 'getHealth') and enemy.getHealth() > 0:
                    er = pygame.Rect(enemy.getXPosition(), enemy.getYPosition(),
                                     enemy.width, enemy.height)
                    br = pygame.Rect(bear.getXPosition(), bear.getYPosition(), 100, 100)
                    if er.colliderect(br) and hurtTimer > 60:
                        _dmg = enemy.getDamageAttack()
                        bear.setHp(bear.getHp() - _dmg)
                        hurtTimer = 0

            if attackingAnimationCounter > 0:
                attackingAnimationCounter += 1
                if attackingAnimationCounter > 15:
                    attackingAnimationCounter = 0

            background.render()
            self.screen.blit(background.surface, (0, 0))

            monkey.setBlocks([])
            if monkey.getHealth() > 0:
                monkey.drawMonster()
            elif monkey.getStartDestructionAnimationStatus():
                monkey.drawDestruction(monkey.getDamageReceived())
            else:
                monkey = MonkeyMummy(random.randint(300, 700), 220, 180, 180,
                                     self.mummy1, self.mummy2, self.screen, _ms)

            if lion.getHealth() > 0:
                lion.drawMonster()
            elif lion.startDestructionAnimation:
                lion.drawDestruction(lion.getDamageReceived())
            else:
                lion = Lion(random.randint(300, 700), 230, self.screen, _lr)

            if attackingAnimationCounter > 0:
                attackingAnimationCounter += 1
                if attackingAnimationCounter >= 12:
                    attackingAnimationCounter = 0
                if bear.getLeftDirection():
                    self.screen.blit(self.bearAttackingLeft,
                                     (bear.getXPosition() - 80, bear.getYPosition()))
                else:
                    self.screen.blit(self.bearAttacking,
                                     (bear.getXPosition(), bear.getYPosition()))
            else:
                self._draw_idle_bear(bear)

            label = test_font.render("TEST ROOM - Press ESC to exit", True, (255, 220, 100))
            self.screen.blit(label, (450 - label.get_width() // 2, 10))
            _mk_info = info_font.render(
                f"Monkey HP: {monkey.getHealth()}/{monkey.max_health}  Y: {int(monkey.getYPosition())}  Floor: {monkey.FLOOR_Y}",
                True, (200, 200, 200))
            self.screen.blit(_mk_info, (10, 660))
            _li_info = info_font.render(
                f"Lion HP: {lion.getHealth()}/{lion.max_health}  Y: {int(lion.getYPosition())}  Floor: {lion.FLOOR_Y}",
                True, (200, 200, 200))
            self.screen.blit(_li_info, (10, 680))

            pygame.display.update()
            clock.tick(60)

    def showStartMenu(self):
        try:
            pygame.mixer.music.load("Game/Sounds/menu_theme.wav")
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

        clock = pygame.time.Clock()
        button_font = pygame.font.SysFont(None, 44, bold=True)
        info_font = pygame.font.SysFont(None, 22)

        selected = 0
        menu_running = True
        anim_tick = 0
        _sparkles = []
        for _i in range(25):
            _sparkles.append({
                'x': random.randint(0, 900),
                'y': random.randint(0, 700),
                'speed': random.uniform(0.2, 0.8),
                'size': random.randint(1, 3),
                'phase': random.randint(0, 120),
            })

        while menu_running:
            anim_tick += 1
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        selected = 0
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = 1
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        menu_running = False
                    elif event.key == pygame.K_p:
                        self._runTestRoom()
                        return None

            self.screen.fill((18, 12, 28))

            for sp in _sparkles:
                sp['y'] -= sp['speed']
                if sp['y'] < -5:
                    sp['y'] = 710
                    sp['x'] = random.randint(0, 900)
                twinkle = abs(((anim_tick + sp['phase']) % 120) / 60.0 - 1.0)
                brightness = int(100 + 155 * twinkle)
                color = (brightness, brightness, int(min(255, brightness + 40)))
                pygame.draw.circle(self.screen, color, (int(sp['x']), int(sp['y'])), sp['size'])

            pulse = abs(((anim_tick % 100) / 50.0) - 1.0)

            try:
                bear_img = self.standingBear
                bx_pos = 450 - bear_img.get_width() // 2
                by_pos = 160
                glow_r = int(70 + 15 * pulse)
                glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (80, 60, 140, int(40 + 25 * pulse)),
                                   (glow_r, glow_r), glow_r)
                self.screen.blit(glow_surf,
                                 (bx_pos + bear_img.get_width() // 2 - glow_r,
                                  by_pos + bear_img.get_height() // 2 - glow_r))
                self.screen.blit(bear_img, (bx_pos, by_pos))
            except Exception:
                pass

            buttons = ["NORMAL", "HARD"]
            btn_colors_sel = [(100, 180, 120), (220, 80, 80)]
            btn_colors_unsel = [(60, 90, 65), (100, 50, 50)]
            for i, btn_text in enumerate(buttons):
                bx = 450
                by = 380 + i * 80
                is_selected = (i == selected)

                if is_selected:
                    glow_alpha = int(50 + 30 * pulse)
                    glow_surf = pygame.Surface((280, 55), pygame.SRCALPHA)
                    glow_surf.fill((*btn_colors_sel[i], glow_alpha))
                    self.screen.blit(glow_surf, (bx - 140, by - 27))

                box_color = btn_colors_sel[i] if is_selected else btn_colors_unsel[i]
                pygame.draw.rect(self.screen, box_color, (bx - 130, by - 24, 260, 48), 3, border_radius=12)

                text_color = (255, 255, 255) if is_selected else (130, 125, 140)
                btn_surf = button_font.render(btn_text, True, text_color)
                self.screen.blit(btn_surf, (bx - btn_surf.get_width() // 2, by - btn_surf.get_height() // 2))

            controls_text = info_font.render("UP / DOWN to select  -  ENTER to start", True, (90, 85, 105))
            self.screen.blit(controls_text, (450 - controls_text.get_width() // 2, 560))

            pygame.display.update()
            clock.tick(60)

        self._hard_mode_selected = (selected == 1)

        _last_frame = self.screen.copy()
        _transition_len = 90

        for frame in range(_transition_len):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return None

            self.screen.blit(_last_frame, (0, 0))

            fade_t = frame / float(_transition_len)
            fade_alpha = int(255 * min(1.0, fade_t * 1.5))
            dark = pygame.Surface((900, 700), pygame.SRCALPHA)
            dark.fill((0, 0, 0, fade_alpha))
            self.screen.blit(dark, (0, 0))

            menu_vol = max(0.0, 1.0 - fade_t)
            try:
                pygame.mixer.music.set_volume(0.35 * menu_vol)
            except Exception:
                pass

            pygame.display.update()
            clock.tick(60)

        try:
            pygame.mixer.music.load("Game/Sounds/spooky_peaceful.wav")
            pygame.mixer.music.set_volume(0.0)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

        self._game_fade_in = 60

        return selected

    def runGame(self):
        self.triggerFire = False
        floorHeight = 400
        continueLoop = True
        bear = Bear(150, 300, self.screen, self.thud_sound)
        self._bear_ref = bear
        bear.grunt_sound = self.grunt_sound
        bear.jump_scream_sound = getattr(self, 'jump_scream_sound', None)
        bear.level_up_sound = getattr(self, 'level_up_sound', None)
        bear.spike_hit_sound = getattr(self, 'spike_hit_sound', None)
        bear.has_lightning = False
        bear.has_lightning_2 = False
        # Assign crouch sprites
        bear.crouch_sprite = self.crouchBear
        bear.crouch_sprite_left = self.crouchBearLeft
        bear.setJumpStatus(False)
        bear.setLeftJumpStatus(False)

        attackingAnimationCounter = 0
        attackingLeftAnimtationCounter = 0
        hurtTimer = 0
        background = Background(self.screen)
        self._bg_ref = background
        for x in [700, 1000, 1300, 1600]:
            mummy = Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen)
            self.mummys.append(mummy)
        self._fireball_tutorial_shown = False

        # Pre-load Zone 1 assets now so there is no stutter when the player
        # reaches that area. These objects sit idle until the zone triggers.
        self._z1_mummy       = Mummy(1000, 20, 260, 360, self.mummy1, self.mummy2, self.screen)
        self._z1_block_left  = Block(0,    250, 130, 150, "monster", self.screen)
        self._z1_block_right = Block(1800, 250, 130, 150, "monster", self.screen)
        self._z1_door        = Door(self.screen, 1650)

        self.activeMonsters = [False] * 16

        # Initial obstacle platforms – each clearly separated with ~80 px gaps
        block1 = Block(230,  340, 100, 60,  "red",     self.screen)
        block2 = Block(500,  190, 100, 60,  "monster", self.screen)
        block3 = Block(780,  190, 100, 60,  "red",     self.screen)
        block5 = Block(1010, 190, 100, 60,  "red",     self.screen)
        block7 = Block(1240, 190, 100, 60,  "monster", self.screen)
        block6 = Block(1470, 190, 100, 60,  "monster", self.screen)
        block8 = Block(1600, 100, 250, 300, "monster", self.screen)

        self.door = []
        self.keys = []

        self.blocks.extend([block1, block2, block3, block5, block6, block7])
        self.bossTimerAnimation = 0
        self.blocks.append(block8)

        bearAnimation = 0
        isBearHurtAnimation = 0
        self.isDoor1Open = False
        self.escape = False
        backgroundScrollX = bear.getXPosition()
        totalDistance = 60
        bear.setLeftDirection(False)
        jumpTimer = 0
        attackCounterReady = 0
        playerFireCooldown = 0
        deflectTimer = 0
        deflectPos = (0, 0)
        waterOffset = 0
        shop_open = False
        shop_selection = 0
        shop_message = ""
        shop_message_timer = 0
        shop_last_weapon_bought = None
        self._current_music = "normal"
        self._footstep_counter = 0
        self._mummy_groan_timer = 0
        beamCharge = 0.0
        beamCooldown = 0
        beamReadyPopupShown = False
        _q_key_prev = False

        # Show intro popup once at game start
        if not self._intro_shown:
            self._intro_shown = True
            bear.setArrayText(['Welcome to the Bear Adventure!', '',
                               'Z:Attack  X:Fireball  ENTER:Shop',
                               'C:Beam  Q:Lightning (once bought)',
                               'Press "s" to continue'])
            bear.setEndText(False)

        for mummy in self.mummys:
            mummy.setStunned(0)
        for witch in self.witches:
            witch.setStunned(0)
        self.door = []
        self.spikes = []

        triggerWitchFireBallAnimation = 0

        # ===================================================================
        # Main game loop
        # ===================================================================
        while continueLoop:
            # --- Handle window close event ---------------------------------
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        shop_open = not shop_open
                        if shop_open:
                            shop_selection = 0
                            shop_message = ''
                            shop_message_timer = 0
                            if self.shop_open_sound: self.shop_open_sound.play()
                        else:
                            if self.shop_close_sound: self.shop_close_sound.play()
                    elif shop_open:
                        shop_items = []
                        _buy_msgs = {
                            'health': 'Health restored! +20% HP!',
                            'shield': 'Shield purchased! 20% damage block!',
                            'aimer': 'Aimer purchased! UP/DOWN to aim!',
                            'lightning': '\u26A1 Lightning purchased! Press UP + A!',
                            'lightning2': '\u26A1 Lightning 2! UP + A fires 3 bolts!',
                            '50pct': 'Protection unlocked! 50% reduction!',
                            'big_fireball': 'Big Fireball! 30% larger!',
                        }
                        shop_items.append(('health', 30))
                        if not bear.has_shield:
                            shop_items.append(('shield', 40))
                        if not getattr(bear, 'has_50pct_protection', False):
                            shop_items.append(('50pct', 100))
                        if not bear.has_aimer:
                            shop_items.append(('aimer', 50))
                        if not getattr(bear, 'has_big_fireball', False):
                            shop_items.append(('big_fireball', 60))
                        if not getattr(bear, 'has_lightning', False):
                            shop_items.append(('lightning', 60))
                        if getattr(bear, 'has_lightning', False) and not getattr(bear, 'has_lightning_2', False):
                            shop_items.append(('lightning2', 80))
                        shop_selection = min(shop_selection, max(len(shop_items) - 1, 0))
                        if event.key == pygame.K_UP:
                            _prev_sel = shop_selection
                            shop_selection = max(0, shop_selection - 1)
                            if shop_selection != _prev_sel and self.shop_navigate_sound: self.shop_navigate_sound.play()
                        elif event.key == pygame.K_DOWN:
                            _prev_sel = shop_selection
                            shop_selection = min(max(len(shop_items) - 1, 0), shop_selection + 1)
                            if shop_selection != _prev_sel and self.shop_navigate_sound: self.shop_navigate_sound.play()
                        elif event.key == pygame.K_x:
                            if shop_selection < len(shop_items):
                                item_type, cost = shop_items[shop_selection]
                                msg = _buy_msgs.get(item_type, 'Purchased!')
                                if bear.getCoins() >= cost:
                                    bear.setCoins(bear.getCoins() - cost)
                                    if item_type == 'health':
                                        heal = int(bear.getMaxHp() * 0.20)
                                        bear.setHp(min(bear.getMaxHp(), bear.getHp() + heal))
                                    elif item_type == 'shield':
                                        bear.has_shield = True
                                    elif item_type == 'aimer':
                                        bear.has_aimer = True
                                        shop_last_weapon_bought = 'aimer'
                                    elif item_type == 'lightning':
                                        bear.has_lightning = True
                                        shop_last_weapon_bought = 'lightning'
                                        shop_open = False
                                        if self.shop_close_sound: self.shop_close_sound.play()
                                        bear.setArrayText(['\u26A1 Lightning bought! \u26A1',
                                            'Press UP + A to strike!',
                                            'Press "s" to continue'])
                                        bear.setEndText(False)
                                        self.lightning_charge = max(self.lightning_charge, 1.0)
                                        if not bear.getLeftDirection():
                                            _demo_lx = bear.getXPosition() + 140
                                        else:
                                            _demo_lx = bear.getXPosition() - 80
                                        self.lightning_x = int(_demo_lx)
                                        self.lightning_anim = 28
                                        if self.explosion_sound:
                                            self.explosion_sound.play()
                                    elif item_type == 'lightning2':
                                        bear.has_lightning_2 = True
                                        shop_last_weapon_bought = 'lightning2'
                                        shop_open = False
                                        if self.shop_close_sound: self.shop_close_sound.play()
                                        bear.setArrayText(['\u26A1 Lightning 2 bought! \u26A1',
                                            'Press UP + A for 3 bolts!',
                                            'Press "s" to continue'])
                                        bear.setEndText(False)
                                        self.lightning_charge = max(self.lightning_charge, 1.0)
                                        if not bear.getLeftDirection():
                                            _demo_lx = bear.getXPosition() + 140
                                        else:
                                            _demo_lx = bear.getXPosition() - 80
                                        _demo_dir = 1 if not bear.getLeftDirection() else -1
                                        for _bi, _off in enumerate([0, 120 * _demo_dir, 240 * _demo_dir]):
                                            self.lightning2_targets.append({
                                                'x': int(_demo_lx + _off),
                                                'anim': 0,
                                                'delay': _bi * 12,
                                                'dmg': 0
                                            })
                                        if self.explosion_sound:
                                            self.explosion_sound.play()
                                    elif item_type == '50pct':
                                        bear.has_50pct_protection = True
                                    elif item_type == 'big_fireball':
                                        bear.has_big_fireball = True
                                        shop_last_weapon_bought = 'big_fireball'
                                    shop_message = msg
                                    if self.shop_buy_sound: self.shop_buy_sound.play()
                                else:
                                    shop_message = 'Not enough coins.'
                                    if self.shop_error_sound: self.shop_error_sound.play()
                                shop_message_timer = 120
                        elif event.key == pygame.K_ESCAPE:
                            shop_open = False
                            if self.shop_close_sound: self.shop_close_sound.play()
                            if shop_last_weapon_bought == 'aimer':
                                bear.setArrayText(['Aimer bought!',
                                    'Hold UP/DOWN while pressing X',
                                    'to aim your fireballs!',
                                    'Press "s" to continue'])
                                bear.setEndText(False)
                            elif shop_last_weapon_bought == 'big_fireball':
                                bear.setArrayText(['Big Fireball bought!',
                                    'Press X to launch a larger,',
                                    'harder-hitting fireball!',
                                    'Press "s" to continue'])
                                bear.setEndText(False)
                            shop_last_weapon_bought = None
                    elif event.key == pygame.K_z:
                        if bear.getJumpStatus() or bear.getLeftJumpStatus():
                            bear.buffer_jump()

            background.render(totalDistance)
            self._update_tension_layers(totalDistance)
            if shop_open:
                _overlay = pygame.Surface((900, 700), pygame.SRCALPHA)
                _overlay.fill((0, 0, 0, 170))
                self.screen.blit(_overlay, (0, 0))

                panel = pygame.Rect(100, 30, 700, 620)
                pygame.draw.rect(self.screen, (22, 14, 44), panel, border_radius=22)
                _inner_top = pygame.Rect(panel.x + 4, panel.y + 4, panel.width - 8, panel.height // 3)
                pygame.draw.rect(self.screen, (36, 24, 64), _inner_top, border_radius=18)
                pygame.draw.rect(self.screen, (210, 160, 50), panel, 4, border_radius=22)
                _hl = pygame.Surface((panel.width - 16, 2), pygame.SRCALPHA)
                _hl.fill((255, 230, 120, 120))
                self.screen.blit(_hl, (panel.x + 8, panel.y + 8))

                _tw = 260
                _title_rect = pygame.Rect(panel.x + (panel.width - _tw) // 2, panel.y - 20, _tw, 42)
                pygame.draw.rect(self.screen, (160, 110, 30), _title_rect, border_radius=12)
                pygame.draw.rect(self.screen, (255, 215, 90), _title_rect, 3, border_radius=12)
                _sparkle = int(abs(math.sin(pygame.time.get_ticks() * 0.003)) * 40)
                _tc = (255, 235 + min(20, _sparkle), 170)
                _t_surf = _FONT_HUD.render('BEAR SHOP', True, _tc)
                _t_x = _title_rect.x + (_title_rect.width - _t_surf.get_width()) // 2
                self.screen.blit(_t_surf, (_t_x, _title_rect.y + 7))

                _categories = []

                _recovery = []
                _recovery.append(('health', 30, 'Heal 20%', 'Restore 20% of max HP'))
                if _recovery:
                    _categories.append(('Recovery', (255, 130, 130), _recovery))

                _defense = []
                if not bear.has_shield:
                    _defense.append(('shield', 40, 'Shield', '20% damage block'))
                if not getattr(bear, 'has_50pct_protection', False):
                    _defense.append(('50pct', 100, 'Protection', '50% damage reduction'))
                if _defense:
                    _categories.append(('Defense', (100, 180, 255), _defense))

                _weapons = []
                if not bear.has_aimer:
                    _weapons.append(('aimer', 50, 'Aimer', 'UP/DOWN to aim fireballs'))
                if not getattr(bear, 'has_big_fireball', False):
                    _weapons.append(('big_fireball', 60, 'Big Fireball', '30% larger fireballs'))
                if _weapons:
                    _categories.append(('Weapons', (255, 180, 80), _weapons))

                _powers = []
                if not getattr(bear, 'has_lightning', False):
                    _powers.append(('lightning', 60, '\u26A1 Lightning', 'Press UP + A'))
                if getattr(bear, 'has_lightning', False) and not getattr(bear, 'has_lightning_2', False):
                    _powers.append(('lightning2', 80, '\u26A1 Lightning 2', 'UP + A: 3 bolts'))
                if _powers:
                    _categories.append(('Powers', (180, 140, 255), _powers))

                shop_items = []
                for _cat_name, _cat_color, _cat_items in _categories:
                    for _ci in _cat_items:
                        shop_items.append((_ci[0], _ci[1], _ci[2], _ci[3], _cat_name, _cat_color))
                shop_selection = min(shop_selection, max(len(shop_items) - 1, 0))

                _left_x = panel.x + 20
                _item_w = panel.width - 40
                _row_h = 48
                _cat_h = 24
                _cur_y = panel.y + 38
                _drawn_cats = set()
                _icon_map = {
                    'health': ('*', (255, 80, 80)),
                    'shield': ('+', (100, 200, 255)),
                    '50pct': ('++', (80, 180, 255)),
                    'aimer': ('o', (255, 200, 80)),
                    'big_fireball': ('~', (255, 140, 40)),
                    'lightning': ('!', (200, 160, 255)),
                    'lightning2': ('!!', (220, 180, 255)),
                }

                if not shop_items:
                    render_hud_text_outlined(self.screen, _FONT_HUD, 'All items owned!',
                                            panel.x + 200, panel.y + 260, (200, 255, 200))
                for idx, (item_id, cost, title, subtitle, cat_name, cat_color) in enumerate(shop_items):
                    if cat_name not in _drawn_cats:
                        _drawn_cats.add(cat_name)
                        _cat_bar = pygame.Rect(_left_x, _cur_y, _item_w, _cat_h)
                        _cat_bg = (cat_color[0] // 6, cat_color[1] // 6, cat_color[2] // 6)
                        pygame.draw.rect(self.screen, _cat_bg, _cat_bar, border_radius=6)
                        _dot_r = 4
                        pygame.draw.circle(self.screen, cat_color, (_left_x + 14, _cur_y + _cat_h // 2), _dot_r)
                        _cs = _FONT_HUD_VAL.render(cat_name.upper(), True, cat_color)
                        self.screen.blit(_cs, (_left_x + 26, _cur_y + 4))
                        _line_x = _left_x + 30 + _cs.get_width() + 8
                        pygame.draw.line(self.screen, (cat_color[0] // 2, cat_color[1] // 2, cat_color[2] // 2),
                                         (_line_x, _cur_y + _cat_h // 2), (_left_x + _item_w - 10, _cur_y + _cat_h // 2), 1)
                        _cur_y += _cat_h + 4

                    _sel = (shop_selection == idx)
                    _row_rect = pygame.Rect(_left_x, _cur_y, _item_w, _row_h)
                    if _sel:
                        _pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.005)) * 20)
                        _bg = (60 + _pulse, 38 + _pulse // 2, 110 + _pulse)
                        pygame.draw.rect(self.screen, _bg, _row_rect, border_radius=10)
                        pygame.draw.rect(self.screen, (220, 180, 255), _row_rect, 2, border_radius=10)
                        _arrow_x = _left_x + 6
                        _arrow_y = _cur_y + _row_h // 2
                        pygame.draw.polygon(self.screen, (255, 220, 100),
                                            [(_arrow_x, _arrow_y - 5), (_arrow_x + 8, _arrow_y), (_arrow_x, _arrow_y + 5)])
                    else:
                        pygame.draw.rect(self.screen, (30, 20, 55), _row_rect, border_radius=10)
                        pygame.draw.rect(self.screen, (70, 55, 100), _row_rect, 1, border_radius=10)

                    _icon_char, _icon_col = _icon_map.get(item_id, ('?', (200, 200, 200)))
                    _icon_cx = _left_x + 30
                    _icon_cy = _cur_y + _row_h // 2
                    pygame.draw.circle(self.screen, (_icon_col[0] // 3, _icon_col[1] // 3, _icon_col[2] // 3),
                                       (_icon_cx, _icon_cy), 14)
                    pygame.draw.circle(self.screen, _icon_col, (_icon_cx, _icon_cy), 12)
                    _ic_s = _FONT_HUD_VAL.render(_icon_char, True, (30, 20, 40))
                    self.screen.blit(_ic_s, (_icon_cx - _ic_s.get_width() // 2, _icon_cy - _ic_s.get_height() // 2))

                    _name_x = _left_x + 52
                    _name_col = (255, 248, 220) if _sel else (210, 200, 180)
                    render_hud_text_outlined(self.screen, _FONT_HUD_LABEL, title, _name_x, _cur_y + 5, _name_col)
                    _desc_col = (190, 175, 230) if _sel else (140, 130, 170)
                    render_hud_text_outlined(self.screen, _FONT_HUD_VAL, subtitle, _name_x, _cur_y + 27, _desc_col)

                    _cost_str = f'{cost}'
                    _cost_surf = _FONT_HUD_LABEL.render(_cost_str, True, (255, 230, 80) if _sel else (200, 180, 60))
                    _cost_x = _left_x + _item_w - _cost_surf.get_width() - 30
                    self.screen.blit(_cost_surf, (_cost_x, _cur_y + 8))
                    _coin_r = 8
                    _coin_cx = _cost_x + _cost_surf.get_width() + 14
                    _coin_cy = _cur_y + 16
                    pygame.draw.circle(self.screen, (255, 215, 0), (_coin_cx, _coin_cy), _coin_r)
                    pygame.draw.circle(self.screen, (255, 245, 130), (_coin_cx, _coin_cy), 4)

                    _cur_y += _row_h + 4

                _footer_y = panel.y + panel.height - 68
                _footer_rect = pygame.Rect(_left_x, _footer_y, _item_w, 52)
                pygame.draw.rect(self.screen, (18, 12, 36), _footer_rect, border_radius=10)
                pygame.draw.rect(self.screen, (80, 60, 110), _footer_rect, 1, border_radius=10)
                _purse_cx = _left_x + 28
                _purse_cy = _footer_y + 18
                pygame.draw.circle(self.screen, (255, 215, 0), (_purse_cx, _purse_cy), 14)
                pygame.draw.circle(self.screen, (255, 245, 130), (_purse_cx, _purse_cy), 8)
                pygame.draw.circle(self.screen, (255, 215, 0), (_purse_cx, _purse_cy), 4)
                render_hud_text_outlined(self.screen, _FONT_HUD_LABEL, f'{bear.getCoins()} coins',
                                         _left_x + 50, _footer_y + 8, (255, 230, 80))
                _ctrl_text = '[UP/DOWN] select    [X] buy    [ENTER] close'
                _ctrl_surf = _FONT_HUD_VAL.render(_ctrl_text, True, (180, 165, 210))
                self.screen.blit(_ctrl_surf, (_left_x + _item_w - _ctrl_surf.get_width() - 8, _footer_y + 30))

                if shop_message_timer > 0:
                    _msg_rect = pygame.Rect(_left_x, _footer_y - 30, _item_w, 26)
                    pygame.draw.rect(self.screen, (50, 35, 18), _msg_rect, border_radius=8)
                    pygame.draw.rect(self.screen, (180, 140, 40), _msg_rect, 1, border_radius=8)
                    render_hud_text_outlined(self.screen, _FONT_HUD_LABEL, shop_message,
                                             _msg_rect.x + 12, _msg_rect.y + 3, (255, 255, 140))
                pygame.display.flip()
                self.clock.tick(60)
                continue

            render_water(self.screen, waterOffset)
            waterOffset = (waterOffset + 2) % 60

            global STEP
            _base_step = 12 if bear.getLevel() >= 14 else 8
            _enemies_on_screen = (self.mummys + self.witches +
                                  self.greenBlobs + self.frankenbear +
                                  self.shadowShamans + self.miniFrankenBears +
                                  self.snakes + self.monkey_mummies + self.lions)
            _has_alive_enemy = any(
                (hasattr(e, 'getHealth') and e.getHealth() > 0 and
                 -150 <= e.getXPosition() <= 950)
                for e in _enemies_on_screen
            )
            _target_step = _base_step if _has_alive_enemy else int(_base_step * 1.5)
            if bear.getLevel() >= 14:
                _target_step = min(_target_step, 12)
            bear._speed_lerp += (_target_step - bear._speed_lerp) * 0.12
            STEP = max(1, int(round(bear._speed_lerp)))

            _on_ground = (not bear.getJumpStatus() and not bear.getLeftJumpStatus())
            bear.update_coyote(_on_ground)
            bear.tick_jump_buffer()

            if bear.getEndText():

                keys = pygame.key.get_pressed()

                # ---- X: throw fireball at full health --------------------
                playerFireCooldown = max(0, playerFireCooldown - 1)
                if (keys[pygame.K_x]
                        and playerFireCooldown == 0):
                    _base_cd = 30
                    if getattr(bear, 'has_aimer', False):
                        _base_cd = 12
                    if bear.getLevel() >= 14:
                        _base_cd = max(5, int(_base_cd * 0.95))
                    playerFireCooldown = _base_cd
                    _lvl = bear.getLevel()
                    _eff_lvl = min(_lvl, 9)
                    _boost = 1.2 if _eff_lvl >= 6 else 1.0
                    if _lvl >= 12:
                        _boost *= 2.5
                    _fb_speed = int(10 * (1.15 ** (_eff_lvl // 2)) * _boost)
                    if getattr(bear, 'has_aimer', False):
                        dx = -1 if keys[pygame.K_LEFT] else (1 if keys[pygame.K_RIGHT] else (-1 if bear.getLeftDirection() else 1))
                        dy = -1 if keys[pygame.K_UP] else (1 if keys[pygame.K_DOWN] else 0)
                        if dx == 0 and dy == 0:
                            dx = -1 if bear.getLeftDirection() else 1
                        if dx != 0 and dy != 0:
                            angle_factor = 0.75
                        else:
                            angle_factor = 1.0
                        vel_x = int(_fb_speed * dx * angle_factor)
                        vel_y = int(_fb_speed * dy * angle_factor)
                    else:
                        vel_x = -_fb_speed if bear.getLeftDirection() else _fb_speed
                        vel_y = 0
                    fb_x = (bear.getXPosition() - 60
                            if bear.getLeftDirection()
                            else bear.getXPosition() + 100)
                    fb_y = bear.getYPosition() + 30
                    if _lvl >= 12:
                        _fb_img = self.fireballGold
                    elif _lvl >= 10:
                        _fb_img = self.fireballRainbow
                    elif _lvl >= 8:
                        _fb_img = self.fireballBlue
                    elif _lvl >= 6:
                        _fb_img = self.fireballGreen
                    elif _lvl >= 4:
                        _fb_img = self.fireballYellow
                    else:
                        _fb_img = self.fireBossBall
                    self.playerFires.append(
                        FireBall(fb_x, fb_y, vel_x, vel_y,
                                 _fb_img,
                                 self.screen,
                                 size=(78, 78) if getattr(bear, 'has_big_fireball', False) else (60, 60)))
                    if getattr(bear, 'has_big_fireball', False):
                        self.playerFires[-1].damageAttack = int(self.playerFires[-1].damageAttack * 1.2)
                    if self.fire_sound:
                        self.fire_sound.play()
                    attackingAnimationCounter = 1

                # ---- C: beam super attack ---------------------------------
                beamCooldown = max(0, beamCooldown - 1)
                beamCharge = min(100.0, beamCharge + 0.10)
                if beamCharge >= 100.0 and not beamReadyPopupShown and not self._beam_ever_shown:
                    beamReadyPopupShown = True
                    self._beam_ever_shown = True
                    bear.setArrayText(['BEAM READY!', 'Press C to fire the beam!', 'Press "s" to continue'])
                    bear.setEndText(False)
                if keys[pygame.K_c] and beamCharge >= 100.0 and beamCooldown == 0:
                    beamCharge = 0.0
                    beamCooldown = 60
                    beamReadyPopupShown = False
                    _beam_dmg = bear.getDamageAttack() * 4
                    _beam_vx = -18 if bear.getLeftDirection() else 18
                    _beam_x = (bear.getXPosition() - 100
                               if bear.getLeftDirection()
                               else bear.getXPosition() + 100)
                    _beam_y = bear.getYPosition() + 30
                    self.beamProjectiles.append({
                        "x": _beam_x, "y": _beam_y,
                        "vx": _beam_vx, "dmg": _beam_dmg, "timer": 90,
                        "hit_ids": set()
                    })
                    if self.beam_sound:
                        self.beam_sound.play()
                    attackingAnimationCounter = 1

                # ---- D: shockwave attack (also crouches on floor when not attacking) ----------------
                self.weapon_cooldown = max(0, self.weapon_cooldown - 1)
                if keys[pygame.K_d] and self.weapon_cooldown == 0:
                    self.weapon_cooldown = 60
                    shock_x = bear.getXPosition() + 50
                    shock_y = bear.getYPosition() + 50
                    if getattr(self, '_secret_attack_unlocked', False):
                        shock_radius = 240
                        shock_damage = int(bear.getDamageAttack() * 2.2)
                    else:
                        shock_radius = 150
                        shock_damage = int(bear.getDamageAttack() * 1.5)
                    
                    # Draw expanding circle effect
                    for r in range(0, shock_radius, 20):
                        pygame.draw.circle(self.screen, (100, 200, 255), (int(shock_x), int(shock_y)), r, 2)
                    
                    if self.explosion_sound:
                        self.explosion_sound.play()
                    
                    # Damage enemies in radius
                    enemies = (self.mummys + self.witches + self.greenBlobs +
                              self.shadowShamans + self.miniFrankenBears + self.snakes + self.lions)
                    for enemy in enemies:
                        if hasattr(enemy, 'getHealth') and enemy.getHealth() > 0:
                            ex = enemy.getXPosition() + 40
                            ey = enemy.getYPosition() + 50
                            dist = ((ex - shock_x) ** 2 + (ey - shock_y) ** 2) ** 0.5
                            if dist < shock_radius:
                                enemy.setDamageReceived(shock_damage)
                                enemy.setStunned(3)
                                enemy.setHealth(enemy.getHealth() - _apply_defense(enemy, shock_damage))
                elif keys[pygame.K_d] and self.weapon_cooldown > 0:
                    # D not on cooldown for attack: crouch only on floor
                    if (not bear.getJumpStatus() and not bear.getLeftJumpStatus()
                            and bear.getYPosition() + 100 >= 400):
                        bear.set_crouch(True)
                    else:
                        bear.set_crouch(False)
                else:
                    bear.set_crouch(False)

                # ---- Q: lightning strike in front of player ----------------
                if getattr(bear, 'has_lightning', False):
                    self.lightning_charge = min(2.0, self.lightning_charge + 0.005)
                _q_key_down = keys[pygame.K_q]
                _q_key_fresh = _q_key_down and not _q_key_prev
                _q_key_prev = _q_key_down
                _up_combo = keys[pygame.K_UP] and keys[pygame.K_a]
                _up_combo_fresh = _up_combo and not getattr(self, '_up_combo_prev', False)
                self._up_combo_prev = _up_combo
                _lightning_trigger = _q_key_fresh or _up_combo_fresh
                if (_lightning_trigger and getattr(bear, 'has_lightning', False)
                        and self.lightning_charge >= 1.0
                        and bear.getEndText() and not shop_open):
                    self.lightning_charge -= 1.0  # consume one charge
                    # Strike point: directly in front of the bear
                    if not bear.getLeftDirection():
                        _lx = bear.getXPosition() + 140
                    else:
                        _lx = bear.getXPosition() - 80
                    if getattr(bear, 'has_lightning_2', False):
                        # Lightning 2: 3 successive bolts each 120 px further
                        _offsets = [0, 120, 240] if not bear.getLeftDirection() else [0, -120, -240]
                        for _bi, _off in enumerate(_offsets):
                            self.lightning2_targets.append({
                                'x': int(_lx + _off),
                                'anim': 0,
                                'delay': _bi * 12,
                                'dmg': int(bear.getDamageAttack() * 2.5)
                            })
                        # Apply damage for each bolt
                        _lene = (self.mummys + self.witches + self.greenBlobs +
                                 self.shadowShamans + self.miniFrankenBears +
                                 self.snakes + self.monkey_mummies + self.lions)
                        for _bi, _off in enumerate(_offsets):
                            _bx = int(_lx + _off)
                            _ldmg = int(bear.getDamageAttack() * 2.5)
                            _lrect = pygame.Rect(_bx - 45, 0, 90, 450)
                            for _le in _lene:
                                if hasattr(_le, 'getHealth') and _le.getHealth() > 0:
                                    _er = pygame.Rect(_le.getXPosition(), _le.getYPosition(), 100, 100)
                                    if _lrect.colliderect(_er):
                                        _le.setHealth(_le.getHealth() - _apply_defense(_le, _ldmg))
                                        _le.setDamageReceived(_ldmg)
                                        if hasattr(_le, 'setStunned'):
                                            _le.setStunned(6)
                    else:
                        self.lightning_x = int(_lx)
                        self.lightning_anim = 28  # frames of animation
                        _ldmg = int(bear.getDamageAttack() * 2.5)
                        _lrect = pygame.Rect(self.lightning_x - 45, 0, 90, 450)
                        _lene = (self.mummys + self.witches + self.greenBlobs +
                                 self.shadowShamans + self.miniFrankenBears +
                                 self.snakes + self.monkey_mummies + self.lions)
                        for _le in _lene:
                            if hasattr(_le, 'getHealth') and _le.getHealth() > 0:
                                _er = pygame.Rect(_le.getXPosition(), _le.getYPosition(), 100, 100)
                                if _lrect.colliderect(_er):
                                    _le.setHealth(_le.getHealth() - _apply_defense(_le, _ldmg))
                                    _le.setDamageReceived(_ldmg)
                                    if hasattr(_le, 'setStunned'):
                                        _le.setStunned(6)
                    if self.explosion_sound:
                        self.explosion_sound.play()

                # ---- Z + RIGHT: jump-right --------------------------------
                if keys[pygame.K_z] and keys[pygame.K_RIGHT]:
                    airborne = bear.getJumpStatus() or bear.getLeftJumpStatus()
                    # x-only wall check for tall blocks (used in both airborne
                    # and ground-start sections below).
                    # Uses STEP look-ahead: would moving right by STEP put the
                    # bear's right edge at or past the block's left edge?
                    def _tall_wall_ahead(bx, ignore=None):
                        bear_right = bx + 100
                        for blk in self.blocks:
                            if blk is ignore:
                                continue
                            if ((bear_right + STEP) >= blk.getBlockXPosition()
                                    and bear_right < blk.getBlockXPosition() + blk.getWidth()
                                    and (blk.getBlockYPosition() + blk.getHeight()) >= 380):
                                return True
                        return False

                    _jump_right_moved = False
                    if airborne:
                        totalDistance += STEP
                        _src = getattr(bear, 'sourceBlock', None)
                        if bear.getXPosition() < self.rightBoundary:
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                            if _src:
                                _src.setIsLeftBoundary(False)
                                _src.setIsRightBoundary(False)
                            if (not any(b.getIsLeftBoundary() for b in self.blocks)
                                    and not _tall_wall_ahead(bear.getXPosition(), _src)):
                                bear.setXPosition(bear.getXPosition() + STEP)
                                backgroundScrollX = bear.getXPosition() - STEP
                                background.setXPosition(backgroundScrollX)
                                _jump_right_moved = True
                            else:
                                totalDistance -= STEP
                        else:
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                            if _src:
                                _src.setIsLeftBoundary(False)
                                _src.setIsRightBoundary(False)
                            if (any(b.getIsLeftBoundary() for b in self.blocks)
                                    or _tall_wall_ahead(bear.getXPosition(), _src)):
                                totalDistance -= STEP
                            else:
                                _jump_right_moved = True
                                moveObjects = (self.mummys + self.fires + self.witches +
                                               self.greenBlobs + self.door + self.keys + self.spikes +
                                               self.playerFires + self.shadowShamans + self.miniFrankenBears +
                                               self.lasers + self.snakes + self.monkey_mummies + self.lions)
                                for obj in moveObjects:
                                    obj.setXPosition(obj.getXPosition() - STEP)
                                for coin in self.coins:
                                    coin.setXPosition(coin.getXPosition() - STEP)
                                for db in self.destroyable_blocks:
                                    db.setblockXPosition(db.getBlockXPosition() - STEP)
                                for _bp in self.beamProjectiles:
                                    _bp["x"] -= STEP
                                for _b in self.bombs:
                                    _b["x"] -= STEP
                                for _orb in self.shaman_orbs:
                                    _orb["x"] -= STEP; _orb["center_x"] -= STEP
                                for _wb in self.witch_beams:
                                    _wb["x1"] -= STEP; _wb["x2"] -= STEP
                                for _hd in self.heart_drops:
                                    _hd["x"] -= STEP
                                for block in self.blocks:
                                    if not block.getIsLeftBoundary():
                                        block.setblockXPosition(block.getBlockXPosition() - STEP)
                                        backgroundScrollX = bear.getXPosition() + STEP
                                        background.setXPosition(backgroundScrollX)

                    elif jumpTimer > 12:
                        totalDistance += STEP
                        _jump_moved = True
                        if bear.getXPosition() < self.rightBoundary:
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                if block.getIsLeftBoundary():
                                    totalDistance -= STEP
                                    _jump_moved = False
                            if _jump_moved and _tall_wall_ahead(bear.getXPosition()):
                                totalDistance -= STEP
                                _jump_moved = False
                            backgroundScrollX = bear.getXPosition() - STEP
                            background.setXPosition(backgroundScrollX)
                            if _jump_moved:
                                bear.setXPosition(bear.getXPosition() + STEP)
                        else:
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                            if (any(b.getIsLeftBoundary() for b in self.blocks)
                                    or _tall_wall_ahead(bear.getXPosition())):
                                totalDistance -= STEP
                                _jump_moved = False
                            else:
                                moveObjects = (self.mummys + self.fires + self.witches +
                                               self.greenBlobs + self.door + self.keys + self.spikes +
                                               self.playerFires + self.shadowShamans + self.miniFrankenBears +
                                               self.lasers + self.snakes + self.monkey_mummies + self.lions)
                                for obj in moveObjects:
                                    obj.setXPosition(obj.getXPosition() - STEP)
                                for coin in self.coins:
                                    coin.setXPosition(coin.getXPosition() - STEP)
                                for db in self.destroyable_blocks:
                                    db.setblockXPosition(db.getBlockXPosition() - STEP)
                                for _bp in self.beamProjectiles:
                                    _bp["x"] -= STEP
                                for _b in self.bombs:
                                    _b["x"] -= STEP
                                for _orb in self.shaman_orbs:
                                    _orb["x"] -= STEP; _orb["center_x"] -= STEP
                                for _wb in self.witch_beams:
                                    _wb["x1"] -= STEP; _wb["x2"] -= STEP
                                for _hd in self.heart_drops:
                                    _hd["x"] -= STEP
                                for block in self.blocks:
                                    if not block.getIsLeftBoundary():
                                        block.setblockXPosition(block.getBlockXPosition() - STEP)
                                        backgroundScrollX = bear.getXPosition() + STEP
                                        background.setXPosition(backgroundScrollX)
                        if _jump_moved:
                            backgroundScrollX -= STEP
                            background.setXPosition(backgroundScrollX)
                        bear.setJumpStatus(True)
                        # Capture which block we're jumping from so _jumpPhysics can skip it
                        for block in self.blocks:
                            if block.getOnPlatform():
                                bear.sourceBlock = block
                                break
                        bear.startJump()
                        jumpTimer = 0

                    # Only enforce side-wall collision on the ground, not mid-arc
                    if not bear.getJumpStatus() and not bear.getLeftJumpStatus():
                        for block in self.blocks:
                            if block.getIsLeftBoundary():
                                bear.setXPosition(bear.getXPosition() - STEP)
                                totalDistance += STEP

                    dangerousObjects = (self.mummys + self.fires + self.witches +
                                        self.greenBlobs + self.spikes + self.bossFires +
                                        self.frankenbear + self.shadowShamans + self.miniFrankenBears + self.snakes + self.monkey_mummies + self.lions)
                    for monster in dangerousObjects:
                        if hasattr(monster, 'getHealth') and monster.getHealth() <= 0:
                            continue
                        if (bear.is_bear_hurt("RIGHT", bear.getXPosition(), bear.getYPosition(),
                                            monster.getXPosition(), monster.getYPosition(),
                                            monster.getName()) and hurtTimer > 60):
                            hurtTimer = 0
                            if getattr(self, 'bear_hurt_sound', None): self.bear_hurt_sound.play()
                            bear.displayDamageOnBear(monster.getDamageAttack(), monster.getName())
                            bear.applyDamage(monster.getDamageAttack())
                            self.screen.blit(self.hurtBear,
                                             (bear.getXPosition(), bear.getYPosition()))
                            if bear.getXPosition() <= 400:
                                bear.setXPosition(bear.getXPosition() + STEP)
                                totalDistance += STEP
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                                bear.displayDamageOnBear(monster.getDamageAttack(), monster.getName())
                            monster.setHurtTimer(monster.getHurtTimer() + 1)
                        elif 0 < monster.getHurtTimer() < 15:
                            monster.setHurtTimer(monster.getHurtTimer() + 1)
                            bear.displayDamageOnBear(monster.getDamageAttack(), monster.getName())
                            self.screen.blit(self.hurtBear,
                                             (bear.getXPosition(), bear.getYPosition()))
                        else:
                            monster.setHurtTimer(0)
                        bear.setLeftDirection(False)

                    if _jump_right_moved or not airborne:
                        background.update(bear.getXPosition(), bear.getYPosition())

                # ---- Z + LEFT: jump-left ---------------------------------
                elif keys[pygame.K_z] and keys[pygame.K_LEFT]:
                    airborne = bear.getJumpStatus() or bear.getLeftJumpStatus()
                    _jump_left_moved = False
                    if airborne:
                        totalDistance -= STEP
                        _src = getattr(bear, 'sourceBlock', None)
                        if bear.getXPosition() > self.leftBoundary:
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                            if _src:
                                _src.setIsLeftBoundary(False)
                                _src.setIsRightBoundary(False)
                            if not any(b.getIsRightBoundary() for b in self.blocks):
                                bear.setXPosition(bear.getXPosition() - STEP)
                                backgroundScrollX = bear.getXPosition() + STEP
                                background.setXPosition(backgroundScrollX)
                                _jump_left_moved = True
                            else:
                                totalDistance += STEP
                        else:
                            _jump_left_moved = True
                            moveObjects = (self.mummys + self.fires + self.witches +
                                           self.greenBlobs + self.door + self.keys + self.spikes +
                                           self.playerFires + self.shadowShamans + self.miniFrankenBears +
                                               self.lasers + self.snakes + self.monkey_mummies + self.lions)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() + STEP)
                            for coin in self.coins:
                                coin.setXPosition(coin.getXPosition() + STEP)
                            for db in self.destroyable_blocks:
                                db.setblockXPosition(db.getBlockXPosition() + STEP)
                            for _bp in self.beamProjectiles:
                                _bp["x"] += STEP
                            for _b in self.bombs:
                                _b["x"] += STEP
                            for _orb in self.shaman_orbs:
                                _orb["x"] += STEP; _orb["center_x"] += STEP
                            for _wb in self.witch_beams:
                                _wb["x1"] += STEP; _wb["x2"] += STEP
                            for _hd in self.heart_drops:
                                _hd["x"] += STEP
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                if not block.getIsRightBoundary():
                                    block.setblockXPosition(block.getBlockXPosition() + STEP)
                                    backgroundScrollX = bear.getXPosition() - STEP
                                    background.setXPosition(backgroundScrollX)
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)

                    elif jumpTimer > 12:
                        totalDistance -= STEP
                        jumpTimer = 0
                        if bear.getXPosition() > self.leftBoundary:
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                if block.getIsRightBoundary():
                                    backgroundScrollX = bear.getXPosition() + STEP
                                    background.setXPosition(backgroundScrollX)
                                    totalDistance += STEP
                            backgroundScrollX = bear.getXPosition() - STEP
                            background.setXPosition(backgroundScrollX)
                            bear.setXPosition(bear.getXPosition() + STEP)
                            totalDistance -= STEP
                        else:
                            moveObjects = (self.mummys + self.fires + self.witches +
                                           self.greenBlobs + self.spikes +
                                           self.playerFires + self.shadowShamans + self.miniFrankenBears +
                                               self.lasers + self.snakes + self.monkey_mummies + self.lions)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() + STEP)
                            for _bp in self.beamProjectiles:
                                _bp["x"] += STEP
                            for _b in self.bombs:
                                _b["x"] += STEP
                            for _orb in self.shaman_orbs:
                                _orb["x"] += STEP; _orb["center_x"] += STEP
                            for _wb in self.witch_beams:
                                _wb["x1"] += STEP; _wb["x2"] += STEP
                            for _hd in self.heart_drops:
                                _hd["x"] += STEP
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                if not block.getIsRightBoundary():
                                    block.setblockXPosition(block.getBlockXPosition() - STEP)
                                    backgroundScrollX = bear.getXPosition() - STEP
                                    background.setXPosition(backgroundScrollX)
                            backgroundScrollX = bear.getXPosition() + STEP
                            background.setXPosition(backgroundScrollX)
                        background.update(backgroundScrollX, bear.getYPosition())
                        bear.setJumpStatus(True)
                        # Capture which block we're jumping from so _jumpPhysics can skip it
                        for block in self.blocks:
                            if block.getOnPlatform():
                                bear.sourceBlock = block
                                break
                        bear.startJump()

                    # Only enforce side-wall collision on the ground, not mid-arc
                    if not bear.getJumpStatus() and not bear.getLeftJumpStatus():
                        for block in self.blocks:
                            if block.getIsRightBoundary():
                                bear.setXPosition(bear.getXPosition() + STEP)
                                totalDistance += STEP

                        dangerousObjects = (self.mummys + self.fires + self.witches +
                                            self.greenBlobs + self.spikes + self.bossFires +
                                            self.frankenbear + self.snakes + self.monkey_mummies + self.lions)
                        for monster in dangerousObjects:
                            if hasattr(monster, 'getHealth') and monster.getHealth() <= 0:
                                continue
                            if (bear.is_bear_hurt("RIGHT", bear.getXPosition(), bear.getYPosition(),
                                                monster.getXPosition(), monster.getYPosition(),
                                                monster.getName()) and hurtTimer > 60):
                                hurtTimer = 0
                                if getattr(self, 'bear_hurt_sound', None): self.bear_hurt_sound.play()
                                bear.displayDamageOnBear(monster.getDamageAttack(), monster.getName())
                                bear.applyDamage(monster.getDamageAttack())
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                                if bear.getXPosition() > self.leftBoundary:
                                    bear.setXPosition(bear.getXPosition() + STEP)
                                    totalDistance += STEP
                                    self.screen.blit(self.hurtBear,
                                                     (bear.getXPosition(), bear.getYPosition()))
                                monster.setHurtTimer(monster.getHurtTimer() + 1)
                            elif 0 < monster.getHurtTimer() < 15:
                                monster.setHurtTimer(monster.getHurtTimer() + 1)
                                bear.displayDamageOnBear(monster.getDamageAttack(), monster.getName())
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                            else:
                                monster.setHurtTimer(0)
                            bear.setLeftDirection(True)
                            bear.setLeftJumpStatus(True)
                            bear.startJump()

                    if _jump_left_moved or not airborne:
                        background.update(backgroundScrollX, bear.getYPosition())

                elif (keys[pygame.K_z]
                      and not bear.getJumpStatus()
                      and not bear.getLeftJumpStatus()
                      and jumpTimer > 12):
                    jumpTimer = 0
                    bear.setJumpStatus(True)
                    bear.setLeftJumpStatus(True)
                    for block in self.blocks:
                        if block.getOnPlatform():
                            bear.sourceBlock = block
                            break
                    bear.startJump()
                    background.update(backgroundScrollX, bear.getYPosition())
                elif (keys[pygame.K_z] and bear.can_coyote_jump()
                      and bear.jumpVelocity <= 0):
                    bear.startJump()
                    bear.setJumpStatus(True)
                    jumpTimer = 0
                    background.update(backgroundScrollX, bear.getYPosition())

                # ---- A + RIGHT: attack right ------------------------------
                elif (keys[pygame.K_a] and keys[pygame.K_RIGHT]
                      and attackingAnimationCounter == 0
                      and attackingLeftAnimtationCounter == 0
                      and attackCounterReady > 20):
                    attackingAnimationCounter += 1
                    bear.setLeftDirection(False)
                    attackCounterReady = 0
                    if self.thud_sound: self.thud_sound.play()
                    if self.attack_sound: self.attack_sound.play()
                    monsters = self.mummys + self.witches + self.greenBlobs + self.frankenbear + self.shadowShamans + self.miniFrankenBears + self.snakes + self.monkey_mummies + self.lions
                    for monster in monsters:
                        if is_monster_hurt(bear.getXPosition(), bear.getYPosition(),
                                         monster.getXPosition(), monster.getYPosition(),
                                         bear.getLeftDirection(), monster.getName()):
                            _base_dmg = bear.getDamageAttack()
                            _is_crit = random.random() < 0.20
                            _dmg = _base_dmg * 2 if _is_crit else _base_dmg
                            if monster.getName() == "bigMummy":
                                if is_monster_forehead_hit(bear.getXPosition(), bear.getYPosition(),
                                                        monster.getXPosition(), monster.getYPosition(),
                                                        bear.getLeftDirection()):
                                    monster.setDamageReceived(_dmg)
                                    monster.setStunned(1)
                                    monster.setHealth(monster.getHealth() - _apply_defense(monster, _dmg))
                                    if _is_crit and self.crit_sound:
                                        self.crit_sound.play()
                                    elif self.hit_sound:
                                        self.hit_sound.play()
                                else:
                                    deflectTimer = 40
                                    deflectPos = (monster.getXPosition() + 70, monster.getYPosition() + 120)
                                    if self.deflect_sound: self.deflect_sound.play()
                            else:
                                if getattr(monster, 'stunned', 0) > 0:
                                    continue
                                if not self.frankenbear:
                                    monster.setXPosition(monster.getXPosition() + STEP)
                                monster.setDamageReceived(_dmg)
                                monster.setStunned(1)
                                monster.setHealth(monster.getHealth() - _apply_defense(monster, _dmg))
                                if _is_crit and self.crit_sound:
                                    self.crit_sound.play()
                                else:
                                    _snd = self.boss_hit_sound if monster in self.frankenbear else self.hit_sound
                                    if _snd: _snd.play()
                    for block in self.blocks:
                        if block.getIsLeftBoundary():
                            bear.setXPosition(bear.getXPosition() - STEP)
                            totalDistance -= STEP

                # ---- A + LEFT: attack left --------------------------------
                elif (keys[pygame.K_a] and keys[pygame.K_LEFT]
                      and attackingAnimationCounter == 0
                      and attackingLeftAnimtationCounter == 0
                      and attackCounterReady > 20):
                    attackingAnimationCounter += 1
                    attackCounterReady = 0
                    bear.setLeftDirection(True)
                    if self.thud_sound: self.thud_sound.play()
                    if self.attack_sound: self.attack_sound.play()
                    monsters = self.mummys + self.witches + self.greenBlobs + self.frankenbear + self.shadowShamans + self.miniFrankenBears + self.snakes + self.monkey_mummies + self.lions
                    for monster in monsters:
                        if is_monster_hurt(bear.getXPosition(), bear.getYPosition(),
                                         monster.getXPosition(), monster.getYPosition(),
                                         bear.getLeftDirection(), monster.getName()):
                            _base_dmg = bear.getDamageAttack()
                            _is_crit = random.random() < 0.20
                            _dmg = _base_dmg * 2 if _is_crit else _base_dmg
                            if monster.getName() == "bigMummy":
                                if is_monster_forehead_hit(bear.getXPosition(), bear.getYPosition(),
                                                        monster.getXPosition(), monster.getYPosition(),
                                                        bear.getLeftDirection()):
                                    monster.setDamageReceived(_dmg)
                                    monster.setStunned(1)
                                    monster.setHealth(monster.getHealth() - _apply_defense(monster, _dmg))
                                    if _is_crit and self.crit_sound:
                                        self.crit_sound.play()
                                    elif self.hit_sound:
                                        self.hit_sound.play()
                                else:
                                    deflectTimer = 40
                                    deflectPos = (monster.getXPosition() + 70, monster.getYPosition() + 120)
                                    if self.deflect_sound: self.deflect_sound.play()
                            else:
                                if getattr(monster, 'stunned', 0) > 0:
                                    continue
                                if not self.frankenbear:
                                    monster.setXPosition(monster.getXPosition() + STEP)
                                monster.setDamageReceived(_dmg)
                                monster.setStunned(1)
                                monster.setHealth(monster.getHealth() - _apply_defense(monster, _dmg))
                                if _is_crit and self.crit_sound:
                                    self.crit_sound.play()
                                else:
                                    _snd = self.boss_hit_sound if monster in self.frankenbear else self.hit_sound
                                    if _snd: _snd.play()
                    for block in self.blocks:
                        if block.getIsLeftBoundary():
                            bear.setXPosition(bear.getXPosition() - STEP)
                            totalDistance += STEP

                # ---- RIGHT: walk right ------------------------------------
                elif (keys[pygame.K_RIGHT]
                      and attackingAnimationCounter == 0
                      and attackingLeftAnimtationCounter == 0):
                    totalDistance += STEP
                    self.deleteAndCreateObjects(totalDistance)
                    bear.setLeftDirection(False)

                    _wall_blocked = False
                    if (not bear.getJumpStatus() and not bear.getLeftJumpStatus()
                            and attackingAnimationCounter == 0):
                        _right_scrolled = False
                        _wall_blocked = False
                        if bear.getXPosition() < self.rightBoundary:
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)
                            bear.setXPosition(bear.getXPosition() + STEP)
                        else:
                            _right_scrolled = True
                            moveObjects = (self.mummys + self.fires + self.witches +
                                           self.greenBlobs + self.door + self.keys + self.spikes +
                                           self.playerFires + self.shadowShamans + self.miniFrankenBears +
                                               self.lasers + self.snakes + self.monkey_mummies + self.lions)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() - STEP)
                            for coin in self.coins:
                                coin.setXPosition(coin.getXPosition() - STEP)
                            for db in self.destroyable_blocks:
                                db.setblockXPosition(db.getBlockXPosition() - STEP)
                            for _bp in self.beamProjectiles:
                                _bp["x"] -= STEP
                            for _b in self.bombs:
                                _b["x"] -= STEP
                            for _orb in self.shaman_orbs:
                                _orb["x"] -= STEP; _orb["center_x"] -= STEP
                            for _wb in self.witch_beams:
                                _wb["x1"] -= STEP; _wb["x2"] -= STEP
                            for _hd in self.heart_drops:
                                _hd["x"] -= STEP
                            for block in self.blocks:
                                if not block.getIsLeftBoundary():
                                    block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                    block.setblockXPosition(block.getBlockXPosition() - STEP)
                                elif block.getIsLeftBoundary():
                                    block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                    block.setblockXPosition(block.getBlockXPosition() - STEP)
                                    totalDistance -= STEP
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)

                        # Non-scroll case: undo bear position if wall detected
                        if not _right_scrolled:
                            for block in self.blocks:
                                if block.getIsLeftBoundary():
                                    bear.setXPosition(bear.getXPosition() - STEP)
                                    totalDistance -= STEP

                        # Detect if any block is blocking movement right
                        _wall_blocked = any(b.getIsLeftBoundary() for b in self.blocks)

                        # Undo world scroll when the bear was blocked by a wall
                        if _right_scrolled and _wall_blocked:
                            for obj in (self.mummys + self.fires + self.witches +
                                        self.greenBlobs + self.door + self.keys +
                                        self.spikes):
                                obj.setXPosition(obj.getXPosition() + STEP)
                            for coin in self.coins:
                                coin.setXPosition(coin.getXPosition() + STEP)
                            for b in self.blocks:
                                b.setblockXPosition(b.getBlockXPosition() + STEP)
                            totalDistance -= STEP
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)

                        _bob = self._get_walk_bob(bearAnimation)
                        _lox, _loy = self._get_walk_offset(bearAnimation)
                        self.screen.blit(self._get_bear_walk_frame(bearAnimation),
                                         (bear.getXPosition() + _lox, bear.getYPosition() - 10 + _bob + _loy))
                        self._footstep_counter += 1
                        if self._footstep_counter % 11 == 0 and self.footstep_sound:
                            self.footstep_sound.play()

                        dangerousObjects = (self.mummys + self.fires + self.witches +
                                            self.greenBlobs + self.spikes + self.bossFires +
                                            self.frankenbear + self.snakes + self.monkey_mummies + self.lions)
                        for monster in dangerousObjects:
                            if hasattr(monster, 'getHealth') and monster.getHealth() <= 0:
                                continue
                            if (bear.is_bear_hurt("RIGHT", bear.getXPosition(), bear.getYPosition(),
                                                monster.getXPosition(), monster.getYPosition(),
                                                monster.getName()) and hurtTimer > 60):
                                hurtTimer = 0
                                if getattr(self, 'bear_hurt_sound', None): self.bear_hurt_sound.play()
                                bear.displayDamageOnBear(monster.getDamageAttack(), monster.getName())
                                bear.applyDamage(monster.getDamageAttack())
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                                bear.setXPosition(bear.getXPosition() - STEP)
                                totalDistance -= STEP
                                monster.setHurtTimer(monster.getHurtTimer() + 1)
                            elif 0 < monster.getHurtTimer() < 15:
                                monster.setHurtTimer(monster.getHurtTimer() + 1)
                                bear.displayDamageOnBear(monster.getDamageAttack(), monster.getName())
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                            else:
                                monster.setHurtTimer(0)

                    elif bear.getJumpStatus() or bear.getLeftJumpStatus():
                        if bear.getXPosition() < self.rightBoundary:
                            jumpTimer = 0
                            bear_right = bear.getXPosition() + 100
                            _wall_right = False
                            _src = getattr(bear, 'sourceBlock', None)
                            for block in self.blocks:
                                if block is _src:
                                    continue
                                blx = block.getBlockXPosition()
                                brx = blx + block.getWidth()
                                bty = block.getBlockYPosition()
                                bby = bty + block.getHeight()
                                if (bear_right > blx and bear.getXPosition() < brx
                                        and bear.getYPosition() < bby and bear.getYPosition() + 100 > bty):
                                    _wall_right = True
                                    break
                            if not _wall_right:
                                bear.setXPosition(bear.getXPosition() + STEP)
                                backgroundScrollX = bear.getXPosition()
                                background.setXPosition(backgroundScrollX)
                            else:
                                totalDistance -= STEP
                        else:
                            jumpTimer = 0
                            moveObjects = (self.mummys + self.fires + self.witches +
                                           self.greenBlobs + self.door + self.keys + self.spikes +
                                           self.playerFires + self.shadowShamans + self.miniFrankenBears +
                                               self.lasers + self.snakes + self.monkey_mummies + self.lions)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() - STEP)
                            for coin in self.coins:
                                coin.setXPosition(coin.getXPosition() - STEP)
                            for db in self.destroyable_blocks:
                                db.setblockXPosition(db.getBlockXPosition() - STEP)
                            for _bp in self.beamProjectiles:
                                _bp["x"] -= STEP
                            for _b in self.bombs:
                                _b["x"] -= STEP
                            for _orb in self.shaman_orbs:
                                _orb["x"] -= STEP; _orb["center_x"] -= STEP
                            for _wb in self.witch_beams:
                                _wb["x1"] -= STEP; _wb["x2"] -= STEP
                            for _hd in self.heart_drops:
                                _hd["x"] -= STEP
                            for block in self.blocks:
                                block.setblockXPosition(block.getBlockXPosition() - STEP)
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)

                    bearAnimation += 1
                    if not _wall_blocked:
                        background.update(backgroundScrollX, bear.getYPosition())
                    self.deleteAndCreateObjects(totalDistance)

                # ---- LEFT: walk left -------------------------------------
                elif (keys[pygame.K_LEFT]
                      and attackingAnimationCounter == 0
                      and attackingLeftAnimtationCounter == 0):
                    totalDistance -= STEP
                    bear.setLeftDirection(True)

                    if (not bear.getJumpStatus() and not bear.getLeftJumpStatus()
                            and attackingAnimationCounter == 0):
                        _left_scrolled = False
                        if bear.getXPosition() > self.leftBoundary:
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)
                            bear.setXPosition(bear.getXPosition() - STEP)
                        else:
                            _left_scrolled = True
                            moveObjects = (self.mummys + self.fires + self.witches +
                                           self.greenBlobs + self.door + self.keys + self.spikes +
                                           self.playerFires + self.shadowShamans + self.miniFrankenBears +
                                               self.lasers + self.snakes + self.monkey_mummies + self.lions)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() + STEP)
                            for coin in self.coins:
                                coin.setXPosition(coin.getXPosition() + STEP)
                            for db in self.destroyable_blocks:
                                db.setblockXPosition(db.getBlockXPosition() + STEP)
                            for _bp in self.beamProjectiles:
                                _bp["x"] += STEP
                            for _b in self.bombs:
                                _b["x"] += STEP
                            for _orb in self.shaman_orbs:
                                _orb["x"] += STEP; _orb["center_x"] += STEP
                            for _wb in self.witch_beams:
                                _wb["x1"] += STEP; _wb["x2"] += STEP
                            for _hd in self.heart_drops:
                                _hd["x"] += STEP
                            for block in self.blocks:
                                if not block.getIsRightBoundary():
                                    block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                    block.setblockXPosition(block.getBlockXPosition() + STEP)
                                if block.getIsRightBoundary():
                                    totalDistance += STEP
                                    block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                    block.setblockXPosition(block.getBlockXPosition() + STEP)
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)

                        for block in self.blocks:
                            if block.getIsRightBoundary():
                                totalDistance += STEP
                                bear.setXPosition(bear.getXPosition() + STEP)

                        # Undo world scroll when the bear was blocked by a wall moving left
                        if _left_scrolled and any(b.getIsRightBoundary() for b in self.blocks):
                            for obj in (self.mummys + self.fires + self.witches +
                                        self.greenBlobs + self.door + self.keys +
                                        self.spikes):
                                obj.setXPosition(obj.getXPosition() - STEP)
                            for coin in self.coins:
                                coin.setXPosition(coin.getXPosition() - STEP)
                            for b in self.blocks:
                                b.setblockXPosition(b.getBlockXPosition() - STEP)
                            totalDistance -= STEP
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)

                        self._footstep_counter += 1
                        if self._footstep_counter % 11 == 0 and self.footstep_sound:
                            self.footstep_sound.play()
                        _bob_l = self._get_walk_bob(bearAnimation)
                        _lox_l, _loy_l = self._get_walk_offset(bearAnimation, facing_left=True)
                        self.screen.blit(self._get_bear_walk_frame(bearAnimation, facing_left=True),
                                         (bear.getXPosition() + _lox_l, bear.getYPosition() - 10 + _bob_l + _loy_l))

                        dangerousObjects = (self.mummys + self.fires + self.witches +
                                            self.greenBlobs + self.spikes + self.bossFires +
                                            self.frankenbear + self.snakes + self.monkey_mummies + self.lions)
                        for monster in dangerousObjects:
                            if hasattr(monster, 'getHealth') and monster.getHealth() <= 0:
                                continue
                            if (bear.is_bear_hurt("RIGHT", bear.getXPosition(), bear.getYPosition(),
                                                monster.getXPosition(), monster.getYPosition(),
                                                monster.getName()) and hurtTimer > 60):
                                if getattr(self, 'bear_hurt_sound', None): self.bear_hurt_sound.play()
                                bear.displayDamageOnBear(monster.getDamageAttack(), monster.getName())
                                bear.applyDamage(monster.getDamageAttack())
                                hurtTimer = 0
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                                bear.setXPosition(bear.getXPosition() + STEP)
                                totalDistance += STEP
                                monster.setHurtTimer(monster.getHurtTimer() + 1)
                            elif 0 < monster.getHurtTimer() < 15:
                                monster.setHurtTimer(monster.getHurtTimer() + 1)
                                bear.displayDamageOnBear(monster.getDamageAttack(), monster.getName())
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                            else:
                                monster.setHurtTimer(0)

                    elif bear.getJumpStatus() or bear.getLeftJumpStatus():
                        jumpTimer = 0
                        if bear.getXPosition() > self.leftBoundary:
                            bear_left = bear.getXPosition()
                            _wall_left = False
                            _src = getattr(bear, 'sourceBlock', None)
                            for block in self.blocks:
                                if block is _src:
                                    continue
                                blx = block.getBlockXPosition()
                                brx = blx + block.getWidth()
                                bty = block.getBlockYPosition()
                                bby = bty + block.getHeight()
                                if (bear_left < brx and bear_left + 100 > blx
                                        and bear.getYPosition() < bby and bear.getYPosition() + 100 > bty):
                                    _wall_left = True
                                    break
                            if not _wall_left:
                                bear.setXPosition(bear.getXPosition() - STEP)
                                backgroundScrollX = bear.getXPosition() + STEP
                                background.setXPosition(backgroundScrollX)
                            else:
                                totalDistance += STEP
                        else:
                            moveObjects = (self.mummys + self.fires + self.greenBlobs +
                                           self.witches + self.door + self.keys + self.spikes +
                                           self.playerFires + self.shadowShamans + self.miniFrankenBears +
                                               self.lasers + self.snakes + self.monkey_mummies + self.lions)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() + STEP)
                            for _bp in self.beamProjectiles:
                                _bp["x"] += STEP
                            for _b in self.bombs:
                                _b["x"] += STEP
                            for _orb in self.shaman_orbs:
                                _orb["x"] += STEP; _orb["center_x"] += STEP
                            for _wb in self.witch_beams:
                                _wb["x1"] += STEP; _wb["x2"] += STEP
                            for _hd in self.heart_drops:
                                _hd["x"] += STEP
                            for block in self.blocks:
                                block.setblockXPosition(block.getBlockXPosition() + STEP)
                            backgroundScrollX = bear.getXPosition() - STEP
                            background.setXPosition(backgroundScrollX)

                    bearAnimation += 1
                    background.update(backgroundScrollX, bear.getYPosition())

                # ---- A only: attack (no direction) -----------------------
                elif (keys[pygame.K_a]
                      and attackingAnimationCounter == 0
                      and attackingLeftAnimtationCounter == 0
                      and attackCounterReady > 20):
                    attackingAnimationCounter += 1
                    attackCounterReady = 0
                    if self.thud_sound: self.thud_sound.play()
                    if self.attack_sound: self.attack_sound.play()
                    monsters = self.mummys + self.witches + self.greenBlobs + self.frankenbear + self.shadowShamans + self.miniFrankenBears + self.snakes + self.monkey_mummies + self.lions
                    for monster in monsters:
                        if is_monster_hurt(bear.getXPosition(), bear.getYPosition(),
                                         monster.getXPosition(), monster.getYPosition(),
                                         bear.getLeftDirection(), monster.getName()):
                            if monster.getName() == "bigMummy":
                                if is_monster_forehead_hit(bear.getXPosition(), bear.getYPosition(),
                                                        monster.getXPosition(), monster.getYPosition(),
                                                        bear.getLeftDirection()):
                                    monster.setDamageReceived(bear.getDamageAttack())
                                    monster.setStunned(1)
                                    monster.setHealth(monster.getHealth() - _apply_defense(monster, bear.getDamageAttack()))
                                    if self.hit_sound: self.hit_sound.play()
                                else:
                                    deflectTimer = 40
                                    deflectPos = (monster.getXPosition() + 70, monster.getYPosition() + 120)
                                    if self.deflect_sound: self.deflect_sound.play()
                            else:
                                if getattr(monster, 'stunned', 0) > 0:
                                    continue
                                if not self.frankenbear:
                                    monster.setXPosition(monster.getXPosition() + STEP)
                                monster.setDamageReceived(bear.getDamageAttack())
                                monster.setStunned(1)
                                monster.setHealth(monster.getHealth() - _apply_defense(monster, bear.getDamageAttack()))
                                _snd = self.boss_hit_sound if monster in self.frankenbear else self.hit_sound
                                if _snd: _snd.play()

                # ---- ESC: quit -------------------------------------------
                elif keys[pygame.K_ESCAPE]:
                    pygame.quit()
                    return

                # ---- idle / standing ------------------------------------
                else:
                    if (not bear.getJumpStatus() and not bear.getLeftJumpStatus()
                            and attackingAnimationCounter == 0
                            and attackingLeftAnimtationCounter == 0
                            and isBearHurtAnimation == 0):
                        self._draw_idle_bear(bear)

                    dangerousObjects = (self.mummys + self.fires + self.witches +
                                        self.greenBlobs + self.spikes + self.bossFires +
                                        self.frankenbear + self.shadowShamans + self.miniFrankenBears + self.snakes + self.monkey_mummies + self.lions)
                    for monster in dangerousObjects:
                        if hasattr(monster, 'getHealth') and monster.getHealth() <= 0:
                            continue
                        if (bear.is_bear_hurt("LEFT", bear.getXPosition(), bear.getYPosition(),
                                            monster.getXPosition(), monster.getYPosition(),
                                            monster.getName()) and hurtTimer > 60):
                            if getattr(self, 'bear_hurt_sound', None): self.bear_hurt_sound.play()
                            bear.displayDamageOnBear(monster.getDamageAttack(), monster.getName())
                            bear.applyDamage(monster.getDamageAttack())
                            hurtTimer = 0
                            self.screen.blit(self.hurtBear,
                                             (bear.getXPosition(), bear.getYPosition()))
                            rel = get_position_relative_to_monster(
                                bear.getXPosition(), bear.getYPosition(),
                                monster.getXPosition(), monster.getYPosition())
                            if rel == "RIGHT":
                                backgroundScrollX = bear.getXPosition() + STEP
                                background.setXPosition(backgroundScrollX)
                                bear.setXPosition(bear.getXPosition() + STEP)
                                totalDistance += STEP
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                            else:
                                backgroundScrollX = bear.getXPosition() - STEP * 2
                                background.setXPosition(backgroundScrollX)
                                bear.setXPosition(bear.getXPosition() - STEP * 2)
                                totalDistance -= STEP * 2
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                                monster.setHurtTimer(monster.getHurtTimer() + 1)
                        elif 0 < monster.getHurtTimer() < 15:
                            monster.setHurtTimer(monster.getHurtTimer() + 1)
                            bear.displayDamageOnBear(monster.getDamageAttack(), monster.getName())
                            self.screen.blit(self.hurtBear,
                                             (bear.getXPosition(), bear.getYPosition()))
                        else:
                            monster.setHurtTimer(0)

            _airborne = bear.getJumpStatus() or bear.getLeftJumpStatus()
            if _airborne:
                if bear.getJumpStatus():
                    bear.jump(self.blocks)
                elif bear.getLeftJumpStatus():
                    bear.leftJump(self.blocks)

            # ---- Attack animation (always runs, fixes 1-frame flicker gap) ------
            if 1 <= attackingAnimationCounter < 12:
                attackingAnimationCounter += 1
                if bear.getLeftDirection():
                    self.screen.blit(self.bearAttackingLeft,
                                     (bear.getXPosition() - 80, bear.getYPosition()))
                else:
                    self.screen.blit(self.bearAttacking,
                                     (bear.getXPosition(), bear.getYPosition()))
            elif attackingAnimationCounter >= 12:
                attackingAnimationCounter = 0
                if not _airborne:
                    self._draw_idle_bear(bear)
            elif 1 <= attackingLeftAnimtationCounter < 12:
                attackingLeftAnimtationCounter += 1
                self.screen.blit(self.bearAttackingLeft,
                                 (bear.getXPosition(), bear.getYPosition()))
            elif attackingLeftAnimtationCounter >= 12:
                attackingLeftAnimtationCounter = 0
                if not _airborne:
                    self._draw_idle_bear(bear)
            elif not _airborne:
                if bear.getJumpStatus():
                    bear.jump(self.blocks)
                elif bear.getLeftJumpStatus():
                    bear.leftJump(self.blocks)


            self._draw_grace_indicator(bear, hurtTimer)

            # ---- Boundary and timer updates ------------------------------
            bear.boundaryExtraCheck()
            jumpTimer += 1

            # ---- Draw blocks first so monsters render in front of them --
            for block in self.blocks:
                block.drawRectangle()
            
            # ---- Draw and update destroyable blocks -----
            destroyable_to_remove = []
            for db in self.destroyable_blocks:
                if db.getHealth() > 0:
                    db.drawRectangle()
                elif (db.getHealth() <= 0
                      and db.getDestructionAnimationCount() < 20
                      and not db.getStartDestructionAnimationStatus()):
                    db.setStartDestructionAnimation(True)
                elif db.getStartDestructionAnimationStatus():
                    db.destructionAnimation += 1
                    if db.destructionAnimation >= 30:
                        db.setStartDestructionAnimation(False)
                        # Drop coin and weapon
                        coin = Coin(db.getBlockXPosition() + 30, db.getBlockYPosition() + 30, self.screen)
                        self.coins.append(coin)
                    if getattr(db, 'secret', False) and not self._secret_attack_unlocked:
                        self._secret_attack_unlocked = True
                        bear.setArrayText([
                            'SECRET ATTACK UNLOCKED!',
                            'Press "r" to unleash the shockwave.',
                            'Greater range and stronger damage.',
                            'Press "s" to continue'])
                        bear.setEndText(False)
            for db in destroyable_to_remove:
                if db in self.destroyable_blocks:
                    self.destroyable_blocks.remove(db)

            # ---- Monster lifecycle ---------------------------------------
            for mummy in self.mummys:
                mummy.setBlocks(self.blocks)
                if not hasattr(mummy, '_jump_sound'):
                    mummy._jump_sound = self.mummy_jump_sound
            
            for mm in self.monkey_mummies:
                mm.setBlocks(self.blocks)

            monsters = self.mummys + self.witches + self.greenBlobs + self.shadowShamans + self.miniFrankenBears + self.snakes + self.monkey_mummies + self.lions
            _bear_x = bear.getXPosition()
            _bear_y = bear.getYPosition()

            _alive = [m for m in monsters if m.getHealth() > 0]
            for i, m in enumerate(_alive):
                if not hasattr(m, '_sep_offset'):
                    continue
                for j in range(i + 1, len(_alive)):
                    o = _alive[j]
                    if not hasattr(o, '_sep_offset'):
                        continue
                    _sdx = m.getXPosition() - o.getXPosition()
                    _sep_dist = abs(_sdx)
                    _min_gap = 60
                    if _sep_dist < _min_gap and _sep_dist > 0:
                        _push = (_min_gap - _sep_dist) * 0.15
                        _sign = 1 if _sdx > 0 else -1
                        m._sep_offset += _sign * _push
                        o._sep_offset -= _sign * _push
                    elif _sep_dist == 0:
                        m._sep_offset += random.choice([-2.0, 2.0])
                        o._sep_offset += random.choice([-2.0, 2.0])

            _popup_active = not bear.getEndText()
            to_remove = []
            for monster in monsters:
                if monster.getHealth() > 0:
                    if hasattr(monster, '_bear_x'):
                        monster._bear_x = _bear_x
                        monster._bear_y = _bear_y
                    monster._popup_frozen = _popup_active
                    if hasattr(monster, 'drawMonster'):
                        monster.drawMonster()
                    else:
                        monster.draw()
                elif (monster.getHealth() <= 0
                      and monster.getDestructionAnimationCount() < 20
                      and not monster.getStartDestructionAnimationStatus()):
                    monster.setStartDestructionAnimation(True)
                elif monster.getStartDestructionAnimationStatus():
                    if monster.getDestructionAnimationCount() == 1:
                        if getattr(self, 'enemy_hit_sound', None):
                            self.enemy_hit_sound.play()
                    if monster.getDestructionAnimationCount() == 5:
                        _is_boss_monster = monster.getName() == "bigMummy"
                        if _is_boss_monster and getattr(self, 'boss_explosion_sound', None):
                            self.boss_explosion_sound.play()
                        elif self.explosion_sound:
                            self.explosion_sound.play()
                    _death_dmg = monster.getDamageReceived() if monster.getDamageReceived() > 0 else bear.getDamageAttack()
                    monster.drawDestruction(_death_dmg) if hasattr(monster, 'drawDestruction') else None
                    _destroy_limit = 60 if monster.getName() == "bigMummy" else 30
                    if monster.getDestructionAnimationCount() >= _destroy_limit:
                        monster.setStartDestructionAnimation(False)
                        _exp_gain = monster.getExp()
                        if self._hardMode:
                            _exp_gain = int(_exp_gain * 1.75)
                        bear.setCurrentExp(bear.getCurrentExp() + _exp_gain)
                        to_remove.append(monster)

            for monster in to_remove:
                _hp_ratio = bear.getHp() / max(1, bear.getMaxHp())
                _heart_chance = 0.75 if _hp_ratio < 0.15 else (0.50 if _hp_ratio < 0.30 else 0.0)
                if _heart_chance > 0 and random.random() < _heart_chance:
                    self.heart_drops.append({
                        'x': float(monster.getXPosition() + 40),
                        'y': float(monster.getYPosition()),
                        'vy': -2.0, 'landed': False, 'life': 420
                    })
                if monster in self.mummys:
                    self.mummys.remove(monster)
                    for _ci in range(random.randint(1, 3)):
                        self.coins.append(Coin(monster.getXPosition() + 20 + _ci * 18,
                                               monster.getYPosition() + 30, self.screen))
                    if len(self.mummys) == 0 and self.door and not self.doorPopupTriggered:
                        self.doorPopupTriggered = True
                        bear.setEndText(False)
                        bear.textArray = [['You opened the door!',
                                           'Proceed to the next area!',
                                           'Press "s" to continue']]
                        bear.showBearArray = [False]
                        bear.tupleIndex = 0
                        bear.line = 0
                        bear.indexArray = 0
                        bear.totalText1 = ""
                        bear.totalText2 = ""
                        bear.totalText3 = ""
                        bear.text1 = ""
                        bear.text2 = ""
                        bear.text3 = ""
                elif monster in self.witches:
                    self.witches.remove(monster)
                    for _ci in range(random.randint(1, 3)):
                        self.coins.append(Coin(monster.getXPosition() + 20 + _ci * 18,
                                               monster.getYPosition() + 30, self.screen))
                elif monster in self.greenBlobs:
                    self.greenBlobs.remove(monster)
                    for _ci in range(random.randint(1, 3)):
                        self.coins.append(Coin(monster.getXPosition() + 20 + _ci * 18,
                                               monster.getYPosition() + 30, self.screen))
                elif monster in self.shadowShamans:
                    self.shadowShamans.remove(monster)
                    for _ci in range(random.randint(1, 3)):
                        self.coins.append(Coin(monster.getXPosition() + 20 + _ci * 18,
                                               monster.getYPosition() + 30, self.screen))
                elif monster in self.miniFrankenBears:
                    self.miniFrankenBears.remove(monster)
                    for _ci in range(random.randint(1, 3)):
                        self.coins.append(Coin(monster.getXPosition() + 20 + _ci * 18,
                                               monster.getYPosition() + 30, self.screen))
                elif monster in self.snakes:
                    self.snakes.remove(monster)
                    for _ci in range(random.randint(1, 3)):
                        self.coins.append(Coin(monster.getXPosition() + 20 + _ci * 18,
                                               monster.getYPosition() + 30, self.screen))
                elif monster in self.monkey_mummies:
                    self.monkey_mummies.remove(monster)
                    for _ci in range(random.randint(1, 3)):
                        self.coins.append(Coin(monster.getXPosition() + 20 + _ci * 18,
                                               monster.getYPosition() + 30, self.screen))
                elif monster in self.lions:
                    self.lions.remove(monster)
                    for _ci in range(random.randint(2, 4)):
                        self.coins.append(Coin(monster.getXPosition() + 20 + _ci * 18,
                                               monster.getYPosition() + 30, self.screen))

                if getattr(self, '_jungle_zone2_active', False):
                    _jungle_enemies_left = len(self.monkey_mummies) + len(self.snakes) + len(self.lions)
                    if _jungle_enemies_left == 0:
                        self.newGamePlusLevel += 1
                        bear.setArrayText([
                            'JUNGLE CONQUERED!', '',
                            'NEW GAME + ' + str(self.newGamePlusLevel) + ' UNLOCKED!',
                            '', 'Returning to the crypt...', '',
                            'Press "s" to continue'])
                        bear.setEndText(False)
                        self._monkey_level_active = False
                        self._jungle_zone2_active = False
                        self._jungle_unlocked = False
                        self._triggerNewGamePlus = True

                if monster.getName() == "greenBlob" and monster.getHeight() == 100:
                    self.greenBlobs.append(
                        GreenBlob(monster.getXPosition() - 40, 350, 70, 100, self.screen, self.blob_jump_sound))
                    self.greenBlobs.append(
                        GreenBlob(monster.getXPosition() + 40, 350, 70, 100, self.screen, self.blob_jump_sound))
                elif monster.getName() == "bigMummy":
                    self.keys.append(
                        KeyItem(self.screen, monster.getXPosition(), monster.getYPosition()))
                    # Boss drops 5 coins
                    for _ci in range(5):
                        self.coins.append(Coin(monster.getXPosition() + 10 + _ci * 28,
                                               monster.getYPosition() + 80, self.screen))
                    self._bigMummyDefeated = True
                    self._start_ambient_loop()
                    self._switch_music("normal")

            # ---- Mini FrankenBear laser generation and drawing ----------------
            if not _popup_active:
                for minibear in self.miniFrankenBears:
                    if minibear.should_throw_laser():
                        self.lasers.append(minibear.throw_laser(bear.getXPosition()))
                        if self.laser_zap_sound: self.laser_zap_sound.play()

            laser_to_remove = []
            for laser in self.lasers:
                if _popup_active:
                    laser.draw_frozen()
                    continue
                if not laser.draw():
                    laser_to_remove.append(laser)
                    if hasattr(laser, '_owner') and laser._owner:
                        laser._owner.has_thrown_laser = False
                else:
                    laser_hit = False
                    laser_rect_top = laser.getYPosition() - 20
                    laser_rect_bot = laser.getYPosition() + 20
                    bear_feet = bear.getYPosition() + 100
                    bear_top = bear.getYPosition()
                    bear_left = bear.getXPosition()
                    bear_right = bear.getXPosition() + 100
                    
                    if (bear_feet > laser_rect_top and bear_top < laser_rect_bot
                            and bear_right > laser.getStartX() and bear_left < laser.getEndX()
                            and hurtTimer > 60):
                        _laser_dmg = max(6, int(bear.getMaxHp() * 0.10))
                        if getattr(self, 'bear_hurt_sound', None): self.bear_hurt_sound.play()
                        bear.displayDamageOnBear(_laser_dmg, "laser")
                        bear.applyDamage(_laser_dmg)
                        hurtTimer = 0
                        laser_hit = True
                    
                    if laser_hit:
                        laser_to_remove.append(laser)
            
            for laser in laser_to_remove:
                if laser in self.lasers:
                    self.lasers.remove(laser)
                    if hasattr(laser, '_owner') and laser._owner:
                        laser._owner.has_thrown_laser = False

            # ---- Deflect indicator for big mummy body hits (drawn on top) ------
            if deflectTimer > 0:
                self.screen.blit(self.deflectIcon, deflectPos)
                deflectTimer -= 1

            # ---- Boss lifecycle ------------------------------------------
            boss_to_remove = []
            for monster in self.frankenbear:
                if (monster.getHealth() <= 0
                        and monster.getDestructionAnimationCount() < 20
                        and not monster.getStartDestructionAnimationStatus()):
                    monster.setStartDestructionAnimation(True)
                    if getattr(self, 'boss_explosion_sound', None):
                        self.boss_explosion_sound.play()
                elif monster.getStartDestructionAnimationStatus():
                    _boss_death_dmg = monster.getDamageReceived() if monster.getDamageReceived() > 0 else bear.getDamageAttack()
                    monster.drawDestruction(_boss_death_dmg)
                    if monster.getDestructionAnimationCount() == 20 and getattr(self, 'boss_explosion_sound', None):
                        self.boss_explosion_sound.play()
                    if monster.getDestructionAnimationCount() >= 70:
                        monster.setStartDestructionAnimation(False)
                        _exp_gain = monster.getExp()
                        if self._hardMode:
                            _exp_gain = int(_exp_gain * 1.75)
                        bear.setCurrentExp(bear.getCurrentExp() + _exp_gain)
                        boss_to_remove.append(monster)
                        self.newGamePlusLevel += 1
                        bear.setArrayText([
                            'FINAL BOSS DEFEATED!', '',
                            'NEW GAME + ' + str(self.newGamePlusLevel) + ' UNLOCKED!',
                            '', 'The world grows stronger...', '',
                            'Press "s" to continue'])
                        bear.setEndText(False)
                        self.isFinalBossDestroyed = True
                        self._triggerNewGamePlus = True
            for monster in boss_to_remove:
                if monster in self.frankenbear:
                    self.frankenbear.remove(monster)

            # ---- Keys and collectibles ----------------------------------
            for key in self.keys:
                key.drawKey()
                key.boundaryExtraCheck()
                if key.isKeyGrabbed(bear.getXPosition(), bear.getYPosition(),
                                     key.getXPosition(), key.getYPosition()):
                    self.keys.remove(key)
                    self.isDoor1Open = True
                    if self.key_pickup_sound: self.key_pickup_sound.play()
                    if self.door_open_sound: self.door_open_sound.play()

            # ---- Coins (collectibles) -----------------------------------
            coins_to_remove = []
            for coin in self.coins:
                coin.setBlocks(self.blocks)
                coin.update()
                coin.draw()
                if coin.is_grabbed(bear.getXPosition(), bear.getYPosition()):
                    coins_to_remove.append(coin)
                    bear.setCoins(bear.getCoins() + 1)
                    if getattr(self, 'coin_sound', None):
                        self.coin_sound.play()
                    if not self._first_coin_popup_shown:
                        self._first_coin_popup_shown = True
                        bear.setArrayText(['You got a coin!',
                                           'Press RETURN to open the Shop',
                                           'and spend your coins!',
                                           'Press "s" to continue'])
                        bear.setEndText(False)
            for coin in coins_to_remove:
                if coin in self.coins:
                    self.coins.remove(coin)

            # ---- Witch fireballs (safe iteration) -----------------------
            fires_to_remove = []
            for fire in self.fires:
                fire.drawFireBall()
                if (fire.getXPosition() < 30 or fire.getXPosition() > 500
                        or fire.getYPosition() < 0):
                    self.triggerFire = True
                    fires_to_remove.append(fire)
            for fire in fires_to_remove:
                if fire in self.fires:
                    self.fires.remove(fire)

            if self.triggerFire and not self.fires and self.witches:
                self.triggerFire = False
                _beam_fired = False
                for witch in self.witches:
                    witch.setThrowsFireBalls(True)
                    if self.witch_cast_sound:
                        self.witch_cast_sound.play()
                    if not _beam_fired and not self.witch_beams and random.random() < 0.15:
                        _beam_fired = True
                        _wb_x1 = witch.getXPosition() + 50
                        _wb_y1 = witch.getYPosition() + 50
                        _wb_dir = 1 if bear.getXPosition() > witch.getXPosition() else -1
                        _wb_x2 = _wb_x1 + _wb_dir * random.randint(200, 400)
                        _wb_y2 = 400.0
                        self.witch_beams.append({
                            'x1': _wb_x1, 'y1': _wb_y1, 'x2': _wb_x2, 'y2': _wb_y2,
                            'life': 50, 'progress': 0.0, 'hit': False
                        })
                        if getattr(self, 'witch_beam_sound', None):
                            self.witch_beam_sound.play()
                    for _ in range(1):
                        _fb = FireBall(witch.getXPosition(), witch.getYPosition(),
                                       random.randint(-7, 7), random.randint(1, 12),
                                       self.fireBall, self.screen)
                        _fb.damageAttack = max(4, int(bear.getMaxHp() * 0.05))
                        if getattr(self, '_hardMode', False):
                            _fb.damageAttack = int(_fb.damageAttack * 1.8)
                        _fb._bounce_sound = self.fireball_bounce_sound
                        self.fires.append(_fb)

            # ---- Player fireballs -----------------------------------------
            pf_to_remove = []
            for pf in self.playerFires:
                pf.drawFireBall()
                pf_x = pf.getXPosition()
                pf_y = pf.getYPosition()
                if pf_x < -100 or pf_x > 1000 or pf_y < 0 or pf_y > 500:
                    pf_to_remove.append(pf)
                    continue
                pf_rect = pygame.Rect(pf_x, pf_y, 60, 60)
                monsters = (self.mummys + self.witches +
                            self.greenBlobs + self.frankenbear + self.shadowShamans + self.miniFrankenBears + self.snakes + self.monkey_mummies + self.lions)
                for monster in monsters:
                    m_rect = pygame.Rect(monster.getXPosition(),
                                         monster.getYPosition(), 80, 100)
                    if pf_rect.colliderect(m_rect):
                        _fb_dmg = bear.fireballDamage
                        _is_crit = random.random() < 0.20
                        if _is_crit:
                            _fb_dmg *= 2
                        monster.setDamageReceived(_fb_dmg)
                        monster.setStunned(1)
                        monster.setHealth(monster.getHealth() - _apply_defense(monster, _fb_dmg))
                        if _is_crit and self.crit_sound:
                            self.crit_sound.play()
                        else:
                            _snd = self.boss_hit_sound if monster in self.frankenbear else self.hit_sound
                            if _snd: _snd.play()
                        pf_to_remove.append(pf)
                        break
                
                # Check destroyable blocks too
                for db in self.destroyable_blocks:
                    db_rect = pygame.Rect(db.getBlockXPosition(), db.getBlockYPosition(),
                                         db.getWidth(), db.getHeight())
                    if pf_rect.colliderect(db_rect) and db.getHealth() > 0:
                        db.setHealth(db.getHealth() - 1)
                        db.setDamageReceived(1)
                        if self.hit_sound:
                            self.hit_sound.play()
                        pf_to_remove.append(pf)
                        break
            for pf in pf_to_remove:
                if pf in self.playerFires:
                    self.playerFires.remove(pf)

            # ---- Beam projectiles -------------------------------------------
            bp_to_remove = []
            for bp in self.beamProjectiles:
                bp["x"] += bp["vx"]
                bp["timer"] -= 1
                _bw, _bh = 120, 30
                _by = bp["y"]
                _glow = pygame.Surface((_bw + 20, _bh + 20), pygame.SRCALPHA)
                pygame.draw.ellipse(_glow, (100, 200, 255, 60), (0, 0, _bw + 20, _bh + 20))
                self.screen.blit(_glow, (bp["x"] - 10, _by - 10))
                _core = pygame.Surface((_bw, _bh), pygame.SRCALPHA)
                pygame.draw.ellipse(_core, (180, 230, 255, 220), (0, 0, _bw, _bh))
                pygame.draw.ellipse(_core, (255, 255, 255, 200), (10, 5, _bw - 20, _bh - 10))
                self.screen.blit(_core, (bp["x"], _by))
                if bp["x"] < -150 or bp["x"] > 1050 or bp["timer"] <= 0:
                    bp_to_remove.append(bp)
                    continue
                bp_rect = pygame.Rect(bp["x"], _by, _bw, _bh)
                monsters = (self.mummys + self.witches +
                            self.greenBlobs + self.frankenbear + self.shadowShamans + self.miniFrankenBears + self.snakes + self.monkey_mummies + self.lions)
                for monster in monsters:
                    _mid = id(monster)
                    if _mid in bp["hit_ids"]:
                        continue
                    m_rect = pygame.Rect(monster.getXPosition(),
                                         monster.getYPosition(), 80, 100)
                    if bp_rect.colliderect(m_rect):
                        bp["hit_ids"].add(_mid)
                        _beam_hit_dmg = bp["dmg"]
                        if isinstance(monster, MiniFrankenBear):
                            _beam_hit_dmg = int(_beam_hit_dmg * 1.5)
                        monster.setDamageReceived(_beam_hit_dmg)
                        monster.setStunned(3)
                        monster.setHealth(monster.getHealth() - _apply_defense(monster, _beam_hit_dmg))
                
                # Check destroyable blocks too
                for db in self.destroyable_blocks:
                    if db.getHealth() > 0:
                        db_rect = pygame.Rect(db.getBlockXPosition(), db.getBlockYPosition(),
                                             db.getWidth(), db.getHeight())
                        if bp_rect.colliderect(db_rect):
                            db.setHealth(db.getHealth() - 1)
                            db.setDamageReceived(1)
            for bp in bp_to_remove:
                if bp in self.beamProjectiles:
                    self.beamProjectiles.remove(bp)

            # ---- Lion drawing and contact detection ----------------------------
            for lion in self.lions:
                if lion.getHealth() > 0:
                    lion_rect = pygame.Rect(lion.getXPosition(), lion.getYPosition(), lion.width, lion.height)
                    bear_rect_l = pygame.Rect(bear.getXPosition(), bear.getYPosition(), 100, 100)
                    if lion_rect.colliderect(bear_rect_l) and hurtTimer > 60:
                        _lion_dmg = lion.damageAttack
                        bear.displayDamageOnBear(_lion_dmg, "lion")
                        bear.setHp(bear.getHp() - _lion_dmg)
                        hurtTimer = 0

            # ---- Snake poison contact detection ----------------------------
            try:
                for snake in self.snakes:
                    if snake.getHealth() > 0:
                        if hasattr(snake, 'update_poison_cooldown'):
                            snake.update_poison_cooldown()
                        snake_rect = pygame.Rect(snake.getXPosition(), snake.getYPosition(), snake.width, snake.height)
                        bear_rect = pygame.Rect(bear.getXPosition(), bear.getYPosition(), 100, 100)
                        if snake_rect.colliderect(bear_rect) and snake.get_poison_cooldown() == 0:
                            bear.set_poison(30)
                            snake.set_poison_cooldown(120)
                if hasattr(bear, 'update_poison') and hasattr(bear, 'poison_timer') and bear.poison_timer > 0:
                    _hp_pre = bear.getHp()
                    bear.update_poison()
                    if bear.getHp() < _hp_pre:
                        self._poison_floats.append({
                            'x': bear.getXPosition() + random.randint(-15, 15),
                            'y': bear.getYPosition() - 10,
                            'timer': 55
                        })

                _fin_font = get_font('damage')
                for _pf in self._poison_floats:
                    _pf['y'] -= 1
                    _pf['timer'] -= 1
                    _alpha = max(0, int(255 * (_pf['timer'] / 55.0)))
                    if _fin_font:
                        _fs = _fin_font.render('-2', True, (80, 230, 80))
                        _fs.set_alpha(_alpha)
                        self.screen.blit(_fs, (int(_pf['x']), int(_pf['y'])))
                self._poison_floats = [f for f in self._poison_floats if f['timer'] > 0]

                if hasattr(bear, 'is_poisoned') and bear.is_poisoned():
                    _ptick = getattr(bear, 'poison_damage_tick', 0)
                    _pulse = (_ptick % 30) / 30.0
                    _p_alpha = int(45 + 45 * (1 - abs(2 * _pulse - 1)))
                    _p_ov = pygame.Surface((80, 100), pygame.SRCALPHA)
                    _p_ov.fill((40, 220, 40, _p_alpha))
                    self.screen.blit(_p_ov, (bear.getXPosition(), bear.getYPosition()),
                                     special_flags=pygame.BLEND_RGBA_ADD)
                    _poi_font = pygame.font.SysFont(None, 20, bold=True)
                    _poi_surf = _poi_font.render('POISONED', True, (80, 230, 80))
                    _poi_alpha = int(160 + 95 * (1 - abs(2 * _pulse - 1)))
                    _poi_surf.set_alpha(_poi_alpha)
                    self.screen.blit(_poi_surf, (bear.getXPosition() - 10, bear.getYPosition() - 32))
            except Exception as _poison_err:
                pass

            if not _popup_active:
                for snake in self.snakes:
                    if snake.getHealth() > 0 and snake.should_spit_venom():
                        _vb = snake.spit_venom()
                        self.venom_balls.append(_vb)

            _vb_remove = []
            _bear_rect_vb = pygame.Rect(bear.getXPosition(), bear.getYPosition(), 100, 100)
            for _vb in self.venom_balls:
                if _popup_active:
                    _vb.draw_frozen()
                    continue
                if not _vb.update():
                    _vb_remove.append(_vb)
                elif _vb.get_rect().colliderect(_bear_rect_vb):
                    if hurtTimer > 60:
                        bear.set_poison(30)
                        bear.setHp(bear.getHp() - 4)
                        hurtTimer = 0
                        if getattr(self, 'bear_hurt_sound', None):
                            self.bear_hurt_sound.play()
                    _vb_remove.append(_vb)
            for _vb in _vb_remove:
                if _vb in self.venom_balls:
                    self.venom_balls.remove(_vb)

            if not _popup_active and self.shadowShamans:
                for _sh in self.shadowShamans:
                    if _sh.getHealth() <= 0:
                        continue
                    if not hasattr(_sh, '_orb_cd'):
                        _sh._orb_cd = random.randint(120, 240)
                    _sh._orb_cd -= 1
                    if _sh._orb_cd <= 0 and abs(_sh.getXPosition() - bear.getXPosition()) < 500:
                        _sh._orb_cd = random.randint(200, 280)
                        _sx, _sy = _sh.getXPosition() + 60, _sh.getYPosition() + 60
                        _pattern = random.choice(['radial', 'spiral', 'cross', 'aimed'])
                        _num_orbs = random.randint(6, 10)
                        _base_dmg = max(6, int(bear.getMaxHp() * 0.08))
                        _dx_t = bear.getXPosition() + 50 - _sx
                        _dy_t = bear.getYPosition() + 50 - _sy
                        _aim_angle = math.atan2(_dy_t, _dx_t)
                        for _oi in range(_num_orbs):
                            if _pattern == 'radial':
                                _angle = (2 * math.pi * _oi / _num_orbs)
                                _spd = random.uniform(2.5, 4.5)
                            elif _pattern == 'spiral':
                                _angle = (2 * math.pi * _oi / _num_orbs) + _oi * 0.3
                                _spd = 2.0 + _oi * 0.4
                            elif _pattern == 'cross':
                                _arm = _oi % 4
                                _idx = _oi // 4
                                _angle = _arm * (math.pi / 2) + _aim_angle
                                _spd = 2.5 + _idx * 1.5
                            else:
                                _spread = (_oi - _num_orbs / 2.0) * 0.15
                                _angle = _aim_angle + _spread
                                _spd = random.uniform(3.0, 5.0)
                            _orb_vx = math.cos(_angle) * _spd
                            _orb_vy = math.sin(_angle) * _spd
                            _orb_cols = [(50, 200, 50), (80, 255, 80), (30, 180, 120), (100, 255, 50)]
                            self.shaman_orbs.append({
                                'x': _sx, 'y': _sy, 'vx': _orb_vx, 'vy': _orb_vy,
                                'life': 140, 'phase': _oi * (2 * math.pi / _num_orbs),
                                'orbit_r': random.uniform(15, 50),
                                'center_x': _sx, 'center_y': _sy,
                                'dmg': _base_dmg,
                                'color': random.choice(_orb_cols)
                            })

            _orbs_remove = []
            _bear_rect_orb = pygame.Rect(bear.getXPosition(), bear.getYPosition(), 100, 100)
            for _orb in self.shaman_orbs:
                if _popup_active:
                    pygame.draw.circle(self.screen, (100, 255, 100), (int(_orb['x']), int(_orb['y'])), 10)
                    pygame.draw.circle(self.screen, (200, 255, 200), (int(_orb['x']), int(_orb['y'])), 5)
                    continue
                _orb['life'] -= 1
                _orb['center_x'] += _orb['vx']
                _orb['center_y'] += _orb['vy']
                _orb['vy'] += 0.02
                _orb_wave = math.sin(pygame.time.get_ticks() * 0.01 + _orb['phase']) * _orb['orbit_r']
                _orb['x'] = _orb['center_x'] + math.cos(_orb['phase'] + pygame.time.get_ticks() * 0.005) * _orb_wave * 0.5
                _orb['y'] = _orb['center_y'] + math.sin(_orb['phase'] + pygame.time.get_ticks() * 0.005) * _orb_wave * 0.5
                _orb_alpha = min(255, max(60, _orb['life'] * 4))
                _oc = _orb.get('color', (50, 200, 50))
                _oc_bright = (min(255, _oc[0]+100), min(255, _oc[1]+55), min(255, _oc[2]+100))
                _oc_core = (min(255, _oc[0]+170), min(255, _oc[1]+55), min(255, _oc[2]+170))
                _orb_s = pygame.Surface((24, 24), pygame.SRCALPHA)
                pygame.draw.circle(_orb_s, (_oc[0], _oc[1], _oc[2], _orb_alpha), (12, 12), 12)
                pygame.draw.circle(_orb_s, (_oc_bright[0], _oc_bright[1], _oc_bright[2], min(255, _orb_alpha + 40)), (12, 12), 7)
                pygame.draw.circle(_orb_s, (_oc_core[0], _oc_core[1], _oc_core[2], min(255, _orb_alpha + 80)), (12, 12), 3)
                self.screen.blit(_orb_s, (int(_orb['x']) - 12, int(_orb['y']) - 12))
                _orb_trail = pygame.Surface((6, 6), pygame.SRCALPHA)
                _orb_trail.fill((_oc[0], min(255, _oc[1]+55), _oc[2], max(30, _orb_alpha // 3)))
                self.screen.blit(_orb_trail, (int(_orb['x'] - _orb['vx'] * 2) - 3, int(_orb['y'] - _orb['vy'] * 2) - 3))
                if _orb['life'] <= 0 or _orb['x'] < -50 or _orb['x'] > 960 or _orb['y'] > 450:
                    _orbs_remove.append(_orb)
                elif pygame.Rect(int(_orb['x']) - 10, int(_orb['y']) - 10, 20, 20).colliderect(_bear_rect_orb):
                    if hurtTimer > 60:
                        bear.applyDamage(_orb['dmg'])
                        bear.displayDamageOnBear(_orb['dmg'], "shaman")
                        hurtTimer = 0
                        if getattr(self, 'bear_hurt_sound', None):
                            self.bear_hurt_sound.play()
                    _orbs_remove.append(_orb)
            for _orb in _orbs_remove:
                if _orb in self.shaman_orbs:
                    self.shaman_orbs.remove(_orb)

            _beams_remove = []
            for _wb in self.witch_beams:
                if _popup_active:
                    pygame.draw.line(self.screen, (200, 50, 255),
                                     (int(_wb['x1']), int(_wb['y1'])),
                                     (int(_wb['x2']), int(_wb['y2'])), 4)
                    continue
                _wb['life'] -= 1
                _wb['progress'] = min(1.0, _wb['progress'] + 0.05)
                _cur_x2 = _wb['x1'] + (_wb['x2'] - _wb['x1']) * _wb['progress']
                _cur_y2 = _wb['y1'] + (_wb['y2'] - _wb['y1']) * _wb['progress']
                _beam_alpha = min(255, max(40, _wb['life'] * 6))
                _beam_thick = 6 if _wb['life'] > 20 else 4
                _beam_s = pygame.Surface((900, 700), pygame.SRCALPHA)
                pygame.draw.line(_beam_s, (200, 50, 255, _beam_alpha),
                                 (int(_wb['x1']), int(_wb['y1'])),
                                 (int(_cur_x2), int(_cur_y2)), _beam_thick)
                pygame.draw.line(_beam_s, (255, 150, 255, min(255, _beam_alpha + 40)),
                                 (int(_wb['x1']), int(_wb['y1'])),
                                 (int(_cur_x2), int(_cur_y2)), max(1, _beam_thick // 2))
                _spark_x = int(_cur_x2)
                _spark_y = int(_cur_y2)
                if _wb['progress'] >= 1.0 and _wb['life'] > 10:
                    for _ in range(3):
                        _sp_s = pygame.Surface((6, 6), pygame.SRCALPHA)
                        pygame.draw.circle(_sp_s, (255, 200, 255, _beam_alpha), (3, 3), 3)
                        _beam_s.blit(_sp_s, (_spark_x + random.randint(-8, 8) - 3, _spark_y + random.randint(-8, 8) - 3))
                self.screen.blit(_beam_s, (0, 0))
                if _wb['progress'] >= 0.3:
                    _bx1, _by1 = int(_wb['x1']), int(_wb['y1'])
                    _bx2, _by2 = int(_cur_x2), int(_cur_y2)
                    _bear_cx_b = bear.getXPosition() + 50
                    _bear_cy_b = bear.getYPosition() + 50
                    _ldx = _bx2 - _bx1
                    _ldy = _by2 - _by1
                    _llen = math.sqrt(_ldx*_ldx + _ldy*_ldy)
                    if _llen > 0:
                        _t = max(0, min(1, ((_bear_cx_b - _bx1)*_ldx + (_bear_cy_b - _by1)*_ldy) / (_llen*_llen)))
                        _closest_x = _bx1 + _t * _ldx
                        _closest_y = _by1 + _t * _ldy
                        _pdist = math.sqrt((_bear_cx_b - _closest_x)**2 + (_bear_cy_b - _closest_y)**2)
                        if _pdist < 40 and hurtTimer > 60 and not _wb.get('hit', False):
                            _wb['hit'] = True
                            _beam_dmg = max(5, int(bear.getMaxHp() * 0.10))
                            bear.applyDamage(_beam_dmg)
                            bear.displayDamageOnBear(_beam_dmg, "beam")
                            hurtTimer = 0
                            if getattr(self, 'bear_hurt_sound', None):
                                self.bear_hurt_sound.play()
                if _wb['life'] <= 0:
                    _beams_remove.append(_wb)
            for _wb in _beams_remove:
                if _wb in self.witch_beams:
                    self.witch_beams.remove(_wb)

            _hd_remove = []
            for _hd in self.heart_drops:
                if _popup_active:
                    _hx, _hy = int(_hd['x']), int(_hd['y'])
                    pygame.draw.polygon(self.screen, (255, 50, 80), [
                        (_hx, _hy + 4), (_hx - 8, _hy - 4), (_hx - 5, _hy - 10),
                        (_hx, _hy - 6), (_hx + 5, _hy - 10), (_hx + 8, _hy - 4)])
                    continue
                if not _hd['landed']:
                    _hd['vy'] += 0.2
                    _hd['y'] += _hd['vy']
                    if _hd['y'] >= 385:
                        _hd['y'] = 385.0
                        _hd['landed'] = True
                        _hd['vy'] = 0.0
                _hd['life'] -= 1
                _hx, _hy = int(_hd['x']), int(_hd['y'])
                _hd_pulse = abs(math.sin(pygame.time.get_ticks() * 0.006)) * 3
                _hr = int(12 + _hd_pulse)
                _heart_s = pygame.Surface((_hr*2+4, _hr*2+4), pygame.SRCALPHA)
                _hcx, _hcy = _hr+2, _hr+2
                pygame.draw.circle(_heart_s, (255, 50, 80, 220), (_hcx - _hr//3, _hcy - _hr//4), _hr//2 + 1)
                pygame.draw.circle(_heart_s, (255, 50, 80, 220), (_hcx + _hr//3, _hcy - _hr//4), _hr//2 + 1)
                pygame.draw.polygon(_heart_s, (255, 50, 80, 220), [
                    (_hcx - _hr, _hcy - 1), (_hcx, _hcy + _hr), (_hcx + _hr, _hcy - 1)])
                _plus_txt = _FONT_HUD.render('+10', True, (255, 255, 255))
                _heart_s.blit(_plus_txt, (_hcx - _plus_txt.get_width()//2, _hcy - _plus_txt.get_height()//2))
                self.screen.blit(_heart_s, (_hx - _hcx, _hy - _hcy))
                if _hd['life'] <= 0:
                    _hd_remove.append(_hd)
                elif _hd['landed']:
                    _hd_rect = pygame.Rect(_hx - 15, _hy - 15, 30, 30)
                    if _hd_rect.colliderect(pygame.Rect(bear.getXPosition(), bear.getYPosition(), 100, 100)):
                        bear.setHp(min(bear.getMaxHp(), bear.getHp() + 10))
                        bear.setCoins(bear.getCoins() + 1)
                        if getattr(self, 'coin_sound', None):
                            self.coin_sound.play()
                        _hd_remove.append(_hd)
            for _hd in _hd_remove:
                if _hd in self.heart_drops:
                    self.heart_drops.remove(_hd)

            if not _popup_active and totalDistance < 30000 and totalDistance > 500:
                self._bomb_spawn_timer += 1
                _bomb_interval = 1800
                if self._bomb_spawn_timer >= _bomb_interval:
                    self._bomb_spawn_timer = 0
                    import random as _br
                    _bear_bx = bear.getXPosition() + 50
                    _bx = max(30, min(870, _bear_bx + _br.randint(50, 250) * _br.choice([-1, 1])))
                    _is_big = _br.random() < 0.20
                    _timer_secs = _br.choice([1, 2, 3])
                    self.bombs.append({
                        'x': float(_bx), 'y': -40.0, 'vy': 3.0,
                        'landed': False, 'timer': _timer_secs * 60,
                        'exploding': False, 'explode_anim': 0,
                        'big': _is_big
                    })

            _bombs_remove = []
            _bear_cx = bear.getXPosition() + 50
            _bear_cy = bear.getYPosition() + 50
            for _bomb in self.bombs:
                if _popup_active:
                    _bx_i = int(_bomb['x'])
                    _by_i = int(_bomb['y'])
                    if _bomb['exploding']:
                        _ea = _bomb['explode_anim']
                        _er = min(80, _ea * 4)
                        _alpha = max(0, 255 - _ea * 8)
                        _es = pygame.Surface((_er*2, _er*2), pygame.SRCALPHA)
                        pygame.draw.circle(_es, (255, 120, 0, _alpha), (_er, _er), _er)
                        pygame.draw.circle(_es, (255, 220, 50, min(255, _alpha+30)), (_er, _er), max(1, _er//2))
                        self.screen.blit(_es, (_bx_i - _er, _by_i - _er))
                    elif _bomb['landed']:
                        pygame.draw.circle(self.screen, (40, 40, 40), (_bx_i, _by_i), 18)
                        pygame.draw.circle(self.screen, (80, 80, 80), (_bx_i, _by_i), 14)
                        pygame.draw.circle(self.screen, (200, 50, 50), (_bx_i, _by_i - 22), 5)
                        _secs = max(0, (_bomb['timer'] + 59) // 60)
                        _ct = _FONT_HUD.render(str(_secs), True, (255, 255, 255))
                        self.screen.blit(_ct, (_bx_i - _ct.get_width()//2, _by_i - _ct.get_height()//2))
                    else:
                        pygame.draw.circle(self.screen, (40, 40, 40), (_bx_i, _by_i), 16)
                        pygame.draw.circle(self.screen, (80, 80, 80), (_bx_i, _by_i), 12)
                        pygame.draw.circle(self.screen, (200, 50, 50), (_bx_i, _by_i - 18), 4)
                    continue

                _b_big = _bomb.get('big', False)
                _b_radius = 28 if _b_big else 18
                _b_inner = 22 if _b_big else 14
                _b_fuse_r = 7 if _b_big else 5
                _b_explode_radius = 160 if _b_big else 120

                if _bomb['exploding']:
                    _bomb['explode_anim'] += 1
                    _ea = _bomb['explode_anim']
                    _max_er = 120 if _b_big else 80
                    _er = min(_max_er, _ea * (6 if _b_big else 4))
                    _alpha = max(0, 255 - _ea * 8)
                    _es = pygame.Surface((_er*2, _er*2), pygame.SRCALPHA)
                    if _b_big:
                        pygame.draw.circle(_es, (180, 0, 200, _alpha), (_er, _er), _er)
                        pygame.draw.circle(_es, (255, 80, 255, min(255, _alpha+30)), (_er, _er), max(1, _er//2))
                        pygame.draw.circle(_es, (255, 220, 255, min(255, _alpha+50)), (_er, _er), max(1, _er//3))
                    else:
                        pygame.draw.circle(_es, (255, 120, 0, _alpha), (_er, _er), _er)
                        pygame.draw.circle(_es, (255, 220, 50, min(255, _alpha+30)), (_er, _er), max(1, _er//2))
                    self.screen.blit(_es, (int(_bomb['x']) - _er, int(_bomb['y']) - _er))
                    if _ea >= 30:
                        _bombs_remove.append(_bomb)
                elif _bomb['landed']:
                    _bomb['timer'] -= 1
                    _bx_i = int(_bomb['x'])
                    _by_i = int(_bomb['y'])
                    _pulse = abs(math.sin(pygame.time.get_ticks() * 0.008)) * 0.3
                    _secs = max(0, (_bomb['timer'] + 59) // 60)
                    if _b_big:
                        _flash = (180, 0, 200) if _bomb['timer'] < 60 and _bomb['timer'] % 10 < 5 else (60, 0, 80)
                    else:
                        _flash = (255, 60, 60) if _bomb['timer'] < 60 and _bomb['timer'] % 10 < 5 else (40, 40, 40)
                    pygame.draw.circle(self.screen, _flash, (_bx_i, _by_i), int(_b_radius + _pulse * 4))
                    pygame.draw.circle(self.screen, (80, 80, 80) if not _b_big else (120, 60, 140), (_bx_i, _by_i), _b_inner)
                    if _b_big:
                        _skull_col = (255, 200, 255)
                        pygame.draw.circle(self.screen, _skull_col, (_bx_i - 4, _by_i - 4), 3)
                        pygame.draw.circle(self.screen, _skull_col, (_bx_i + 4, _by_i - 4), 3)
                        pygame.draw.line(self.screen, _skull_col, (_bx_i - 3, _by_i + 4), (_bx_i + 3, _by_i + 4), 2)
                    pygame.draw.circle(self.screen, (200, 50, 50), (_bx_i, _by_i - _b_radius - 4), _b_fuse_r)
                    _fuse_glow = int(abs(math.sin(pygame.time.get_ticks() * 0.015)) * 80)
                    pygame.draw.circle(self.screen, (255, 200 + min(55, _fuse_glow), 50), (_bx_i, _by_i - _b_radius - 6), max(2, _b_fuse_r - 2))
                    _ct = _FONT_HUD.render(str(_secs), True, (255, 255, 255))
                    _ct_outline = _FONT_HUD.render(str(_secs), True, (0, 0, 0))
                    for _ox, _oy in [(-1,0),(1,0),(0,-1),(0,1)]:
                        self.screen.blit(_ct_outline, (_bx_i - _ct.get_width()//2 + _ox, _by_i - _ct.get_height()//2 + _oy))
                    self.screen.blit(_ct, (_bx_i - _ct.get_width()//2, _by_i - _ct.get_height()//2))

                    if _bomb['timer'] <= 0:
                        _bomb['exploding'] = True
                        _bomb['explode_anim'] = 0
                        if getattr(self, 'explosion_sound', None):
                            self.explosion_sound.play()
                        _dx_b = _bear_cx - _bomb['x']
                        _dy_b = _bear_cy - _bomb['y']
                        _dist_b = math.sqrt(_dx_b*_dx_b + _dy_b*_dy_b)
                        if _dist_b < _b_explode_radius and hurtTimer > 60:
                            _bomb_pct = 0.40 if _b_big else 0.30
                            _bomb_dmg = max(8, int(bear.getMaxHp() * _bomb_pct))
                            bear.applyDamage(_bomb_dmg)
                            bear.displayDamageOnBear(_bomb_dmg, "bomb")
                            hurtTimer = 0
                            if getattr(self, 'bear_hurt_sound', None):
                                self.bear_hurt_sound.play()
                else:
                    _bomb['y'] += _bomb['vy']
                    _bomb['vy'] += 0.15
                    if _bomb['y'] >= 385:
                        _bomb['y'] = 385.0
                        _bomb['landed'] = True
                        _bomb['vy'] = 0.0
                    _bx_i = int(_bomb['x'])
                    _by_i = int(_bomb['y'])
                    _fall_r = 24 if _b_big else 16
                    _fall_inner = 18 if _b_big else 12
                    _fall_fuse = 6 if _b_big else 4
                    _fall_col = (60, 0, 80) if _b_big else (40, 40, 40)
                    _fall_inner_col = (120, 60, 140) if _b_big else (80, 80, 80)
                    pygame.draw.circle(self.screen, _fall_col, (_bx_i, _by_i), _fall_r)
                    pygame.draw.circle(self.screen, _fall_inner_col, (_bx_i, _by_i), _fall_inner)
                    pygame.draw.circle(self.screen, (200, 50, 50), (_bx_i, _by_i - _fall_r - 2), _fall_fuse)
                    _trail_alpha = max(0, 180 - int(_bomb['vy'] * 15))
                    if _trail_alpha > 30:
                        _tw = 12 if _b_big else 8
                        _th = 24 if _b_big else 16
                        _ts = pygame.Surface((_tw, _th), pygame.SRCALPHA)
                        _trail_col = (200, 80, 255, _trail_alpha) if _b_big else (255, 160, 50, _trail_alpha)
                        _ts.fill(_trail_col)
                        self.screen.blit(_ts, (_bx_i - _tw//2, _by_i - _fall_r - _th))

            for _bomb in _bombs_remove:
                if _bomb in self.bombs:
                    self.bombs.remove(_bomb)

            if (totalDistance > 30000 and not getattr(self, '_checkpoint_saved', False)
                    and bear.getEndText() and not self.escape
                    and not getattr(self, '_monkey_level_active', False)):
                self._save_checkpoint(backgroundScrollX, totalDistance, bear)
                self._switch_music("deep_crypt")
                bear.setArrayText(['GAME SAVED!', '',
                                   'Checkpoint reached at 50%.',
                                   'Press "s" to continue'])
                bear.setEndText(False)

            if bear.getCoins() == 42 and not self._easter_egg_42 and bear.getEndText():
                self._easter_egg_42 = True
                bear.setArrayText(['Nice, 42 coins!',
                                   'The answer to life is hidden.',
                                   'Press "s" to continue'])
                bear.setEndText(False)
            # Every 100 coins: full health restore + 100 max HP
            if bear.getEndText():
                _coin_milestone = bear.getCoins() // 100
                if _coin_milestone > self._last_coin_milestone:
                    self._last_coin_milestone = _coin_milestone
                    bear.setMaxHp(bear.getMaxHp() + 100)
                    bear.setHp(bear.getMaxHp())
                    bear.setArrayText([str(_coin_milestone * 100) + ' COINS!',
                                       '+100 Max HP! Full health restored!',
                                       'Press "s" to continue'])
                    bear.setEndText(False)
            if bear.getLevel() == 13 and not self._easter_egg_13 and bear.getEndText():
                self._easter_egg_13 = True
                bear.setArrayText(['Lucky thirteen!',
                                   'Magic seems to be smiling at you.',
                                   'Press "s" to continue'])
                bear.setEndText(False)

            if bear.getEndText():
                hurtTimer += 1
            else:
                hurtTimer = 0

            _was_in_popup = getattr(self, '_was_in_popup', False)
            if not bear.getEndText():
                self._was_in_popup = True
            elif _was_in_popup:
                self._was_in_popup = False
                hurtTimer = -35

            self._mummy_groan_timer += 1
            if (self._mummy_groan_timer >= 180 and self.mummys
                    and self.mummy_groan_sound):
                import random as _r
                if _r.random() < 0.3:
                    self.mummy_groan_sound.play()
                self._mummy_groan_timer = 0

            # ---- Boss trigger zone (scaled to STEP-based totalDistance) --
            # Original triggers were designed for 30px steps; scaled to 8px steps
            # by multiplying by (8/30) ≈ 0.267. Zone triggers ÷ ~3.75.
            if 59900 < totalDistance < 60000 and not self.createdBoss:
                self.createdBoss = True

            if totalDistance > 60000 and not self.activeMonsters[9]:
                self.spikes = []
                self.activeMonsters[9] = True
                if getattr(self, 'wave_warning_sound', None): self.wave_warning_sound.play()
                self._switch_music("boss_final")
                self.mummys = []
                self.witches = []
                self.blocks = []
                self.greenBlobs = []
                self.fires = []
                self.bombs = []
                self.shaman_orbs = []
                self.witch_beams = []
                self.heart_drops = []
                self.activeMonsters[1] = True

            if totalDistance > 60000:
                totalDistance = 90000
                background.setStopBackground(True)
                self.leftBoundary = 80
                self.rightBoundary = 700
                self.screen.blit(self.pillar, (-40, 0))
                self.screen.blit(self.pillar, (800, 0))
                self.bossTimerAnimation += 1

                if self.bossTimerAnimation > 30:
                    background.setBlackBackground(True)

                if self.bossTimerAnimation > 170:
                    if self.showBoss:
                        frankenbear = FrankenBear(1400, 40, self.screen)
                        self.frankenbear.append(frankenbear)
                        self.showBoss = False
                        if self.boss_entrance_sound: self.boss_entrance_sound.play()
                    for frankenbear in self.frankenbear:
                        frankenbear._popup_frozen = _popup_active
                        frankenbear.drawMonster()
                        if not _popup_active and (frankenbear.getThrowFireBallLeft() or frankenbear.getThrowFireBallRight()):
                            frankenbear.setThrowFireBallLeft(False)
                            frankenbear.setThrowFireBallRight(False)
                            volley = 6 if frankenbear.getHealth() <= 10 else 4
                            import math as _m
                            _fx = frankenbear.getXPosition() + 200
                            _fy = frankenbear.getYPosition() + 100
                            _bx = bear.getXPosition() + 50
                            _by = bear.getYPosition() + 50
                            _dx = _bx - _fx
                            _dy = _by - _fy
                            _dist = max(1, _m.sqrt(_dx*_dx + _dy*_dy))
                            for _ in range(volley):
                                _speed = random.uniform(6, 11)
                                _spread = random.uniform(-0.25, 0.25)
                                _vx = _speed * (_dx / _dist) + _spread * _speed
                                _vy_raw = _speed * (_dy / _dist)
                                _vy_raw = max(1, abs(_vy_raw)) * (1 if _dy > 0 else -1)
                                _bfb = FireBall(_fx, _fy,
                                             _vx,
                                             _vy_raw,
                                             self.fireBossBall, self.screen)
                                _bfb.damageAttack = max(4, int(bear.getMaxHp() * 0.05))
                                if getattr(self, '_hardMode', False):
                                    _bfb.damageAttack = int(_bfb.damageAttack * 1.8)
                                _bfb._bounce_sound = self.fireball_bounce_sound
                                self.bossFires.append(_bfb)

                    boss_fires_to_remove = []
                    for fire in self.bossFires:
                        if _popup_active:
                            fire.drawFireBallFrozen() if hasattr(fire, 'drawFireBallFrozen') else None
                        else:
                            fire.drawFireBall()
                            if (fire.getXPosition() < 30 or fire.getXPosition() > 800
                                    or fire.getYPosition() < 0):
                                self.triggerFire = True
                                boss_fires_to_remove.append(fire)
                    for fire in boss_fires_to_remove:
                        if fire in self.bossFires:
                            self.bossFires.remove(fire)

                bear.displayBearExp()

            triggerWitchFireBallAnimation += 1
            attackCounterReady += 1

            keys = pygame.key.get_pressed()

            # ---- Platforms and gravity ----------------------------------
            for block in self.blocks:
                # Only run boundary logic on the ground.  While airborne,
                # _jumpPhysics() is the sole authority on vertical state;
                # calling isBoundaryPresent() mid-air can corrupt dropStatus
                # the instant _jumpPhysics() sets jumpStatus=False, causing the
                # bear to fall straight through a platform it just landed on.
                if not bear.getJumpStatus() and not bear.getLeftJumpStatus():
                    block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())

            # ---- Drop-through platform (DOWN key) -----------------------
            if (keys[pygame.K_DOWN]
                    and not bear.getJumpStatus()
                    and not bear.getLeftJumpStatus()
                    and bear.getYPosition() + 100 < floorHeight):
                _on_plat = [b for b in self.blocks if b.getOnPlatform()]
                if _on_plat:
                    bear.jumpVelocity = -2.0
                    bear.setComingUpStatus(False)
                    bear.setJumpStatus(True)
                    for b in self.blocks:
                        b.setDropStatus(False)
                        b.setOnPlatform(False)
                    bear.sourceBlock = _on_plat[0]
                    bear._drop_timer = 40

            # ---- Post-boss platform popup (first time landing on platform after door) --
            if (self._boss_door_passed
                    and not self._post_boss_platform_popup_shown
                    and not bear.getJumpStatus()
                    and not bear.getLeftJumpStatus()
                    and any(b.getOnPlatform() for b in self.blocks)):
                self._post_boss_platform_popup_shown = True
                bear.setArrayText([
                    'Tip: press DOWN while on',
                    'a platform to drop through it!',
                    'Press "s" to continue'])
                bear.setEndText(False)

            # Walk-off-edge detection: if the bear is grounded (not in a jump),
            # not on the floor, and no platform is supporting it, the bear has
            # walked off a platform edge.  Activate fall physics with zero initial
            # velocity so _jumpPhysics() handles gravity and collision detection
            # with its robust frame-crossing check — the same path used for jumps.
            if (not bear.getJumpStatus() and not bear.getLeftJumpStatus()
                    and bear.getYPosition() + 100 < floorHeight
                    and not any(b.getOnPlatform() for b in self.blocks)):
                bear.jumpVelocity = 0.0
                bear.setComingUpStatus(False)
                bear.setJumpStatus(True)
                for b in self.blocks:
                    b.setDropStatus(False)
                # Identify the block the bear just walked off (closest block beneath)
                # and set it as sourceBlock so _jumpPhysics won't re-land on it.
                bear_feet_y = bear.getYPosition() + 100
                closest_block = None
                closest_dist = float('inf')
                for block in self.blocks:
                    bty = block.getBlockYPosition()
                    blx = block.getBlockXPosition()
                    brx = blx + block.getWidth()
                    bear_x = bear.getXPosition()
                    bear_x2 = bear_x + 100
                    # Block must be roughly horizontal to the bear and just below
                    if (bear_x2 > blx and bear_x < brx
                            and bty >= bear_feet_y - 5 and bty <= bear_feet_y + 20):
                        dist = abs(bty - bear_feet_y)
                        if dist < closest_dist:
                            closest_dist = dist
                            closest_block = block
                if closest_block:
                    bear.sourceBlock = closest_block

            for block in self.blocks:
                # Skip drop gravity while jump physics are already controlling
                # vertical movement – double-falling causes the bear to blow
                # through landing windows and fall through platforms.
                if (block.getDropStatus() and not bear.getComingUp()
                        and not bear.getJumpStatus()
                        and not bear.getLeftJumpStatus()):
                    if bear.getYPosition() + 100 < floorHeight:
                        bear.setYPosition(bear.getYPosition() + JUMP_STEP)
                    elif bear.getYPosition() + 100 >= floorHeight:
                        bear.setYPosition(floorHeight - 100)
                        block.setDropStatus(False)
                        block.setOnPlatform(False)
                        bear.setJumpStatus(False)
                        bear.setLeftJumpStatus(False)

            # ---- Damage numbers always rendered on top of blocks --------
            for _m in (self.mummys + self.witches +
                       self.greenBlobs + self.frankenbear +
                       self.shadowShamans + self.miniFrankenBears +
                       self.snakes + self.monkey_mummies + self.lions):
                if not _m.getStartDestructionAnimationStatus():
                    if getattr(_m, 'stunned', 0) and _m.getDamageReceived() > 0:
                        _m.displayDamageOnMonster(_m.getDamageReceived())

            bear.displayBearHp()
            bear.displayBearExp()
            bear.displayBearCoins()
            if (not self._critical_hp_popup_shown
                    and bear.getHp() < bear.getMaxHp() * 0.30
                    and bear.getHp() > 0 and bear.getEndText()):
                self._critical_hp_popup_shown = True
                bear.setArrayText([
                    'CRITICAL HEALTH!', '',
                    'Some enemies drop hearts',
                    'when your health is low.',
                    'Defeat them to recover HP!',
                    '', 'Press "s" to continue'])
                bear.setEndText(False)
            if getattr(self, '_hard_mode_selected', False):
                _hm_font = _FONT_HUD_VAL or pygame.font.SysFont(None, 20, bold=True)
                _hm_surf = _hm_font.render('HARD MODE', True, (255, 80, 80))
                self.screen.blit(_hm_surf, (810 - _hm_surf.get_width(), 680))
            _bc_x, _bc_y, _bc_w, _bc_h = 624, 6, 180, 28
            render_hud_panel(self.screen, _bc_x, _bc_y, _bc_w, _bc_h, (30, 50, 100))
            _bc_ratio = min(1.0, beamCharge / 100.0)
            if _bc_ratio >= 1.0:
                _bc_col = (100, 200, 255)
            else:
                _bc_col = (60, 100, 180)
            render_hud_bar(self.screen, _bc_x + 50, _bc_y + 5, _bc_w - 58, 14, _bc_ratio, _bc_col)
            render_hud_text_outlined(self.screen, _FONT_HUD_VAL, "BEAM",
                               _bc_x + 6, _bc_y + 4, (100, 200, 255))
            if _bc_ratio >= 1.0:
                _rdy = _FONT_HUD_VAL.render("C:READY", True, (255, 255, 100))
                self.screen.blit(_rdy, (_bc_x + 52, _bc_y + 14))
            # ---- Lightning charge pips HUD (2 charges) ------------------
            if getattr(bear, 'has_lightning', False):
                _lc_x, _lc_y, _lc_w, _lc_h = 624, 38, 180, 26
                render_hud_panel(self.screen, _lc_x, _lc_y, _lc_w, _lc_h, (30, 50, 100))
                render_hud_text_outlined(self.screen, _FONT_HUD_VAL, "Q:ZAP",
                                   _lc_x + 4, _lc_y + 3, (180, 240, 100))
                _pip_w, _pip_h, _pip_gap = 55, 14, 6
                _pip_start = _lc_x + 62
                for _pi in range(2):
                    _px = _pip_start + _pi * (_pip_w + _pip_gap)
                    _py = _lc_y + 5
                    if self.lightning_charge >= (_pi + 1):
                        _pc = (160, 255, 80)
                    elif self.lightning_charge >= _pi + 0.05:
                        _frac = self.lightning_charge - _pi
                        _fc = int(255 * _frac)
                        _pc = (_fc // 2, _fc, 30)
                    else:
                        _pc = (40, 60, 30)
                    pygame.draw.rect(self.screen, _pc, (_px, _py, _pip_w, _pip_h), border_radius=4)
                    pygame.draw.rect(self.screen, (80, 120, 60), (_px, _py, _pip_w, _pip_h), 1, border_radius=4)
            if self.newGamePlusLevel > 0:
                _ng_txt = _FONT_DAMAGE.render(
                    "NG+" + str(self.newGamePlusLevel), True, (255, 215, 0))
                self.screen.blit(_ng_txt, (810, 10))

            # ---- Story / trigger text (triggers scaled to 8px steps) ----
            if totalDistance > 2300 and not self.triggerText1 and not getattr(self, '_monkey_level_active', False):
                bear.setEndText(False)
                self.triggerText1 = True
                bear.setArrayText(['The big mummy ahead has',
                                   'a red ring on its forehead.',
                                   'Press "s" to continue'])
                bear.setArrayText(['Attack it there!', 'It\'s carrying a key.',
                                   'Press "s" to continue'])

            for spike in self.spikes:
                spike.draw()

            for door in self.door:
                door.drawRectangle()
                door_x = door.getXPosition()

                if not self.isDoor1Open:
                    # Block the bear every frame while door is locked
                    if door_x - 90 <= bear.getXPosition():
                        bear.setXPosition(door_x - 91)
                        totalDistance -= STEP
                        # Show hint the first time the bear reaches the door
                        if not self.triggerText3:
                            bear.setArrayText(['Attack the mummy\'s forehead!', '',
                                               'Press "s" to continue'])
                            bear.setArrayText(['Hit it to grab the key',
                                               'for the locked door.',
                                               'Press "s" to continue'])
                            self.triggerText3 = True
                            bear.setEndText(False)
                else:
                    # Door is unlocked — detect when bear fully passes through
                    if self.isDoor1Open and bear.getXPosition() > door_x + 50:
                        self._boss_door_passed = True
                    # Show text only once the bear reaches it
                    if (not self.triggerText2
                            and door_x - 150 <= bear.getXPosition()):
                        self.triggerText2 = True
                        bear.setEndText(False)
                        bear.textArray = [['The door is unlocked!',
                                           'Keep moving forward!',
                                           'Press "s" to continue']]
                        bear.showBearArray = [False]
                        bear.tupleIndex = 0
                        bear.line = 0
                        bear.indexArray = 0
                        bear.totalText1 = ""
                        bear.totalText2 = ""
                        bear.totalText3 = ""
                        bear.text1 = ""
                        bear.text2 = ""
                        bear.text3 = ""

            if not bear.getEndText():
                bear.displayTextBox()

            if bear.getHealth() <= 0 and not self.triggerText4:
                if getattr(self, '_checkpoint_saved', False) and self._checkpoint_data:
                    totalDistance, backgroundScrollX = self._restore_checkpoint(
                        bear, background, totalDistance)
                    bear.setArrayText(['Checkpoint restored!', '',
                                       'Return to your last save.',
                                       'Press "s" to continue'])
                    bear.setEndText(False)
                else:
                    self._clear_poison(bear)
                    bear.setEndText(False)
                    self.triggerText4 = True
                    bear.setArrayText(['GAME OVER!', '',
                                       'Press "s" to continue'])
                    bear.setArrayText(['Please try again.', '',
                                       'Press "s" to continue'])
                    self.escape = True
            elif self.escape and bear.getEndText():
                pygame.quit()
                return

            if bear.getEndText() and (getattr(self, '_triggerJungleTransition', False)
                                      or getattr(self, '_triggerNewGamePlus', False)):
                transition_mode = 'jungle' if getattr(self, '_triggerJungleTransition', False) else 'ng_plus'
                self._triggerJungleTransition = False
                self._triggerNewGamePlus = False
                saved_level = bear.getLevel()
                saved_exp = bear.getCurrentExp()
                saved_hp = bear.getMaxHp()
                saved_damage = bear.getDamageAttack()
                saved_fireball_damage = getattr(bear, 'fireballDamage', 10)
                saved_max_exp = bear.getMaxExp()
                saved_coins = bear.getCoins()
                saved_shield = getattr(bear, 'has_shield', False)
                saved_aimer = getattr(bear, 'has_aimer', False)
                saved_lightning = getattr(bear, 'has_lightning', False)
                saved_lightning2 = getattr(bear, 'has_lightning_2', False)
                saved_50pct = getattr(bear, 'has_50pct_protection', False)
                saved_big_fireball = getattr(bear, 'has_big_fireball', False)

                self.bossFires = []; self.mummys = []; self.fires = []
                self.playerFires = []; self.greenBlobs = []; self.witches = []
                self.shadowShamans = []; self.blocks = []; self.frankenbear = []
                self.miniFrankenBears = []; self.lasers = []; self.waterfalls = []
                self.door = []; self.keys = []; self.spikes = []
                self.snakes = []; self.monkey_mummies = []; self.lions = []; self.coins = []
                self.venom_balls = []
                self.destroyable_blocks = []; self.beamProjectiles = []

                self.showBoss = True
                self.triggerText1 = False; self.triggerText2 = False
                self.triggerText3 = False; self.triggerText4 = False
                self.triggerText5 = False; self.createdBoss = False
                self.doorPopupTriggered = False
                self.leftBoundary = 180; self.rightBoundary = 300
                self.isFinalBossDestroyed = False
                self.escape = False; self.triggerFire = False
                self.isDoor1Open = False; self.bossTimerAnimation = 0
                self._boss_door_passed = False
                if self.water_sound and self._water_playing:
                    self.water_sound.stop()
                self._water_playing = False
                self.activeMonsters = [False] * 16
                self._monkey_level_active = False
                self._jungle_zone2_active = False

                bear = Bear(150, 300, self.screen, self.thud_sound)
                self._bear_ref = bear
                bear.grunt_sound = self.grunt_sound
                bear.jump_scream_sound = getattr(self, 'jump_scream_sound', None)
                bear.level_up_sound = getattr(self, 'level_up_sound', None)
                bear.spike_hit_sound = getattr(self, 'spike_hit_sound', None)
                # Assign crouch sprites
                bear.crouch_sprite = self.crouchBear
                bear.crouch_sprite_left = self.crouchBearLeft
                bear.setJumpStatus(False); bear.setLeftJumpStatus(False)
                bear.crouch_sprite = self.crouchBear
                bear.crouch_sprite_left = self.crouchBearLeft
                bear.setLevel(saved_level)
                bear.setCurrentExp(saved_exp)
                bear.setMaxHp(saved_hp)
                bear.setHp(saved_hp)
                bear.setDamageAttack(saved_damage)
                bear.fireballDamage = saved_fireball_damage
                bear.setMaxExp(saved_max_exp)
                bear.setCoins(saved_coins)
                bear.has_shield = saved_shield
                bear.has_aimer = saved_aimer
                bear.has_lightning = saved_lightning
                bear.has_lightning_2 = saved_lightning2
                bear.has_50pct_protection = saved_50pct
                bear.has_big_fireball = saved_big_fireball
                self._fireball_tutorial_shown = True
                self._bigMummyDefeated = (transition_mode == 'jungle')
                self._hardMode = False
                self._hardMode75 = False
                self._hardMode80 = False
                self._zone85_active = False
                self._beam_popup_shown = False
                self.lightning2_targets = []
                self.lightning2_cooldown = 0
                background.reset()

                background = Background(self.screen)
                self._bg_ref = background
                bear.setLeftDirection(False)
                bearAnimation = 0; isBearHurtAnimation = 0
                hurtTimer = 0; jumpTimer = 0
                attackCounterReady = 0; playerFireCooldown = 0
                deflectTimer = 0; deflectPos = (0, 0)
                waterOffset = 0; triggerWitchFireBallAnimation = 0
                attackingAnimationCounter = 0; attackingLeftAnimtationCounter = 0
                self._current_music = None

                self._bigMummyDefeated = False
                self._stop_ambient_loop()
                self._boss_door_passed = False
                self._post_boss_platform_popup_shown = False
                self._fireball_tutorial_shown = True
                self._clear_poison(bear)

                if transition_mode == 'jungle':
                    self._jungle_unlocked = True
                    background._jungle_mode = True
                    background._black_latched = False
                    self._switch_music("normal")
                    self.blocks = []
                    self.mummys = []
                else:
                    self._jungle_unlocked = False
                    background._ng_blue = True
                    _ng_hp_mult = (1.0 + 10.0 * self.newGamePlusLevel) * 0.7
                    _ng_dmg_mult = 1.0 + 3.0 * self.newGamePlusLevel
                    _ng_exp_mult = 1.0 + 1.0 * self.newGamePlusLevel
                    _ng_spd_mult = 1.0 + 0.2 * self.newGamePlusLevel
                    self._z1_mummy = Mummy(1000, 20, 260, 360, self.mummy1, self.mummy2, self.screen)
                    self._z1_mummy.health = int(self._z1_mummy.health * _ng_hp_mult)
                    self._z1_mummy.damageAttack = int(self._z1_mummy.damageAttack * _ng_dmg_mult)
                    self._z1_mummy.exp = int(self._z1_mummy.exp * _ng_exp_mult)
                    self._z1_mummy.rand = max(1, round(self._z1_mummy.rand * _ng_spd_mult))
                    self._z1_mummy._ng_boosted = True
                    self._z1_block_left  = Block(0,    250, 130, 150, "monster", self.screen)
                    self._z1_block_right = Block(1800, 250, 130, 150, "monster", self.screen)
                    self._z1_door = Door(self.screen, 1650)
                    _b1 = Block(230,  340, 100, 60,  "red",     self.screen)
                    _b2 = Block(500,  190, 100, 60,  "monster", self.screen)
                    _b3 = Block(780,  190, 100, 60,  "red",     self.screen)
                    _b5 = Block(1010, 190, 100, 60,  "red",     self.screen)
                    _b7 = Block(1240, 190, 100, 60,  "monster", self.screen)
                    _b6 = Block(1470, 190, 100, 60,  "monster", self.screen)
                    _b8 = Block(1600, 100, 250, 300, "monster", self.screen)
                    self.blocks.extend([_b1, _b2, _b3, _b5, _b6, _b7, _b8])
                    for _mx in [700, 1000, 1300, 1600]:
                        _m = Mummy(_mx, 300, 100, 100, self.mummy1, self.mummy2, self.screen)
                        _m.health = int(_m.health * _ng_hp_mult)
                        _m.damageAttack = int(_m.damageAttack * _ng_dmg_mult)
                        _m.rand = max(1, round(_m.rand * _ng_spd_mult))
                        self.mummys.append(_m)
                    self._switch_music("normal")
                bear.setXPosition(150)
                bear.setYPosition(300)
                backgroundScrollX = 60
                totalDistance = 60
                background.setXPosition(backgroundScrollX)
                self._switch_music("normal")

            # ---- Lightning strike animation (drawn on top of everything) ----
            if self.lightning_anim > 0:
                self.lightning_anim -= 1
                _lx = self.lightning_x
                _bright = self.lightning_anim > 14
                _rng_bolt = random.Random(self.lightning_anim)  # stable shape per frame
                bx, by = _lx, 0
                while by < 410:
                    nbx = int(bx + _rng_bolt.randint(-22, 22))
                    nby = min(410, by + _rng_bolt.randint(20, 38))
                    _c_outer = (80, 180, 255) if _bright else (40, 90, 160)
                    _c_core  = (255, 255, 80) if _bright else (160, 200, 80)
                    pygame.draw.line(self.screen, _c_outer, (bx, by), (nbx, nby), 9)
                    pygame.draw.line(self.screen, _c_core,  (bx, by), (nbx, nby), 4)
                    pygame.draw.line(self.screen, (255, 255, 255), (bx, by), (nbx, nby), 1)
                    bx, by = nbx, nby
                if _bright:
                    pygame.draw.circle(self.screen, (255, 255, 160), (_lx, 398), 50)
                    pygame.draw.circle(self.screen, (255, 255, 220), (_lx, 398), 28)
                    pygame.draw.circle(self.screen, (255, 255, 255), (_lx, 398), 14)
                # Cooldown indicator: thin arc above bear when lightning charged
                if self.lightning_cooldown == 0 and getattr(bear, 'has_lightning', False):
                    _bxx = bear.getXPosition() + 50
                    pygame.draw.circle(self.screen, (80, 200, 255),
                                       (_bxx, bear.getYPosition() - 12), 8, 2)
            # ---- Lightning 2 successive bolts animation ------------------
            _l2_keep = []
            for _l2b in self.lightning2_targets:
                if _l2b['delay'] > 0:
                    _l2b['delay'] -= 1
                    _l2_keep.append(_l2b)
                else:
                    if _l2b['anim'] == 0:
                        _l2b['anim'] = 28
                    _l2b['anim'] -= 1
                    if _l2b['anim'] > 0:
                        _l2_keep.append(_l2b)
                    _lx2 = _l2b['x']
                    _bright2 = _l2b['anim'] > 14
                    _rng2 = random.Random(_l2b['anim'] + _lx2)
                    bx2, by2 = _lx2, 0
                    while by2 < 410:
                        nbx2 = int(bx2 + _rng2.randint(-18, 18))
                        nby2 = min(410, by2 + _rng2.randint(20, 38))
                        _co2 = (120, 220, 120) if _bright2 else (60, 140, 60)
                        _cc2 = (200, 255, 80)  if _bright2 else (120, 200, 60)
                        pygame.draw.line(self.screen, _co2, (bx2, by2), (nbx2, nby2), 9)
                        pygame.draw.line(self.screen, _cc2, (bx2, by2), (nbx2, nby2), 4)
                        pygame.draw.line(self.screen, (240, 255, 200), (bx2, by2), (nbx2, nby2), 1)
                        bx2, by2 = nbx2, nby2
                    if _bright2:
                        pygame.draw.circle(self.screen, (200, 255, 160), (_lx2, 398), 45)
                        pygame.draw.circle(self.screen, (220, 255, 200), (_lx2, 398), 24)
            self.lightning2_targets = _l2_keep

            if not shop_open and bear.getEndText():
                _hint_alpha = max(0, min(180, 180 - (totalDistance // 50)))
                if _hint_alpha > 0:
                    _hint_parts = ['ARROWS:Move', 'SPACE:Jump', 'Z:Attack', 'X:Fireball', 'ENTER:Shop']
                    if getattr(bear, 'has_lightning', False):
                        _hint_parts.append('Q:Lightning')
                    _hint_str = '    '.join(_hint_parts)
                    _hint_surf = _FONT_HUD_VAL.render(_hint_str, True, (200, 200, 220))
                    _hint_a_surf = pygame.Surface((_hint_surf.get_width() + 16, _hint_surf.get_height() + 6), pygame.SRCALPHA)
                    _hint_a_surf.fill((0, 0, 0, min(120, _hint_alpha)))
                    _hint_a_surf.blit(_hint_surf, (8, 3))
                    _hint_a_surf.set_alpha(_hint_alpha)
                    self.screen.blit(_hint_a_surf, ((900 - _hint_a_surf.get_width()) // 2, 682))

            _gfi = getattr(self, '_game_fade_in', 0)
            if _gfi > 0:
                self._game_fade_in -= 1
                _fi_alpha = int(255 * (self._game_fade_in / 60.0))
                _fi_surf = pygame.Surface((900, 700), pygame.SRCALPHA)
                _fi_surf.fill((0, 0, 0, _fi_alpha))
                self.screen.blit(_fi_surf, (0, 0))
                _music_vol = 0.35 * (1.0 - self._game_fade_in / 60.0)
                try:
                    pygame.mixer.music.set_volume(_music_vol)
                except Exception:
                    pass

            pygame.display.flip()
            self.clock.tick(60)

    # -----------------------------------------------------------------------
    def deleteAndCreateObjects(self, backgroundScrollX):
        # Zones are ordered in ascending scroll distance with ~4 000+ unit gaps
        # so they never overlap or interfere with one another.

        # ── Fireball tutorial popup @ 400 ──────────────────────────────────────
        if backgroundScrollX > 400 and not self._fireball_tutorial_shown:
            self._fireball_tutorial_shown = True
            bear = None
            for obj in [getattr(self, '_bear_ref', None)]:
                if obj is not None:
                    bear = obj
            if bear is not None:
                bear.setArrayText(['Press "x" to shoot fireballs!', '',
                                   'Press "s" to continue'])
                bear.setEndText(False)

        # ── Zone 1 pre-load @ 2 500 – quietly position Zone 1 objects ────────
        # Objects are given offset positions so they scroll naturally into place
        # by the time Zone 1 triggers at 5 000, eliminating any pop-in.
        if backgroundScrollX > 2500 and not self.activeMonsters[11]:
            self.activeMonsters[11] = True
            if getattr(self, 'wave_warning_sound', None): self.wave_warning_sound.play()
            offset = 5000 - 2500  # 2 500 scroll-units of lead time
            self._z1_block_left.setblockXPosition(0    + offset)
            self._z1_block_right.setblockXPosition(1400 + offset)  # left of door (door at 1650)
            self._z1_door.setXPosition(1650 + offset)
            self._z1_mummy.setXPosition(1000 + offset)
            self.blocks.append(self._z1_block_left)
            self.blocks.append(self._z1_block_right)
            # Boss mummy stays off-screen – added to self.mummys only when Zone 1 fires.
            self.door.append(self._z1_door)
            self.door1 = self._z1_door

        # ── Zone 1 @ 5 000 – big mummy flanked by monster blocks ─────────────
        if backgroundScrollX > 5000 and not self.activeMonsters[1]:
            self.activeMonsters[1] = True
            if getattr(self, 'enemy_spawn_sound', None): self.enemy_spawn_sound.play()
            self._switch_music("boss_mummy")
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []; self.miniFrankenBears = []; self.lasers = []

            self.blocks.extend([self._z1_block_left, self._z1_block_right])
            self._z1_mummy.setXPosition(750)  # Start just off right edge; walks toward player
            self.mummys.append(self._z1_mummy)

            self.door1 = self._z1_door
            self.door = [self.door1]  # replace list to avoid duplicate
            self.doorPopupTriggered = False

        # ── Zone TEST @ 6 500 – "Monkey Temple" – Optional Challenge Level ──
        if (backgroundScrollX > 5000 and not getattr(self, '_monkey_level_active', False)
            and self._jungle_unlocked and not self.activeMonsters[3]):
            self.activeMonsters[3] = True
            self._monkey_level_active = True
            self._jungle_zone2_active = False
            self._switch_music("jungle")
            if hasattr(self, '_bg_ref') and self._bg_ref:
                self._bg_ref._jungle_mode = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []; self.miniFrankenBears = []; self.lasers = []
            self.monkey_mummies = []; self.snakes = []; self.lions = []
            self.venom_balls = []
            self.door = []; self.keys = []
            self.frankenbear = []; self.shadowShamans = []
            self.bossFires = []; self.spikes = []
            self.coins = []; self.destroyable_blocks = []

            self.blocks.extend([
                Block(1100, 280, 120, 50, "greyRock", self.screen),
                Block(1350, 220, 110, 50, "striped", self.screen),
                Block(1600, 260, 130, 50, "checkered", self.screen),
                Block(1900, 200, 100, 50, "greyRock", self.screen),
                Block(2150, 300, 140, 50, "striped", self.screen),
            ])

            _ms = self.monkey_screech_sound
            _lr = self.lion_roar_sound
            self.monkey_mummies.extend([
                MonkeyMummy(1150, 220, 180, 180, self.mummy1, self.mummy2, self.screen, _ms),
                MonkeyMummy(1700, 220, 180, 180, self.mummy1, self.mummy2, self.screen, _ms),
            ])
            self.snakes.extend([
                Snake(1400, 320, self.screen),
                Snake(2000, 320, self.screen),
            ])
            self.lions.extend([
                Lion(1550, 300, self.screen, _lr),
            ])

        if (self._monkey_level_active and not self._jungle_zone2_active
                and backgroundScrollX > 8000):
            _j1_left = len(self.monkey_mummies) + len(self.snakes) + len(self.lions)
            if _j1_left == 0:
                self._jungle_zone2_active = True
                self.blocks = []; self.coins = []
                self.monkey_mummies = []; self.snakes = []; self.lions = []

                self.blocks.extend([
                    Block(1050, 250, 130, 50, "checkered", self.screen),
                    Block(1300, 180, 110, 50, "greyRock", self.screen),
                    Block(1550, 300, 120, 50, "striped", self.screen),
                    Block(1800, 220, 100, 50, "checkered", self.screen),
                    Block(2050, 260, 140, 50, "greyRock", self.screen),
                    Block(2300, 190, 110, 50, "striped", self.screen),
                ])

                _ms = self.monkey_screech_sound
                _lr = self.lion_roar_sound
                self.monkey_mummies.extend([
                    MonkeyMummy(1100, 220, 180, 180, self.mummy1, self.mummy2, self.screen, _ms),
                    MonkeyMummy(1700, 220, 180, 180, self.mummy1, self.mummy2, self.screen, _ms),
                ])
                self.snakes.extend([
                    Snake(1400, 320, self.screen),
                    Snake(2100, 320, self.screen),
                ])
                self.lions.extend([
                    Lion(1550, 300, self.screen, _lr),
                ])

        # ── Zone 1.2 @ 8 000 – "Enchanted Tomb" mystical gauntlet ──────────────
        elif not self._monkey_level_active and backgroundScrollX > 8000 and not self.activeMonsters[14]:
            self.activeMonsters[14] = True
            self._switch_music("enchanted_tomb")
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []; self.snakes = []

            # Mystical floating platforms at varied heights
            plat1 = Block(1050, 250, 110, 50, "checkered", self.screen)
            plat2 = Block(1250, 180, 110, 50, "striped",   self.screen)
            plat3 = Block(1450, 240, 110, 50, "checkered", self.screen)
            plat4 = Block(1650, 150, 110, 50, "monster",   self.screen)
            plat5 = Block(1850, 220, 110, 50, "striped",   self.screen)
            self.blocks.extend([plat1, plat2, plat3, plat4, plat5])

            # Witch-heavy zone — no mummies
            witch1 = Witch(1500, 200, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch2 = Witch(1850, 280, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch3 = Witch(2200, 150, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch4 = Witch(2550, 100, self.witch, self.witch2, self.screen, self.fireball_sound)
            self.witches.extend([witch1, witch2, witch3, witch4])
            self.snakes.append(Snake(1500, 220, self.screen))

        # ── Zone 1.5 @ 11 000 – "Crumbling Ruins" gauntlet ───────────────────
        elif not self._monkey_level_active and backgroundScrollX > 11000 and not self.activeMonsters[10]:
            self.activeMonsters[10] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []

            # ── Pyramid staircase – all platforms have y+h ≤ 310 so floor
            #    mummies (m_top = 312) walk straight underneath them. ──────────
            plat1 = Block(1050, 248, 200, 60, "striped",     self.screen)
            plat2 = Block(1240, 188, 180, 60, "greyRock",    self.screen)
            plat3 = Block(1410, 122, 220, 60, "checkered",   self.screen)
            plat4 = Block(1635, 188, 180, 60, "monster",     self.screen)
            plat5 = Block(1810, 248, 200, 60, "stripedFlip", self.screen)

            # ── Tall coffin pillars – y = 260 so mummies (m_top=312) hit them
            #    as turning walls; player must jump over or around. ────────────
            coffin1 = Block(1160, 260, 45, 140, "monster", self.screen)
            coffin2 = Block(1390, 260, 45, 140, "monster", self.screen)
            coffin3 = Block(1610, 260, 45, 140, "monster", self.screen)
            coffin4 = Block(1800, 260, 45, 140, "monster", self.screen)

            self.blocks.extend([plat1, plat2, plat3, plat4, plat5,
                                 coffin1, coffin2, coffin3, coffin4])

            # ── Five floor mummies – coffins act as natural patrol walls ──────
            for x in [1030, 1300, 1550, 1800]:
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))

            # ── Two green blobs adding chaos in the wider gaps ────────────────
            self.greenBlobs.append(GreenBlob(1310, 300, 100, 100, self.screen, self.blob_jump_sound))
            self.greenBlobs.append(GreenBlob(1720, 300, 100, 100, self.screen, self.blob_jump_sound))

            # ── Two witches: one low-and-close, one high-and-far ─────────────
            witch1 = Witch(1800,  80, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch2 = Witch(2200, 140, self.witch, self.witch2, self.screen, self.fireball_sound)
            self.witches.extend([witch1, witch2])
            self.triggerFire = True

        # ── Zone 2 @ 14 500 – green blobs on a rock platform ──────────────────
        elif not self._monkey_level_active and backgroundScrollX > 14500 and not self.activeMonsters[3]:
            self.activeMonsters[3] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []

            block1 = Block(1000, 340, 900,  60, "greyRock", self.screen)
            block2 = Block(1900, 220, 2000, 60, "greyRock", self.screen)
            self.blocks.extend([block1, block2])

            greenBlob  = GreenBlob(1050, 300, 100, 100, self.screen, self.blob_jump_sound)
            greenBlob2 = GreenBlob(1400, 300, 100, 100, self.screen, self.blob_jump_sound)
            greenBlob3 = GreenBlob(1750, 300, 100, 100, self.screen, self.blob_jump_sound)
            greenBlob4 = GreenBlob(2100, 300, 100, 100, self.screen, self.blob_jump_sound)
            self.greenBlobs.extend([greenBlob, greenBlob2, greenBlob3, greenBlob4])

            x = 1950
            for _ in range(6):
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
                x += 450

        # ── Zone 3 @ 18 500 – first witch encounter (3 witches) ──────────────
        elif not self._monkey_level_active and backgroundScrollX > 18500 and not self.activeMonsters[2]:
            self.activeMonsters[2] = True
            if getattr(self, 'enemy_spawn_sound', None): self.enemy_spawn_sound.play()
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []; self.shadowShamans = []

            block1 = Block(1100, 340, 100, 60,  "greyRock", self.screen)
            block2 = Block(1420, 100, 150, 300, "monster",  self.screen)
            block3 = Block(1260, 160, 130, 60,  "greyRock", self.screen)
            block4 = Block(950,  340, 600, 60,  "greyRock", self.screen)
            self.blocks.extend([block1, block2, block3, block4])

            witch1 = Witch(1600, 100, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch2 = Witch(2000, 200, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch3 = Witch(2400, 150, self.witch, self.witch2, self.screen, self.fireball_sound)
            self.witches.extend([witch1, witch2, witch3])
            
            shaman = ShadowShaman(1400, 60, self.witch, self.witch2, self.screen)
            self.shadowShamans.append(shaman)
            
            for x in [1030, 1500, 1900]:
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
            self.triggerFire = True

        # ── Zone 3.5 @ 22 000 – waterfall passage ─────────────────────────────
        elif not self._monkey_level_active and backgroundScrollX > 22000 and not self.activeMonsters[13]:
            self.activeMonsters[13] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []; self.shadowShamans = []
            self.miniFrankenBears = []; self.lasers = []; self.waterfalls = []

            block1 = Block(1000, 300, 900, 60, "greyRock", self.screen)
            block2 = Block(1950, 240, 800, 60, "greyRock", self.screen)
            self.blocks.extend([block1, block2])

            waterfall = Waterfall(1300, 80, 120, 150, self.screen)
            self.waterfalls.append(waterfall)
            if self.water_sound and not self._water_playing:
                self.water_sound.play(-1)
                self._water_playing = True

        # ── Zone 4 @ 25 500 – mummy rush on tiered platforms ─────────────────
        elif not self._monkey_level_active and backgroundScrollX > 25500 and not self.activeMonsters[4]:
            self._switch_music("halfway")
            if self.water_sound and self._water_playing:
                self.water_sound.stop()
                self._water_playing = False
            self.activeMonsters[4] = True
            if getattr(self, 'wave_warning_sound', None): self.wave_warning_sound.play()
            self._hardMode = True
            if hasattr(self, '_bg_ref') and self._bg_ref:
                self._bg_ref.setHardModeFloor()
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []; self.waterfalls = []

            block1 = Block(1100, 280, 200, 50, "greyRock", self.screen)
            block2 = Block(1500, 180, 200, 50, "greyRock", self.screen)
            block3 = Block(1900, 250, 200, 50, "greyRock", self.screen)
            block4 = Block(2300, 220, 200, 50, "greyRock", self.screen)
            self.blocks.extend([block1, block2, block3, block4])

            x = 1050
            for _ in range(6):
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
                x += 400
            self.greenBlobs.append(GreenBlob(1300, 300, 100, 100, self.screen, self.blob_jump_sound))
            self.greenBlobs.append(GreenBlob(1900, 300, 100, 100, self.screen, self.blob_jump_sound))
            self._secret_box_spawned = True
            secret_block = DestroyableBlock(1550, 110, 80, 80, self.screen, secret=True)
            self.destroyable_blocks.append(secret_block)

        # ── Zone 4.2 @ 29 000 – mini frankenbeares with rainbow lasers ────────
        elif not self._monkey_level_active and backgroundScrollX > 29000 and not self.activeMonsters[12]:
            self.activeMonsters[12] = True
            self.miniFrankenBears = []; self.blocks = []
            self.mummys = []; self.witches = []; self.greenBlobs = []; self.fires = []
            self.lasers = []

            block1 = Block(1000, 280, 800, 60, "greyRock", self.screen)
            block2 = Block(1900, 200, 800, 60, "greyRock", self.screen)
            self.blocks.extend([block1, block2])

            mini1 = MiniFrankenBear(1200, 200, self.screen)
            mini2 = MiniFrankenBear(1600, 120, self.screen)
            mini3 = MiniFrankenBear(2000, 200, self.screen)
            self.miniFrankenBears.extend([mini1, mini2, mini3])

        # ── Zone 5 @ 34 000 – striped platforms, mummies + 2 witches ─────────
        elif not self._monkey_level_active and backgroundScrollX > 34000 and not self.activeMonsters[5]:
            self.activeMonsters[5] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []; self.miniFrankenBears = []; self.lasers = []

            block1 = Block(1050, 240, 3000, 60, "striped",     self.screen)
            block2 = Block(1200, 280, 2000, 60, "stripedFlip", self.screen)
            block3 = Block(1400, 310, 1000, 60, "striped",     self.screen)
            self.blocks.extend([block1, block2, block3])

            x = 1050
            for _ in range(5):
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
                x += 400

            witch1 = Witch(1800, 100, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch2 = Witch(2300, 100, self.witch, self.witch2, self.screen, self.fireball_sound)
            self.witches.extend([witch1, witch2])

        # ── Zone 5.5 @ 36 500 – snake encounter with platform gauntlet ────────
        elif not self._monkey_level_active and backgroundScrollX > 36500 and not getattr(self, '_zone55_active', False):
            self._zone55_active = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []; self.miniFrankenBears = []; self.lasers = []

            block1 = Block(1050, 280, 1500, 60, "monster", self.screen)
            block2 = Block(1350, 220, 1000, 60, "greyRock", self.screen)
            block3 = Block(1650, 280, 1200, 60, "monster", self.screen)
            self.blocks.extend([block1, block2, block3])

            # Snakes scattered across the platforms
            snake1 = Snake(1200, 220, self.screen)
            snake2 = Snake(1500, 160, self.screen)
            snake3 = Snake(1800, 220, self.screen)
            self.snakes.extend([snake1, snake2, snake3])

        # ── Zone 6 @ 39 500 – checkered gauntlet, blobs + mummies + miniFranken
        elif not self._monkey_level_active and backgroundScrollX > 39500 and not self.activeMonsters[6]:
            self.activeMonsters[6] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []
            self.miniFrankenBears = []; self.lasers = []

            block1 = Block(1100, 240, 3500, 60, "checkered", self.screen)
            block2 = Block(1020, 280, 3500, 60, "checkered", self.screen)
            block3 = Block(950,  310, 3000, 60, "checkered", self.screen)
            block4 = Block(1100, 200, 1000, 60, "greyRock",  self.screen)
            self.blocks.extend([block1, block2, block3, block4])

            greenBlob  = GreenBlob(1030, 300, 100, 100, self.screen, self.blob_jump_sound)
            greenBlob2 = GreenBlob(1450, 300, 100, 100, self.screen, self.blob_jump_sound)
            greenBlob3 = GreenBlob(1900, 300, 100, 100, self.screen, self.blob_jump_sound)
            self.greenBlobs.extend([greenBlob, greenBlob2, greenBlob3])

            x = 1350
            for _ in range(4):
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
                x += 500

            mini1 = MiniFrankenBear(1500, 160, self.screen)
            mini2 = MiniFrankenBear(1900, 200, self.screen)
            self.miniFrankenBears.extend([mini1, mini2])

        # ── Zone 7 @ 45 000 – 75% mark, enemies 100% harder ────────
        elif not self._monkey_level_active and backgroundScrollX > 45000 and not self.activeMonsters[7]:
            self.activeMonsters[7] = True
            if getattr(self, 'wave_warning_sound', None): self.wave_warning_sound.play()
            self._hardMode75 = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []

            block1 = Block(1020, 340, 100, 60, "checkered", self.screen)
            block2 = Block(1300, 340, 100, 60, "checkered", self.screen)
            block3 = Block(1580, 280, 100, 60, "checkered", self.screen)
            self.blocks.extend([block1, block2, block3])

            witch1 = Witch(1900, 200, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch2 = Witch(1600, 250, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch3 = Witch(2200, 150, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch4 = Witch(1400, 120, self.witch, self.witch2, self.screen, self.fireball_sound)
            self.witches.extend([witch1, witch2, witch3, witch4])
            for x in [1050, 1450, 1850]:
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))

        # ── Zone 8 @ 50 500 – spike gauntlet + miniFranken ────────────────────
        elif not self._monkey_level_active and backgroundScrollX > 50500 and not self.activeMonsters[8]:
            self.activeMonsters[8] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []
            self.miniFrankenBears = []; self.lasers = []
            self._switch_music("final_push")
            self._hardMode80 = True

            block1 = Block(1050, 220, 100, 60, "checkered", self.screen)
            block2 = Block(1300, 220, 100, 60, "checkered", self.screen)
            block3 = Block(1550, 280, 100, 60, "checkered", self.screen)
            block4 = Block(950,  340, 100, 60, "checkered", self.screen)
            block5 = Block(1800, 280, 100, 60, "checkered", self.screen)
            self.blocks.extend([block1, block2, block3, block4, block5])

            self.spikes.append(SpikeBlock(1100, 340, self.screen))
            self.spikes.append(SpikeBlock(1350, 340, self.screen))
            self.spikes.append(SpikeBlock(1600, 340, self.screen))
            self.spikes.append(SpikeBlock(1900, 340, self.screen))

            for x in [1000, 1400, 1800]:
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
            witch1 = Witch(1400, 180, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch2 = Witch(1700, 120, self.witch, self.witch2, self.screen, self.fireball_sound)
            self.witches.extend([witch1, witch2])
            self.greenBlobs.append(GreenBlob(1150, 300, 100, 100, self.screen, self.blob_jump_sound))
            self.greenBlobs.append(GreenBlob(1650, 300, 100, 100, self.screen, self.blob_jump_sound))

            mini1 = MiniFrankenBear(1200, 140, self.screen)
            mini2 = MiniFrankenBear(1700, 100, self.screen)
            self.miniFrankenBears.extend([mini1, mini2])
            self.triggerFire = True

        # ── Zone 8.5 @ 53 500 – "Shadow Ambush" ──────────────────────────────
        elif not self._monkey_level_active and backgroundScrollX > 53500 and not getattr(self, '_zone85_active', False):
            self._zone85_active = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []; self.spikes = []
            self.miniFrankenBears = []; self.lasers = []

            block1 = Block(1000, 260, 110, 50, "checkered", self.screen)
            block2 = Block(1350, 200, 110, 50, "checkered", self.screen)
            block3 = Block(1700, 260, 110, 50, "checkered", self.screen)
            self.blocks.extend([block1, block2, block3])

            self.spikes.append(SpikeBlock(1200, 340, self.screen))
            self.spikes.append(SpikeBlock(1500, 340, self.screen))

            self.shadowShamans.extend([
                ShadowShaman(1100, 180, self.witch, self.witch2, self.screen),
                ShadowShaman(1600, 140, self.witch, self.witch2, self.screen),
            ])
            mini1 = MiniFrankenBear(1300, 120, self.screen)
            mini2 = MiniFrankenBear(1800, 160, self.screen)
            self.miniFrankenBears.extend([mini1, mini2])

            self.mummys.extend([
                Mummy(1050, 300, 100, 100, self.mummy1, self.mummy2, self.screen),
                Mummy(1550, 300, 100, 100, self.mummy1, self.mummy2, self.screen),
            ])
            self.greenBlobs.extend([
                GreenBlob(1300, 300, 100, 100, self.screen, self.blob_jump_sound),
                GreenBlob(1800, 300, 100, 100, self.screen, self.blob_jump_sound),
            ])
            self.triggerFire = True

        # ── Zone 9 @ 49 500 – "Floating Gauntlet" mixed challenge ──────────────
        elif not self._monkey_level_active and backgroundScrollX > 56500 and not self.activeMonsters[15]:
            self.activeMonsters[15] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []; self.spikes = []

            # Floating platforms arranged at varied heights
            block1 = Block(1000, 200, 120, 50, "striped", self.screen)
            block2 = Block(1250, 280, 120, 50, "striped", self.screen)
            block3 = Block(1500, 160, 120, 50, "striped", self.screen)
            block4 = Block(1750, 240, 120, 50, "striped", self.screen)
            block5 = Block(2000, 180, 120, 50, "striped", self.screen)
            self.blocks.extend([block1, block2, block3, block4, block5])

            # Mixed enemy types for a challenging final gauntlet
            self.mummys.extend([
                Mummy(1050, 300, 100, 100, self.mummy1, self.mummy2, self.screen),
                Mummy(1550, 300, 100, 100, self.mummy1, self.mummy2, self.screen),
                Mummy(1800, 300, 100, 100, self.mummy1, self.mummy2, self.screen),
            ])
            witch1 = Witch(1300, 230, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch2 = Witch(1950, 130, self.witch, self.witch2, self.screen, self.fireball_sound)
            self.witches.extend([witch1, witch2])
            self.greenBlobs.extend([
                GreenBlob(1150, 250, 100, 100, self.screen, self.blob_jump_sound),
                GreenBlob(1700, 210, 100, 100, self.screen, self.blob_jump_sound),
            ])

        if self._hardMode:
            _sprite_attrs = {
                'Mummy':           ['mummy1', 'mummy2', 'hurtMummy', 'hurtLeftMummy'],
                'Witch':           ['witch', 'witch2', 'hurtWitch'],
                'GreenBlob':       ['greenBlob', 'hurtGreenBlob'],
                'ShadowShaman':    ['witch', 'witch2', 'hurtWitch'],
                'MiniFrankenBear': [],
            }
            for _m in (self.mummys + self.witches + self.greenBlobs +
                       self.shadowShamans + self.miniFrankenBears + self.lions):
                if not getattr(_m, '_hm_boosted', False):
                    _m._hm_boosted = True
                    _m.health = int(_m.health * 1.7)
                    _m.damageAttack = int(_m.damageAttack * 1.7)
                    _cls = type(_m).__name__
                    for attr in _sprite_attrs.get(_cls, []):
                        _img = getattr(_m, attr, None)
                        if _img and isinstance(_img, pygame.Surface):
                            _tinted = _img.copy()
                            _red_ov = pygame.Surface(_tinted.get_size(), pygame.SRCALPHA)
                            _red_ov.fill((255, 130, 130))
                            _tinted.blit(_red_ov, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
                            _bright = pygame.Surface(_tinted.get_size(), pygame.SRCALPHA)
                            _bright.fill((60, 0, 0))
                            _tinted.blit(_bright, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
                            setattr(_m, attr, _tinted)

        if self.newGamePlusLevel > 0:
            _ng_hp_m = (1.0 + 10.0 * self.newGamePlusLevel) * 0.7
            _ng_dmg_m = 1.0 + 3.0 * self.newGamePlusLevel
            _ng_exp_m = 1.0 + 1.0 * self.newGamePlusLevel
            _ng_spd_m = 1.0 + 0.2 * self.newGamePlusLevel
            for _m in (self.mummys + self.witches + self.greenBlobs +
                       self.shadowShamans + self.miniFrankenBears + self.lions):
                if not getattr(_m, '_ng_boosted', False):
                    _m._ng_boosted = True
                    _m.health = int(_m.health * _ng_hp_m)
                    _m.damageAttack = int(_m.damageAttack * _ng_dmg_m)
                    _m.exp = int(_m.exp * _ng_exp_m)
                    if hasattr(_m, 'walk_speed'):
                        _m.walk_speed = max(1, round(_m.walk_speed * _ng_spd_m))
                    if hasattr(_m, 'rand'):
                        _m.rand = max(1, round(_m.rand * _ng_spd_m))

        if getattr(self, '_hardMode75', False):
            for _m in (self.mummys + self.witches + self.greenBlobs +
                       self.shadowShamans + self.miniFrankenBears + self.lions):
                if not getattr(_m, '_hm75_boosted', False):
                    _m._hm75_boosted = True
                    _m.health = int(_m.health * 2.0)
                    _m.damageAttack = int(_m.damageAttack * 2.0)

        if getattr(self, '_hardMode80', False):
            for _m in (self.mummys + self.witches + self.greenBlobs +
                       self.shadowShamans + self.miniFrankenBears + self.lions):
                if not getattr(_m, '_hm80_boosted', False):
                    _m._hm80_boosted = True
                    _m.health = int(_m.health * 1.2)
                    _m.damageAttack = int(_m.damageAttack * 1.2)
                    if isinstance(_m, GreenBlob):
                        _m.nextJumpTimer = max(20, int(_m.nextJumpTimer * 0.5))
                    if isinstance(_m, Witch):
                        _m.changeDirectionX = max(100, int(_m.changeDirectionX * 0.6))

        _all_for_variance = (self.mummys + self.witches + self.greenBlobs +
                             self.shadowShamans + self.miniFrankenBears + self.lions +
                             self.monkey_mummies + self.snakes)
        for _m in _all_for_variance:
            if not getattr(_m, '_speed_variance_applied', False):
                _m._speed_variance_applied = True

                _walk_roll = random.random()
                if _walk_roll < 0.20:
                    _walk_scale = 1.4
                elif _walk_roll < 0.60:
                    _walk_scale = 1.2
                else:
                    _walk_scale = 1.1
                if hasattr(_m, 'change_direction_timer'):
                    _m.change_direction_timer = int(_m.change_direction_timer * _walk_scale)
                    _m._turn_timer_scale = getattr(_m, '_turn_timer_scale', 1.0) * _walk_scale
                if hasattr(_m, 'rand') and _m.rand >= 2:
                    _m.rand = max(2, int(_m.rand * _walk_scale))

                _stat_roll = random.random()
                if _stat_roll < 0.05:
                    _hp_mult = 2.0
                    _atk_mult = 2.0
                elif _stat_roll < 0.25:
                    _hp_mult = 1.3
                    _atk_mult = 1.3
                elif _stat_roll < 0.65:
                    _hp_mult = 1.1
                    _atk_mult = 1.1
                else:
                    _hp_mult = 1.0
                    _atk_mult = 1.0
                if _hp_mult > 1.0:
                    if hasattr(_m, 'health'):
                        _m.health = int(_m.health * _hp_mult)
                    if hasattr(_m, 'max_health'):
                        _m.max_health = int(_m.max_health * _hp_mult)
                if _atk_mult > 1.0:
                    if hasattr(_m, 'damageAttack'):
                        _m.damageAttack = int(_m.damageAttack * _atk_mult)

        if getattr(self, '_hard_mode_selected', False):
            _all_enemies = (self.mummys + self.witches + self.greenBlobs +
                            self.shadowShamans + self.miniFrankenBears + self.lions +
                            self.monkey_mummies + self.snakes)
            for _m in _all_enemies:
                if not getattr(_m, '_hms_speed_boosted', False):
                    _m._hms_speed_boosted = True
                    _m._hard_mode = True
                    if hasattr(_m, 'walk_speed'):
                        _m.walk_speed = round(_m.walk_speed * 1.1)
                    if hasattr(_m, 'speed'):
                        _m.speed = round(_m.speed * 1.1)
                    if hasattr(_m, 'charge_speed'):
                        _m.charge_speed = round(_m.charge_speed * 1.1)
                    if hasattr(_m, 'rand') and _m.rand >= 2:
                        _m.rand = max(2, round(_m.rand * 1.1))
                    if hasattr(_m, 'change_direction_timer'):
                        _m.change_direction_timer = int(_m.change_direction_timer * 1.8)
                        _m._turn_timer_scale = 1.8

            for _m in _all_enemies:
                if getattr(_m, '_hard_mode', False) and _m.getHealth() > 0 and getattr(_m, 'stunned', 0) == 0:
                    if random.random() < 0.02:
                        if hasattr(_m, 'directionX'):
                            _m.directionX = -_m.directionX
                        elif hasattr(_m, 'direction'):
                            _m.direction = -_m.direction
                    if random.random() < 0.015:
                        _burst = random.choice([2, 3, 4])
                        _dir = getattr(_m, 'direction', getattr(_m, 'directionX', -1))
                        _m.x = max(0, min(870, _m.x + _dir * _burst))
                    if hasattr(_m, 'can_jump') and _m.can_jump and random.random() < 0.01:
                        _m.jump_timer = 999
                    if hasattr(_m, 'is_charging') and not _m.is_charging and random.random() < 0.012:
                        _m.is_charging = True
                        _m.charge_timer = random.randint(15, 35)

            if not getattr(self, '_hms_post_boss_applied', False) and self._bigMummyDefeated:
                self._hms_post_boss_applied = True

            for _m in _all_enemies:
                if not getattr(_m, '_hms_boosted', False):
                    _m._hms_boosted = True
                    if getattr(self, '_hms_post_boss_applied', False):
                        _m.health = int(_m.health * 1.4)
                        _m.damageAttack = int(_m.damageAttack * 1.4)
                    else:
                        _m.damageAttack = int(_m.damageAttack * 1.5)

    # -----------------------------------------------------------------------
    def _tint_silver(self, surface):
        copy = surface.copy()
        grey = pygame.Surface(copy.get_size(), pygame.SRCALPHA)
        grey.fill((170, 170, 195))
        copy.blit(grey, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        bright = pygame.Surface(copy.get_size(), pygame.SRCALPHA)
        bright.fill((75, 75, 80))
        copy.blit(bright, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        return copy

    def _apply_silver_tint(self):
        self._silver_applied = True
        self.standingBear = self._tint_silver(self.standingBear)
        self.standingBearLeft = self._tint_silver(self.standingBearLeft)
        self.bearWalking1 = self._tint_silver(self.bearWalking1)
        self.bearWalking2 = self._tint_silver(self.bearWalking2)
        self.bearWalking3 = self._tint_silver(self.bearWalking3)
        self.bearWalking4 = self._tint_silver(self.bearWalking4)
        self.bearWalkingLeft1 = self._tint_silver(self.bearWalkingLeft1)
        self.bearWalkingLeft2 = self._tint_silver(self.bearWalkingLeft2)
        self.bearWalkingLeft3 = self._tint_silver(self.bearWalkingLeft3)
        self.bearWalkingLeft4 = self._tint_silver(self.bearWalkingLeft4)
        self._precompute_walk_lean()
        self.bearAttacking = self._tint_silver(self.bearAttacking)
        self.bearAttackingLeft = self._tint_silver(self.bearAttackingLeft)
        self.hurtBear = self._tint_silver(self.hurtBear)

    # -----------------------------------------------------------------------
    def _update_tension_layers(self, totalDistance):
        if not getattr(self, '_tension_layers_ready', False):
            return
        _FADE_SPEED = 0.003
        for layer in self._tension_layers:
            should_play = totalDistance >= layer['threshold']
            if should_play and not layer['active']:
                layer['channel'].play(layer['sound'], loops=-1)
                layer['channel'].set_volume(0.0)
                layer['active'] = True
            if layer['active']:
                if should_play:
                    target = layer['max_vol']
                else:
                    target = 0.0
                if layer['current_vol'] < target:
                    layer['current_vol'] = min(target, layer['current_vol'] + _FADE_SPEED)
                elif layer['current_vol'] > target:
                    layer['current_vol'] = max(target, layer['current_vol'] - _FADE_SPEED * 2)
                layer['channel'].set_volume(layer['current_vol'])
                if layer['current_vol'] <= 0.0 and not should_play:
                    layer['channel'].stop()
                    layer['active'] = False

    def _stop_tension_layers(self):
        if not getattr(self, '_tension_layers_ready', False):
            return
        for layer in self._tension_layers:
            if layer['active']:
                layer['channel'].stop()
                layer['active'] = False
                layer['current_vol'] = 0.0

    def _start_ambient_loop(self):
        if self._ambient_sound and self._ambient_channel and not self._ambient_playing:
            self._ambient_playing = True
            self._ambient_channel.play(self._ambient_sound, loops=-1)
            self._ambient_channel.set_volume(0.0)

    def _stop_ambient_loop(self):
        if self._ambient_channel and self._ambient_playing:
            self._ambient_channel.fadeout(1000)
            self._ambient_playing = False

    def _switch_music(self, track):
        if getattr(self, '_current_music', None) == track:
            return
        self._current_music = track
        if track in ("boss_mummy", "boss_final", "jungle", "post_boss_normal"):
            self._stop_tension_layers()
        _files = {
            "normal":           "Game/Sounds/spooky_peaceful.wav",
            "post_boss_normal": "Game/Sounds/spooky_peaceful.wav",
            "deep_crypt":       "Game/Sounds/deep_crypt.wav",
            "enchanted_tomb":   "Game/Sounds/halfway_intense.wav",
            "halfway":          "Game/Sounds/halfway_intense.wav",
            "final_push":       "Game/Sounds/final_push.wav",
            "boss_mummy":       "Game/Sounds/boss_spooky.wav",
            "boss_final":       "Game/Sounds/boss_spooky.wav",
            "jungle":           "Game/Sounds/jungle_music.wav",
        }
        _volumes = {
            "normal": 0.40,
            "post_boss_normal": 0.45,
            "deep_crypt": 0.50,
            "enchanted_tomb": 0.50,
            "halfway": 0.45,
            "final_push": 0.50,
            "boss_mummy": 0.45,
            "boss_final": 0.80,
            "jungle": 0.50,
        }
        if self._ambient_playing and self._ambient_channel:
            if track == "normal" or track == "post_boss_normal":
                self._ambient_channel.set_volume(0.0)
            elif track == "boss_final":
                self._ambient_channel.set_volume(0.08)
            else:
                self._ambient_channel.set_volume(0.15)
        try:
            pygame.mixer.music.load(_files[track])
            _vol = _volumes.get(track, 0.50)
            if track in ("boss_mummy", "boss_final"):
                pygame.mixer.music.set_volume(0.0)
                pygame.mixer.music.play(-1, fade_ms=3000)
                pygame.mixer.music.set_volume(_vol)
            else:
                pygame.mixer.music.set_volume(_vol)
                pygame.mixer.music.play(-1)
        except Exception:
            pass


# ---------------------------------------------------------------------------
class Block():
    def __init__(self, x, y, width, height, type, screen):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.screen = screen
        self.drop = False
        self.onPlatform = False
        self.wasInPlatform = False
        self.isBoundary = False
        self.isLeftBoundary = False
        self.isRightBoundary = False
        self.isInsideBox = False
        self.maxBlinkTime = random.randint(80, 180)
        self.type = type
        self.monsterBlockTimer = 0

        self.redBlock = pygame.image.load("Game/Images/Bear/redBlock.png")
        self.redBlock = pygame.transform.scale(self.redBlock, (width, height))
        self.blockClosedEyes = pygame.image.load("Game/Images/monsterBlock3.png")
        self.blockClosedEyes = pygame.transform.scale(self.blockClosedEyes, (width, height))

        if self.type == "monster":
            self.redBlock = pygame.image.load("Game/Images/monsterBlock1.png")
            self.redBlock = pygame.transform.scale(self.redBlock, (width, height))
        elif self.type == "greyRock":
            self.redBlock = pygame.image.load("Game/Images/rocks.png")
            self.redBlock = pygame.transform.scale(self.redBlock, (width, height))
        elif self.type == "checkered":
            self.redBlock = pygame.image.load("Game/Images/checkered.png")
            self.redBlock = pygame.transform.scale(self.redBlock, (width, height))
        elif self.type == "striped":
            self.redBlock = pygame.image.load("Game/Images/stripes.png")
            self.redBlock = pygame.transform.scale(self.redBlock, (width, height))
        elif self.type == "stripedFlip":
            img = pygame.image.load("Game/Images/stripes.png")
            img = pygame.transform.flip(img, True, False)
            self.redBlock = pygame.transform.scale(img, (width, height))

    def setblockXPosition(self, x):
        self.x = x

    def setDropStatus(self, drop):
        self.drop = drop

    def setIsInsideBox(self, isInsideBox):
        self.isInsideBox = isInsideBox

    def getIsInsideBox(self):
        return self.isInsideBox

    def getDropStatus(self):
        return self.drop

    def getBlockXPosition(self):
        return self.x

    def getBlockYPosition(self):
        return self.y

    def getHeight(self):
        return self.height

    def getWidth(self):
        return self.width

    def setOnPlatform(self, onPlatform):
        self.onPlatform = onPlatform

    def getOnPlatform(self):
        return self.onPlatform

    def setIsBoundary(self, isBoundary):
        self.isBoundary = isBoundary

    def getIsBoundary(self):
        return self.isBoundary

    def setIsLeftBoundary(self, isLeftBoundary):
        self.isLeftBoundary = isLeftBoundary

    def getIsLeftBoundary(self):
        return self.isLeftBoundary

    def setIsRightBoundary(self, isRightBoundary):
        self.isRightBoundary = isRightBoundary

    def getIsRightBoundary(self):
        return self.isRightBoundary

    def drawRectangle(self):
        if self.type == "monster":
            self.monsterBlockTimer += 1
        if self.monsterBlockTimer <= self.maxBlinkTime:
            self.screen.blit(self.redBlock,
                             (self.getBlockXPosition(), self.getBlockYPosition()))
        elif self.monsterBlockTimer < self.maxBlinkTime + 25:
            self.screen.blit(self.blockClosedEyes,
                             (self.getBlockXPosition(), self.getBlockYPosition()))
        else:
            self.monsterBlockTimer = 1
            self.maxBlinkTime = random.randint(150, 280)
            self.screen.blit(self.blockClosedEyes,
                             (self.getBlockXPosition(), self.getBlockYPosition()))

    def isBoundaryPresent(self, bearX, bearY):
        floorHeight = 400
        self.setIsLeftBoundary(False)
        self.setIsRightBoundary(False)

        bx2 = bearX + 100
        by2 = bearY + 100
        blx = self.getBlockXPosition()
        brx = self.getBlockXPosition() + self.getWidth()
        bty = self.getBlockYPosition()
        bby = self.getBlockYPosition() + self.getHeight()

        # On-platform detection
        if by2 == bty:
            if bx2 > blx and bearX < brx + 30:
                self.setOnPlatform(True)
                self.setDropStatus(False)

        # Off-platform (left/right fall)
        if by2 == bty and self.getOnPlatform():
            if bx2 < blx:
                self.setDropStatus(True)
                self.setOnPlatform(False)
            elif bearX > brx:
                self.setDropStatus(True)
                self.setOnPlatform(False)

        if by2 < bty and self.getOnPlatform():
            if bx2 < blx or bearX > brx:
                self.setDropStatus(True)
                self.setOnPlatform(False)

        # Inside box
        if (bx2 > blx and bx2 < brx - 30) and (by2 <= bby and by2 > bty):
            self.setIsInsideBox(True)
        elif (bearX > blx and bearX < brx) and (by2 == floorHeight) and (bty == floorHeight):
            self.setIsInsideBox(True)

        # Left boundary (bear's right edge hitting block's left side)
        if (bx2 > blx and bx2 < brx + 30) and (bearY <= bby and by2 > bty):
            self.setIsLeftBoundary(True)
            self.setDropStatus(False)

        # Right boundary (bear's left edge hitting block's right side)
        elif (bearX > blx + 30 and bearX < brx) and (by2 <= bby and by2 > bty):
            self.setIsRightBoundary(True)
            self.setDropStatus(False)

        if by2 == floorHeight:
            self.setDropStatus(False)
            self.setOnPlatform(False)


# ---------------------------------------------------------------------------
class Background():
    def __init__(self, surface):
        self.bg_pairs = []
        for i in range(1, 4):
            a = pygame.image.load(f'Game/Images/background{i}.png')
            a = pygame.transform.scale(a, (900, 700))
            b = pygame.image.load(f'Game/Images/background{i}_b.png')
            b = pygame.transform.scale(b, (900, 700))
            self.bg_pairs.append((a, b))

        self.bg_alt_pairs = []
        import os
        for i in range(1, 4):
            alt_path = f'Game/Images/background{i}_alt.png'
            if os.path.exists(alt_path):
                alt = pygame.image.load(alt_path)
                alt = pygame.transform.scale(alt, (900, 700))
            else:
                alt = self.bg_pairs[i - 1][0]
            self.bg_alt_pairs.append(alt)

        self.bgimage = self.bg_pairs[0][0]
        self.bgimage_alt = self.bg_alt_pairs[0]
        self._sway_timer  = 0
        self._sway_frame  = 0
        self._sway_period = 10

        try:
            _jungle = pygame.image.load('Game/Images/jungle_bg.png')
            self.jungle_bg = pygame.transform.scale(_jungle, (900, 700))
        except (FileNotFoundError, Exception):
            self.jungle_bg = self.bg_pairs[0][0]
        self._jungle_mode = False

        self.bgBlack  = pygame.image.load('Game/Images/black.png')
        self.bgBlack  = pygame.transform.scale(self.bgBlack, (900, 700))
        self.floor = pygame.image.load('Game/Images/wood.png')
        self.floor = pygame.transform.scale(self.floor, (900, 200))
        try:
            self.dirt_floor = pygame.image.load('Game/Images/dirt_floor.png')
            self.dirt_floor = pygame.transform.scale(self.dirt_floor, (900, 200))
        except (FileNotFoundError, Exception):
            self.dirt_floor = self.floor
        self.roof  = pygame.image.load('Game/Images/cobstone.png')
        self.roof  = pygame.transform.scale(self.roof, (900, 20))
        self.water = pygame.image.load('Game/Images/water.png')
        self.water = pygame.transform.scale(self.water, (900, 100))

        # Fire animation frames for torch overlay
        self.fire_frames = []
        for fname in ['fire.png', 'fire2.png', 'fire3.png', 'fire4.png']:
            f = pygame.image.load(f'Game/Images/{fname}').convert_alpha()
            f = pygame.transform.scale(f, (52, 52))
            self.fire_frames.append(f)
        self.fire_frame_idx = 0
        self.fire_timer = 0
        # Torch x offsets and fire position (sconce is now baked into background images)
        self.torch_offsets = [73, 233]
        self.fire_y = 148     # flame top (52px tall → flame bottom at y=200)

        self.rectBGimg = self.bgimage.get_rect()
        self.bgY1 = 0
        self.bgX1 = 0
        self.bgY2 = 0
        self.bgX2 = self.rectBGimg.width
        self.surface = surface
        # Reduced from 10 → 3 to match the slower STEP-based world movement
        self.moving_speed = 3
        self.totalX = 0
        self.stopBackground = False
        self.isBlackBackground = False

    def setBlackBackground(self, isBlackBackground):
        self.isBlackBackground = isBlackBackground

    def getBlackBackground(self):
        return self.isBlackBackground

    def setStopBackground(self, stopBackground):
        self.stopBackground = stopBackground

    def getStopBackground(self):
        return self.stopBackground

    def reset(self):
        self.stopBackground = False
        self.isBlackBackground = False
        self._black_latched = False
        self._sway_timer = 0
        self._sway_frame = 0
        self.bgimage = self.bg_pairs[0][0]
        self.bgX1 = 0
        self.bgX2 = self.rectBGimg.width

    def getBackgroundX(self):
        return self.totalX

    def setXPosition(self, totalX):
        self.totalX = totalX

    def setHardModeFloor(self):
        _tinted = self.floor.copy()
        _ov = pygame.Surface(_tinted.get_size(), pygame.SRCALPHA)
        _ov.fill((255, 120, 120))
        _tinted.blit(_ov, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        _bright = pygame.Surface(_tinted.get_size(), pygame.SRCALPHA)
        _bright.fill((80, 0, 0))
        _tinted.blit(_bright, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        self.floor = _tinted

    def render(self, total_distance=0):
        if self.isBlackBackground and not getattr(self, '_jungle_mode', False):
            self.bgimage = self.bgBlack
            self.bgimage_alt = self.bgBlack
            self._black_latched = True
            self.isBlackBackground = False
        elif getattr(self, '_jungle_mode', False):
            self._black_latched = False
            self.isBlackBackground = False
            self.bgimage = self.jungle_bg
            self.bgimage_alt = self.jungle_bg
        elif not getattr(self, '_black_latched', False):
                bg_idx = min(2, max(0, int(total_distance)) // 4500)
                self._sway_timer += 1
                if self._sway_timer >= self._sway_period:
                    self._sway_timer = 0
                    self._sway_frame = 1 - self._sway_frame
                self.bgimage = self.bg_pairs[bg_idx][self._sway_frame]
                self.bgimage_alt = self.bg_alt_pairs[bg_idx]

        if getattr(self, '_ng_blue', False):
            self.surface.fill((15, 25, 60))
        else:
            self.surface.fill((0, 0, 0))

        _bg_draw1 = self.bgimage
        _bg_draw2 = self.bgimage_alt
        if getattr(self, '_ng_blue', False) and not getattr(self, '_black_latched', False):
            _cache_key1 = id(self.bgimage)
            if getattr(self, '_blue_cache_key1', None) != _cache_key1:
                self._blue_cache_key1 = _cache_key1
                self._blue_cached1 = self.bgimage.copy()
                _blue_ov = pygame.Surface(self._blue_cached1.get_size(), pygame.SRCALPHA)
                _blue_ov.fill((80, 100, 200))
                self._blue_cached1.blit(_blue_ov, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
                _bright = pygame.Surface(self._blue_cached1.get_size(), pygame.SRCALPHA)
                _bright.fill((20, 30, 80))
                self._blue_cached1.blit(_bright, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            _bg_draw1 = self._blue_cached1

            _cache_key2 = id(self.bgimage_alt)
            if getattr(self, '_blue_cache_key2', None) != _cache_key2:
                self._blue_cache_key2 = _cache_key2
                self._blue_cached2 = self.bgimage_alt.copy()
                _blue_ov = pygame.Surface(self._blue_cached2.get_size(), pygame.SRCALPHA)
                _blue_ov.fill((80, 100, 200))
                self._blue_cached2.blit(_blue_ov, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
                _bright = pygame.Surface(self._blue_cached2.get_size(), pygame.SRCALPHA)
                _bright.fill((20, 30, 80))
                self._blue_cached2.blit(_bright, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            _bg_draw2 = self._blue_cached2

        self.surface.blit(_bg_draw1, (self.bgX1, self.bgY1))
        self.surface.blit(_bg_draw2, (self.bgX2, self.bgY2))
        _is_jungle = getattr(self, '_jungle_mode', False)
        _cur_floor = self.dirt_floor if _is_jungle else self.floor
        self.surface.blit(_cur_floor, (self.bgX1, self.bgY1 + 400))
        self.surface.blit(_cur_floor, (self.bgX2, self.bgY2 + 400))
        self.surface.blit(self.water, (self.bgX1, self.bgY1 + 600))
        self.surface.blit(self.water, (self.bgX2, self.bgY2 + 600))
        if not _is_jungle:
            self.surface.blit(self.roof, (self.bgX1, self.bgY1))
            self.surface.blit(self.roof, (self.bgX2, self.bgY2))

        # Fire is baked into background A/B images – no sprite overlay needed

    def update(self, characterPosition, height):
        if self.getStopBackground() or self.getBlackBackground():
            return

        if characterPosition >= 290:
            self.totalX += STEP
            self.bgX1 -= self.moving_speed
            self.bgX2 -= self.moving_speed
            if self.bgX1 <= -self.rectBGimg.width:
                self.bgX1 = self.rectBGimg.width
            if self.bgX2 <= -self.rectBGimg.width:
                self.bgX2 = self.rectBGimg.width
        elif characterPosition <= 180:
            self.totalX -= STEP
            self.bgX1 += self.moving_speed
            self.bgX2 += self.moving_speed
            if self.bgX1 >= self.rectBGimg.width:
                self.bgX1 = -self.rectBGimg.width
            if self.bgX2 >= self.rectBGimg.width:
                self.bgX2 = -self.rectBGimg.width


# ---------------------------------------------------------------------------
class Mummy():
    def __init__(self, x, y, width, height, mummy1Image, mummy2Image, screen):
        self.mummy1 = pygame.transform.scale(mummy1Image, (width, height))
        self.mummy2 = pygame.transform.scale(mummy2Image, (width, height))
        self.direction = -1
        self.x = x
        self.y = y
        self.destructionAnimation = 0
        self.stunned = 0
        self.screen = screen
        self.rand = random.choice([1, 2, 2, 3])
        randomMax = random.randint(300, 500)
        self.changeDirection = random.randint(200, randomMax)
        self.storeDirection = 1
        self.health = int(random.randint(7, 16) * 1.20)
        self._defense = random.randint(1, 10) / 100.0
        self._bear_x = 400
        self._bear_y = 300
        self._chase_range = random.randint(250, 450)
        self._aggro = False
        self._aggro_delay = random.randint(0, 90)
        self._aggro_timer = 0
        self._sep_offset = 0.0
        self._personality = random.choice(['aggressive', 'cautious', 'flanker'])
        self._preferred_gap = random.randint(50, 120)
        self._vy = 0.0
        self._gravity = 0.5
        self._on_ground = True
        self._jump_cooldown = 0
        self._FLOOR_Y = 400
        self.fire = pygame.image.load("Game/Images/fire.png")
        self.fire = pygame.transform.scale(self.fire, (60, 60))
        self.hurtMummy = pygame.image.load("Game/Images/Mummy/hurtMummy.png")
        self.hurtMummy = pygame.transform.scale(self.hurtMummy, (width, height))
        self.hurtLeftMummy = pygame.transform.flip(self.hurtMummy, True, False)
        self.hurtLeftMummy = pygame.transform.scale(self.hurtLeftMummy, (width, height))
        self.damageAttack = 11
        self.hp = 120
        self.height = height
        self.width = width
        self.hurtTimer = 0
        self.isMonsterHurtAnimation = 0
        self.damageReceived = 0
        self.exp = 4
        self.isHurtAnimationStarted = False
        self.isHurtTimer = 0
        self.startDestructionAnimation = False
        self.blocks = []   # set each frame by the game loop for wall collision

        # Walk-frame outlines (only used by the big mummy)
        self.mummy1Outline = None
        self.mummy2Outline = None

        # White flash surface for hurt highlight (big mummy only)
        self.hurtFlash = None

        if height > 100:  # Big mummy – use dedicated art with forehead marker
            self.damageAttack = 13
            self.exp = 20
            self.health = int(24 * 1.20)
            raw1     = pygame.image.load("Game/Images/Mummy/mummy1Big.png")
            raw_hurt = pygame.image.load("Game/Images/Mummy/hurtMummy.png")
            # Use the same art for both walk frames (flipped) so the character
            # looks consistent – same forehead ring, same body shape.
            self.mummy1      = pygame.transform.scale(raw1,     (width, height))
            self.mummy2      = pygame.transform.flip(self.mummy1, True, False)
            self.hurtMummy   = pygame.transform.scale(raw_hurt, (width, height))
            self.hurtLeftMummy = pygame.transform.flip(self.hurtMummy, True, False)
            self.changeDirection = random.randint(800, 1200)
            self.mummy1Outline = create_outline_surface(self.mummy1)
            self.mummy2Outline = create_outline_surface(self.mummy2)
            # Pre-create the white flash overlay (reused every hurt frame)
            self.hurtFlash = pygame.Surface((width, height), pygame.SRCALPHA)
            self.hurtFlash.fill((255, 255, 255, 140))

        # Outline surfaces built AFTER final hurt sprites are set
        self.hurtOutline     = create_outline_surface(self.hurtMummy)
        self.hurtLeftOutline = create_outline_surface(self.hurtLeftMummy)
        # Record maximum health for temporary health-bar rendering
        self.max_health = self.health

    def setStartDestructionAnimation(self, v):
        self.startDestructionAnimation = v

    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation

    def setBlocks(self, blocks):
        self.blocks = blocks

    def setDirection(self, direction):
        self.direction = direction

    def getDirection(self):
        return self.direction

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer

    def getHurtTimer(self):
        return self.isHurtTimer

    def setIsHurtAnimationStarted(self, v):
        self.isHurtAnimationStarted = v

    def getIsHurtAnimationStarted(self):
        return self.isHurtAnimationStarted

    def getExp(self):
        return self.exp

    def setIsMonsterHurtAnimation(self, v):
        self.isMonsterHurtAnimation = v

    def getIsMonsterHurtAnimation(self):
        return self.isMonsterHurtAnimation

    def setHp(self, hp):
        self.hp = hp

    def getHp(self):
        return self.hp

    def setDamageAttack(self, v):
        self.damageAttack = v

    def getDamageAttack(self):
        return self.damageAttack

    def setXPosition(self, x):
        self.x = x

    def getXPosition(self):
        return self.x

    def setHealth(self, health):
        self.health = health

    def getHealth(self):
        return self.health

    def setYPosition(self, y):
        self.y = y

    def getYPosition(self):
        return self.y

    def setStunned(self, stunned):
        self.stunned = stunned

    def getStunned(self):
        return self.stunned

    def getName(self):
        return "bigMummy" if self.height > 100 else "mummy"

    def getDestructionAnimationCount(self):
        return self.destructionAnimation

    def getHeight(self):
        return self.height

    def setDamageReceived(self, v):
        self.damageReceived = v

    def getDamageReceived(self):
        return self.damageReceived

    def displayDamageOnMonster(self, damage):
        stunned_val = getattr(self, 'stunned', 1)
        try:
            s = int(stunned_val)
        except Exception:
            s = 1
        fade_frames = 8
        alpha = int(255 * min(max(0, s), fade_frames) / float(fade_frames))
        render_damage_text(self.screen, _FONT_DAMAGE, damage,
                            self.getXPosition() + 60, self.getYPosition() - 60,
                            alpha=alpha)

    def drawDestruction(self, damage):
        self.destructionAnimation += 1
        self.displayDamageOnMonster(damage)
        is_big = self.height > 100
        _limit = 60 if is_big else 30
        if self.destructionAnimation < _limit and self.destructionAnimation % 2 == 0:
            _num = 2 if is_big else 1
            for _ in range(_num):
                self.screen.blit(self.fire,
                                 (self.x + random.randint(-100, 20),
                                  self.y + random.randint(-100, 20)))

    def _hits_block(self, new_x):
        """Return True if moving to new_x would overlap a block horizontally."""
        _dy = 20
        m_top    = self.y + _dy
        m_bottom = self.y + _dy + self.height
        m_left   = new_x
        m_right  = new_x + self.width
        for b in self.blocks:
            bx = b.getBlockXPosition()
            by = b.getBlockYPosition()
            bx2 = bx + b.getWidth()
            by2 = by + b.getHeight()
            if m_bottom <= by + 6 or m_top >= by2:
                continue
            if m_right > bx and m_left < bx2:
                return True
        return False

    def _apply_gravity_and_platforms(self):
        if self.height > 100:
            return
        if self._jump_cooldown > 0:
            self._jump_cooldown -= 1

        self._vy += self._gravity
        self.y += self._vy

        feet_y = self.y + self.height
        self._on_ground = False

        for b in self.blocks:
            bx = b.getBlockXPosition()
            by = b.getBlockYPosition()
            bw = b.getWidth()
            bh = b.getHeight()
            if self._vy >= 0 and self.x + self.width > bx + 10 and self.x < bx + bw - 10:
                old_feet = feet_y - self._vy
                if old_feet <= by + 4 and feet_y >= by:
                    self.y = by - self.height
                    self._vy = 0
                    self._on_ground = True
                    break

        if self.y + self.height >= self._FLOOR_Y:
            self.y = self._FLOOR_Y - self.height
            self._vy = 0
            self._on_ground = True

        if self._on_ground and self._jump_cooldown <= 0:
            feet_y = self.y + self.height
            on_platform = feet_y < self._FLOOR_Y - 5

            if on_platform:
                bear_below = self._bear_y > self.y + 40
                if bear_below and random.random() < 0.02:
                    self._vy = 0
                    self._on_ground = False
                    self._jump_cooldown = 60
                    _js = getattr(self, '_jump_sound', None)
                    if _js: _js.play()
                elif random.random() < 0.008:
                    self._vy = -8 - random.random() * 2
                    self._on_ground = False
                    self._jump_cooldown = 90
                    _js = getattr(self, '_jump_sound', None)
                    if _js: _js.play()
            else:
                bear_above = self._bear_y < self.y - 60
                if bear_above and self._aggro and random.random() < 0.025:
                    self._vy = -10 - random.random() * 2
                    self._on_ground = False
                    self._jump_cooldown = 60
                    _js = getattr(self, '_jump_sound', None)
                    if _js: _js.play()

    def drawMonster(self):
        _dy = 20  # push sprite down so feet touch the floor
        is_big = self.height > 100

        if getattr(self, '_popup_frozen', False):
            self.screen.blit(self.mummy1, (self.x, self.y + _dy))
            if self.health < self.max_health:
                render_enemy_health_bar(self.screen, self.x, self.y - 20, self.health, self.max_health)
            return

        if not is_big:
            self._apply_gravity_and_platforms()

        # ── Walking frames ────────────────────────────────────────────────────
        if self.stunned == 0:
            if self.x % 90 < 40:
                if is_big and self.mummy1Outline:
                    self.screen.blit(self.mummy1Outline, (self.x, self.y + _dy))
                self.screen.blit(self.mummy1, (self.x, self.y + _dy))
            else:
                if is_big and self.mummy2Outline:
                    self.screen.blit(self.mummy2Outline, (self.x, self.y + _dy))
                self.screen.blit(self.mummy2, (self.x, self.y + _dy))

        # ── Movement / direction ──────────────────────────────────────────────
        if self.stunned == 0:
            _dx = self._bear_x - self.x
            _dist = abs(_dx)

            self._aggro_timer += 1
            if _dist < self._chase_range and self._aggro_timer >= self._aggro_delay:
                self._aggro = True
            elif _dist > self._chase_range + 150:
                self._aggro = False
                self._aggro_timer = 0

            if self._aggro and _dist > 20:
                if self._personality == 'cautious' and _dist < self._preferred_gap:
                    _want_dir = -1 if _dx > 0 else 1
                elif self._personality == 'flanker':
                    _flank_side = 1 if id(self) % 2 == 0 else -1
                    if _dist < 80:
                        _want_dir = _flank_side
                    else:
                        _want_dir = 1 if _dx > 0 else -1
                else:
                    _want_dir = 1 if _dx > 0 else -1
                if _want_dir != self.direction:
                    self.direction = _want_dir
                    self.mummy1 = pygame.transform.flip(self.mummy1, True, False)
                    self.mummy2 = pygame.transform.flip(self.mummy2, True, False)
                    if is_big and self.mummy1Outline:
                        self.mummy1Outline = pygame.transform.flip(self.mummy1Outline, True, False)
                        self.mummy2Outline = pygame.transform.flip(self.mummy2Outline, True, False)
                _speed = self.rand + (1 if _dist < 150 else 0)
            else:
                _speed = self.rand

            new_x = self.x + self.direction * _speed + self._sep_offset
            self._sep_offset *= 0.9
            if self._hits_block(new_x):
                self.direction *= -1
                self.mummy1 = pygame.transform.flip(self.mummy1, True, False)
                self.mummy2 = pygame.transform.flip(self.mummy2, True, False)
                if is_big and self.mummy1Outline:
                    self.mummy1Outline = pygame.transform.flip(self.mummy1Outline, True, False)
                    self.mummy2Outline = pygame.transform.flip(self.mummy2Outline, True, False)
            else:
                self.x = new_x

        # ── Hurt / stunned frames ─────────────────────────────────────────────
        elif self.stunned > 0 and self.direction > 0:
            self.stunned += 1
            if is_big:
                self.screen.blit(self.hurtOutline, (self.x, self.y + _dy))
            self.screen.blit(self.hurtMummy, (self.x, self.y + _dy))
            if is_big and self.hurtFlash:
                self.screen.blit(self.hurtFlash, (self.x, self.y + _dy))
            elif self.stunned <= 8:
                self.screen.blit(self.hurtOutline, (self.x, self.y + _dy))
            if self.stunned == 20:
                self.stunned = 0
        elif self.stunned > 0 and self.direction < 0:
            self.stunned += 1
            if is_big:
                self.screen.blit(self.hurtLeftOutline, (self.x, self.y + _dy))
            self.screen.blit(self.hurtLeftMummy, (self.x, self.y + _dy))
            if is_big and self.hurtFlash:
                self.screen.blit(self.hurtFlash, (self.x, self.y + _dy))
            elif self.stunned <= 8:
                self.screen.blit(self.hurtLeftOutline, (self.x, self.y + _dy))
            if self.stunned == 20:
                self.stunned = 0

        # ── Auto-reverse direction ────────────────────────────────────────────
        if self.x % self.changeDirection == 0 and self.stunned == 0:
            self.direction *= -1
            self.mummy1 = pygame.transform.flip(self.mummy1, True, False)
            self.mummy2 = pygame.transform.flip(self.mummy2, True, False)
            if is_big and self.mummy1Outline:
                self.mummy1Outline = pygame.transform.flip(self.mummy1Outline, True, False)
                self.mummy2Outline = pygame.transform.flip(self.mummy2Outline, True, False)

        if self.health < self.max_health:
            render_enemy_health_bar(self.screen, self.x, self.y - 20, self.health, self.max_health)


# ---------------------------------------------------------------------------
class Witch():
    def __init__(self, x, y, witch1Image, witch2Image, screen, fireball_sound=None):
        self.witch = pygame.transform.scale(witch1Image, (100, 100))
        self.witch2 = pygame.transform.scale(witch2Image, (100, 100))
        self.hurtWitch = pygame.image.load("Game/Images/Bear/hurtWitch.png")
        self.hurtWitch = pygame.transform.scale(self.hurtWitch, (100, 100))
        self._facing = -1
        self.directionX = -1
        self.x = x
        self.y = y
        self.destructionAnimation = 0
        self.stunned = 0
        self.screen = screen
        self.fireball_sound = fireball_sound
        self.rand = random.choice([1, 1, 2])
        self.health = int(random.randint(24, 42) * 1.20)
        self.max_health = self.health
        self._defense = random.randint(1, 10) / 100.0
        self.fire = pygame.image.load("Game/Images/fire2.png")
        self.fire = pygame.transform.scale(self.fire, (60, 60))
        self.changeDirectionX = random.randint(400, 700)
        self.changeDirectionY = random.randint(60, 100)
        self.storeDirection = 1
        self.directionY = 1
        self.setThrowsFireBall = False
        self.fireBallAnimationCounter = 0
        self.damageAttack = 7
        self.hp = 120
        self.isMonsterHurtAnimation = 0
        self.damageReceived = 0
        self.exp = 12
        self.isHurtAnimationStarted = False
        self.isHurtTimer = 0
        self._bear_x = 400
        self._bear_y = 300
        self._preferred_dist = random.randint(150, 280)
        self._strafe_timer = random.randint(0, 60)
        self._sep_offset = 0.0
        self._state = 'approach'
        self._state_timer = 0
        self._dodge_dir = random.choice([-1, 1])
        self._aggro_range = random.randint(400, 600)
        self.startDestructionAnimation = False

    def setStartDestructionAnimation(self, v):
        self.startDestructionAnimation = v

    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer

    def getHurtTimer(self):
        return self.isHurtTimer

    def setIsHurtAnimationStarted(self, v):
        self.isHurtAnimationStarted = v

    def getIsHurtAnimationStarted(self):
        return self.isHurtAnimationStarted

    def getExp(self):
        return self.exp

    def setIsMonsterHurtAnimation(self, v):
        self.isMonsterHurtAnimation = v

    def getIsMonsterHurtAnimation(self):
        return self.isMonsterHurtAnimation

    def setHp(self, hp):
        self.hp = hp

    def getHp(self):
        return self.hp

    def setDamageAttack(self, v):
        self.damageAttack = v

    def getDamageAttack(self):
        return self.damageAttack

    def setXPosition(self, x):
        self.x = x

    def getXPosition(self):
        return self.x

    def setHealth(self, health):
        self.health = health

    def getHealth(self):
        return self.health

    def setYPosition(self, y):
        self.y = y

    def getYPosition(self):
        return self.y

    def setStunned(self, stunned):
        self.stunned = stunned

    def getStunned(self):
        return self.stunned

    def getDestructionAnimationCount(self):
        return self.destructionAnimation

    def getName(self):
        return "witch"

    def setThrowsFireBalls(self, v):
        self.setThrowsFireBall = v

    def getThrowsFireBalls(self):
        return self.setThrowsFireBall

    def setDamageReceived(self, v):
        self.damageReceived = v

    def getDamageReceived(self):
        return self.damageReceived

    def displayDamageOnMonster(self, damage):
        stunned_val = getattr(self, 'stunned', 1)
        try:
            s = int(stunned_val)
        except Exception:
            s = 1
        fade_frames = 8
        alpha = int(255 * min(max(0, s), fade_frames) / float(fade_frames))
        render_damage_text(self.screen, _FONT_DAMAGE, damage,
                            self.getXPosition() + 60, self.getYPosition() - 60,
                            alpha=alpha)

    def drawDestruction(self, damage):
        self.destructionAnimation += 1
        self.displayDamageOnMonster(damage)
        if self.destructionAnimation < 30 and self.destructionAnimation % 2 < 10:
            self.screen.blit(self.fire,
                             (self.x + random.randint(-100, 0),
                              self.y + random.randint(-100, 0)))

    def _flip_all_to(self, new_facing):
        if new_facing == self._facing:
            return
        self._facing = new_facing
        self.witch = pygame.transform.flip(self.witch, True, False)
        self.witch2 = pygame.transform.flip(self.witch2, True, False)
        self.hurtWitch = pygame.transform.flip(self.hurtWitch, True, False)

    def drawMonster(self):
        if getattr(self, '_popup_frozen', False):
            self.screen.blit(self.witch, (self.x, self.y))
            if self.health < self.max_health:
                render_enemy_health_bar(self.screen, self.x, self.y - 15, self.health, self.max_health)
            return

        _dx = self._bear_x - self.x
        _dy_b = self._bear_y - self.y
        _dist = abs(_dx)

        _want_face = 1 if _dx > 0 else -1
        self._flip_all_to(_want_face)
        self.directionX = _want_face

        if self.stunned == 0:
            if not self.setThrowsFireBall:
                self.screen.blit(self.witch, (self.x, self.y))
            else:
                self.fireBallAnimationCounter += 1
                if self.fireBallAnimationCounter == 1 and self.fireball_sound:
                    self.fireball_sound.play()
                self.screen.blit(self.witch2, (self.x, self.y))

        if self.fireBallAnimationCounter > 50:
            self.fireBallAnimationCounter = 0
            self.setThrowsFireBalls(False)

        if self.stunned == 0:
            self._strafe_timer += 1
            self._state_timer += 1

            if _dist > self._aggro_range:
                self._state = 'idle'
            elif self._state == 'idle' and _dist < self._aggro_range:
                self._state = 'approach'
                self._state_timer = 0

            if self._state == 'approach':
                _move_x = 1 if _dx > 0 else -1
                _spd = self.rand + 2
                if _dist < self._preferred_dist + 30:
                    self._state = random.choice(['strafe', 'dive', 'orbit'])
                    self._state_timer = 0
                    self._dodge_dir = random.choice([-1, 1])
            elif self._state == 'strafe':
                if _dist < self._preferred_dist - 50:
                    _move_x = -1 if _dx > 0 else 1
                elif _dist > self._preferred_dist + 60:
                    _move_x = 1 if _dx > 0 else -1
                else:
                    _move_x = self._dodge_dir
                _spd = self.rand + 1
                if self._state_timer > random.randint(40, 90):
                    self._dodge_dir *= -1
                    self._state_timer = 0
                    if random.random() < 0.3:
                        self._state = random.choice(['approach', 'dive', 'orbit'])
                if _dist > self._preferred_dist + 120:
                    self._state = 'approach'
                    self._state_timer = 0
            elif self._state == 'dive':
                _move_x = 1 if _dx > 0 else -1
                _spd = self.rand + 3
                if self._state_timer > 30 or _dist < 40:
                    self._state = 'retreat'
                    self._state_timer = 0
            elif self._state == 'retreat':
                _move_x = -1 if _dx > 0 else 1
                _spd = self.rand + 2
                if self._state_timer > 40:
                    self._state = 'strafe'
                    self._state_timer = 0
                    self._dodge_dir = random.choice([-1, 1])
            elif self._state == 'orbit':
                _move_x = self._dodge_dir
                _spd = self.rand + 2
                if self._state_timer > 120:
                    self._state = 'approach'
                    self._state_timer = 0
                elif self._state_timer % 50 == 49:
                    self._dodge_dir *= -1
            elif self._state == 'idle':
                _move_x = self._dodge_dir
                _spd = self.rand + 1
                if self._strafe_timer % 60 == 0:
                    self._dodge_dir *= -1
            else:
                _move_x = 0
                _spd = self.rand

            if self.y > 60 and _dy_b < -40:
                _move_y = -(self.rand + 1)
            elif self.y < 300 and _dy_b > 40:
                _move_y = self.rand + 1
            elif abs(_dy_b) < 30:
                _move_y = self._dodge_dir * (self.rand + 1) if self._strafe_timer % 40 < 20 else 0
            else:
                _move_y = self._dodge_dir if self._state == 'orbit' else 0

            self.x += _move_x * _spd + self._sep_offset
            self._sep_offset *= 0.9
            self.y += _move_y

            self.x = max(-50, min(860, self.x))
            self.y = max(30, min(350, self.y))
        elif self.stunned > 0:
            self.stunned += 1
            self.screen.blit(self.hurtWitch, (self.x, self.y))
            if self.stunned == 20:
                self.stunned = 0

        if self.health < self.max_health:
            render_enemy_health_bar(self.screen, self.x, self.y - 15, self.health, self.max_health)


# ---------------------------------------------------------------------------
class FireBall():
    def __init__(self, x, y, vel_x, vel_y, fireballImage, screen, size=(60, 60)):
        self.x = x
        self.y = y
        self.vel_x = vel_x
        self.vel_y = -1 * vel_y
        self.screen = screen
        # Pre-scale once; reused every frame
        self.fire = pygame.transform.scale(fireballImage, size)
        self.stunned = False
        self.health = 1
        self.damageAttack = 6
        self.isHurtTimer = 0

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer

    def getHurtTimer(self):
        return self.isHurtTimer

    def setDamageAttack(self, v):
        self.damageAttack = v

    def getDamageAttack(self):
        return self.damageAttack

    def setXPosition(self, x):
        self.x = x

    def getXPosition(self):
        return self.x

    def setYPosition(self, y):
        self.y = y

    def getYPosition(self):
        return self.y

    def getName(self):
        return "fireBall"

    def setStunned(self, stunned):
        self.stunned = stunned

    def getStunned(self):
        return self.stunned

    def setHealth(self, health):
        self.health = health

    def getHealth(self):
        return self.health

    def drawFireBall(self):
        if self.y < 370:
            self.y -= self.vel_y
            self.x += self.vel_x
        else:
            self.vel_y *= -1
            self.y -= self.vel_y
            _bs = getattr(self, '_bounce_sound', None)
            if _bs: _bs.play()
        self.screen.blit(self.fire, (self.x, self.y))

    def drawFireBallFrozen(self):
        self.screen.blit(self.fire, (self.x, self.y))


# ---------------------------------------------------------------------------
class GreenBlob():
    def __init__(self, x, y, height, width, screen, blob_jump_sound=None):
        self.height = height
        self.width = width
        self.greenBlob = pygame.image.load("Game/Images/greenBlob.png")
        self.greenBlob = pygame.transform.scale(self.greenBlob, (self.width, self.height))
        self.comingUp = False
        self.direction = -1 * random.randint(1, 2)
        self.x = x
        self.y = y
        self.health = int(26 * 1.20)
        self._defense = random.randint(1, 10) / 100.0
        self.destructionAnimation = 0
        self.stunned = 0
        self.screen = screen
        self.blob_jump_sound = blob_jump_sound
        self.rand = random.choice([1, 1, 2, 2, 3])
        randomMax = random.randint(120, 250)
        self.changeDirection = random.randint(80, randomMax)
        self._bear_x = 400
        self._bear_y = 300
        self._sep_offset = 0.0
        self._chase_range = random.randint(300, 500)
        self._preferred_gap = random.randint(30, 100)
        self._personality = random.choice(['aggressive', 'aggressive', 'cautious', 'flanker'])
        self.jump = False
        self.comingDown = False
        self.nextJumpTimer = random.randint(80, 200)
        self.timer = 0
        self.hurtGreenBlob = pygame.image.load("Game/Images/greenBlob2.png")
        self.hurtGreenBlob = pygame.transform.scale(self.hurtGreenBlob, (100, 100))
        self.fire = pygame.image.load("Game/Images/fire.png")
        self.fire = pygame.transform.scale(self.fire, (60, 60))
        self.damageAttack = 16
        self.hp = int(26 * 1.20)
        self.hurtTimer = 0
        self.isMonsterHurtAnimation = 0
        self.damageReceived = 0
        self.exp = 14
        self.isHurtAnimationStarted = False
        self.isHurtTimer = 0
        self.startDestructionAnimation = False

        if self.height >= 200:
            self.height = 500
            self.width = 300
            self.health = int(60 * 1.20)
            self.exp = 40
            self.damageAttack = 34

        # record max health for temporary health-bar rendering
        self.max_health = self.health

    def setStartDestructionAnimation(self, v):
        self.startDestructionAnimation = v

    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer

    def getHurtTimer(self):
        return self.isHurtTimer

    def setIsHurtAnimationStarted(self, v):
        self.isHurtAnimationStarted = v

    def getIsHurtAnimationStarted(self):
        return self.isHurtAnimationStarted

    def getExp(self):
        return self.exp

    def setDamageReceived(self, v):
        self.damageReceived = v

    def getDamageReceived(self):
        return self.damageReceived

    def setIsMonsterHurtAnimation(self, v):
        self.isMonsterHurtAnimation = v

    def getIsMonsterHurtAnimation(self):
        return self.isMonsterHurtAnimation

    def setHp(self, hp):
        self.hp = hp

    def getHp(self):
        return self.hp

    def setDamageAttack(self, v):
        self.damageAttack = v

    def getDamageAttack(self):
        return self.damageAttack

    def setXPosition(self, x):
        self.x = x

    def getXPosition(self):
        return self.x

    def setHealth(self, health):
        self.health = health

    def getHealth(self):
        return self.health

    def getHeight(self):
        return self.height

    def setYPosition(self, y):
        self.y = y

    def getYPosition(self):
        return self.y

    def setStunned(self, stunned):
        self.stunned = stunned

    def getStunned(self):
        return self.stunned

    def getName(self):
        return "bigGreenBlob" if self.height >= 200 else "greenBlob"

    def getDestructionAnimationCount(self):
        return self.destructionAnimation

    def displayDamageOnMonster(self, damage):
        stunned_val = getattr(self, 'stunned', 1)
        try:
            s = int(stunned_val)
        except Exception:
            s = 1
        fade_frames = 8
        alpha = int(255 * min(max(0, s), fade_frames) / float(fade_frames))
        render_damage_text(self.screen, _FONT_DAMAGE, damage,
                            self.getXPosition() + 60, self.getYPosition() - 60,
                            alpha=alpha)

    def drawDestruction(self, damage):
        self.destructionAnimation += 1
        self.displayDamageOnMonster(damage)
        if self.destructionAnimation < 30 and self.destructionAnimation % 2 == 0:
            self.screen.blit(self.fire,
                             (self.x + random.randint(-100, 0),
                              self.y + random.randint(-100, 0)))

    def drawMonster(self):
        if getattr(self, '_popup_frozen', False):
            self.screen.blit(self.greenBlob, (self.x, self.y))
            if self.health < self.max_health:
                render_enemy_health_bar(self.screen, self.x, self.y - 10, self.health, self.max_health)
            return

        self.timer += 1

        if self.jump:
            if self.y + self.height <= 80 and not self.comingDown:
                self.comingDown = True
                self.y += JUMP_STEP
            elif not self.comingDown:
                self.y -= JUMP_STEP
            elif self.y + self.height < 400 and self.comingDown:
                self.y += JUMP_STEP
            elif self.y + self.height >= 400 and self.comingDown:
                self.jump = False
                self.timer = 0
                self.comingDown = False
                self.nextJump = random.randint(30, 80)

        if self.timer == self.nextJumpTimer:
            self.jump = True
            if self.blob_jump_sound:
                self.blob_jump_sound.play()

        if self.stunned == 0:
            self.screen.blit(self.greenBlob, (self.x, self.y + 10))
            _dx = self._bear_x - self.x
            _dist = abs(_dx)
            if _dist < self._chase_range:
                if self._personality == 'cautious' and _dist < self._preferred_gap:
                    _want_dir = -1 if _dx > 0 else 1
                elif self._personality == 'flanker' and _dist < 80:
                    _want_dir = 1 if id(self) % 2 == 0 else -1
                else:
                    _want_dir = 1 if _dx > 0 else -1
                if _want_dir != self.direction:
                    self.direction = _want_dir
                    self.greenBlob = pygame.transform.flip(self.greenBlob, True, False)
                _spd = self.rand + (1 if _dist < 200 else 0)
            else:
                _spd = self.rand
            self.x += self.direction * _spd + self._sep_offset
            self._sep_offset *= 0.9
        elif self.stunned > 0:
            self.stunned += 1
            self.screen.blit(self.hurtGreenBlob, (self.x, self.y + 10))
            if self.stunned == 20:
                self.stunned = 0

        if self.x % self.changeDirection == 0 and self.stunned == 0 and abs(self._bear_x - self.x) > 400:
            self.direction *= -1
            self.greenBlob = pygame.transform.flip(self.greenBlob, True, False)

        if self.health < self.max_health:
            render_enemy_health_bar(self.screen, self.x, self.y - 10, self.health, self.max_health)


# ---------------------------------------------------------------------------
class Bear:
    def __init__(self, x, y, screen, thud_sound=None):
        self.screen = screen
        self.thud_sound = thud_sound
        self.textTimer = 0
        self.xText = 200
        self.yText = 100
        self.indexArray = 0
        self.blinkTimer = 0
        self.timerHpText = 0
        self.displayTimer = 0
        self.totalText1 = ""
        self.totalText2 = ""
        self.totalText3 = ""
        self.line = 0
        self.x = x
        self.y = y
        self.initialHeight = 300
        self.sourceBlock = None
        self._drop_timer = 0         # frames remaining to skip sourceBlock (drop-through)
        self.jumping = False
        self.jumpLeft = False
        self.jumpVelocity = 0.0      # px/frame upward; positive = rising
        self.level = 1
        self.textHeight = 30
        self.randomBlink = random.randint(15, 30)
        self.talking  = pygame.image.load("Game/Images/Talking.png")
        self.talking  = pygame.transform.scale(self.talking,  (900, 250))
        self.talking2 = pygame.image.load("Game/Images/Talking2.png")
        self.talking2 = pygame.transform.scale(self.talking2, (900, 250))
        self.talkingNoBear = pygame.image.load("Game/Images/TalkingNoBear.png")
        self.talkingNoBear = pygame.transform.scale(self.talkingNoBear, (900, 250))
        self.bearJumping1 = pygame.image.load("Game/Images/Bear/bearJump1.png")
        self.bearJumping1 = pygame.transform.scale(self.bearJumping1, (120, 105))
        self.endText = False
        self.maxHp = 100
        self.attack = 10
        self.hp = 100
        self.maxExp = 12
        self.exp = 0
        self.text1 = ""
        self.text2 = ""
        self.text3 = ""
        self.textArray = [
            ['To jump press "z"', 'To attack press "a"',
             'Press "s" to continue'],
            ['Press "ESC" to end game',
             'Defeat Frankenbear at end of castle!',
             'Press "s" to continue']
        ]
        self.tupleIndex = 0
        # False = no bear face (tutorial msgs), True = show bear face (story msgs)
        self.showBearArray = [False, False]
        self.bearJumping2 = pygame.image.load("Game/Images/Bear/bearJump2.png")
        self.bearJumping2 = pygame.transform.scale(self.bearJumping2, (120, 105))
        self.bearJumpingLeft1 = pygame.transform.flip(
            pygame.image.load("Game/Images/Bear/bearJump1.png"), True, False)
        self.bearJumpingLeft1 = pygame.transform.scale(self.bearJumpingLeft1, (120, 105))
        self.bearJumpingLeft2 = pygame.transform.flip(
            pygame.image.load("Game/Images/Bear/bearJump2.png"), True, False)
        self.bearJumpingLeft2 = pygame.transform.scale(self.bearJumpingLeft2, (120, 105))
        self.damageAttack = 2
        self.fireballDamage = 1
        self.hurtTimer = 0
        self.leftDirection = False
        self.comingUp = False
        self.coins = 0
        self.has_shield = False
        self.has_aimer = False
        self.has_50pct_protection = False
        # Crouch mechanic
        self.is_crouching = False
        self.crouch_sprite = None  # crouchBear.png not available
        self.crouch_sprite_left = None
        # Poison mechanic
        self.poison_timer = 0
        self.poison_damage_tick = 0
        self._move_speed = 0.0
        self._move_accel = 0.25
        self._move_friction = 0.35
        self._coyote_timer = 0
        self._coyote_max = 6
        self._jump_buffer = 0
        self._jump_buffer_max = 8
        self._land_squash = 0
        self._was_on_ground = True
        self._move_dir = 0
        self._speed_lerp = 8.0

    def setArrayText(self, text):
        self.textArray.append(text)
        self.showBearArray.append(True)

    def getArrayText(self):
        return self.textArray

    def clearArray(self):
        self.textArray.clear()

    def setHurtTimer(self, hurtTimer):
        self.hurtTimer = hurtTimer

    def getHurtTimer(self):
        return self.hurtTimer

    def setHp(self, hp):
        self.hp = hp

    def getHp(self):
        return self.hp

    def setDamageAttack(self, damageAttack):
        self.damageAttack = damageAttack

    def getDamageAttack(self):
        return self.damageAttack

    def setXPosition(self, x):
        self.x = x

    def getXPosition(self):
        return self.x

    def setInitialHeight(self, height):
        self.initialHeight = height

    def getInitialHeight(self):
        return self.initialHeight

    def setYPosition(self, y):
        self.y = y

    def getYPosition(self):
        return self.y

    def setJumpStatus(self, jump):
        self.jumping = jump

    def getJumpStatus(self):
        return self.jumping

    def setLeftJumpStatus(self, leftJump):
        self.jumpLeft = leftJump

    def getLeftJumpStatus(self):
        return self.jumpLeft

    def setLeftDirection(self, direction):
        self.leftDirection = direction

    def getLeftDirection(self):
        return self.leftDirection

    def setComingUpStatus(self, comingUp):
        self.comingUp = comingUp

    def getComingUp(self):
        return self.comingUp

    def setHealth(self, health):
        self.hp = health

    def getHealth(self):
        return self.hp

    def setLevel(self, level):
        self.level = level

    def getLevel(self):
        return self.level

    def set_crouch(self, is_crouching):
        """Set crouch state."""
        self.is_crouching = is_crouching

    def get_crouch(self):
        """Check if currently crouching."""
        return self.is_crouching

    def set_poison(self, seconds):
        """Apply poison for N seconds (30 default)."""
        self.poison_timer = seconds * 60  # Convert to frames (60 fps)
        self.poison_damage_tick = 0

    def update_poison(self):
        """Update poison timer, apply damage every 2 seconds."""
        if self.poison_timer > 0:
            self.poison_timer -= 1
            self.poison_damage_tick += 1
            # Apply 2 damage every 2 seconds (120 frames)
            if self.poison_damage_tick >= 120:
                self.hp = max(0, self.hp - 2)
                self.poison_damage_tick = 0

    def is_poisoned(self):
        """Check if currently poisoned."""
        return self.poison_timer > 0

    def update_movement(self, moving, direction, max_step):
        """Update horizontal velocity with acceleration/deceleration."""
        if moving:
            self._move_dir = direction
            self._move_speed = min(max_step, self._move_speed + max_step * self._move_accel)
        else:
            self._move_speed = max(0.0, self._move_speed - max_step * self._move_friction)
        if self._move_speed < 0.5:
            self._move_speed = 0.0

    def get_effective_step(self, max_step):
        """Return integer step based on current velocity."""
        return max(1, int(round(self._move_speed))) if self._move_speed > 0 else max_step

    def update_coyote(self, on_ground):
        """Track coyote time — grace period after leaving a ledge."""
        if on_ground:
            self._was_on_ground = True
            self._coyote_timer = 0
        else:
            if self._was_on_ground:
                self._coyote_timer = self._coyote_max
                self._was_on_ground = False
            if self._coyote_timer > 0:
                self._coyote_timer -= 1

    def can_coyote_jump(self):
        """True if within coyote-time grace period (just left ground, not from a jump)."""
        return self._coyote_timer > 0

    def buffer_jump(self):
        """Record that jump was pressed (for jump buffering). Only call on fresh key press."""
        self._jump_buffer = self._jump_buffer_max

    def consume_jump_buffer(self):
        """Check and consume buffered jump. Returns True if a jump was buffered."""
        if self._jump_buffer > 0:
            self._jump_buffer = 0
            return True
        return False

    def tick_jump_buffer(self):
        """Decrement jump buffer timer each frame."""
        if self._jump_buffer > 0:
            self._jump_buffer -= 1

    def trigger_land_squash(self, intensity=6):
        """Trigger visual squash on landing."""
        self._land_squash = intensity

    def get_land_squash_scale(self):
        """Returns (width_scale, height_scale) for squash-and-stretch."""
        if self._land_squash > 0:
            self._land_squash -= 1
            t = self._land_squash / 6.0
            return (1.0 + 0.15 * t, 1.0 - 0.12 * t)
        return (1.0, 1.0)

    def startJump(self):
        """Kick off a new jump – sets initial upward velocity."""
        self.jumpVelocity = 16.8   # tuned so peak ≈ 217 px – clears y=190 blocks
        self.comingUp = True
        self._coyote_timer = 0
        self._jump_buffer = 0
        try:
            if hasattr(self, 'jump_scream_sound') and self.jump_scream_sound:
                self.jump_scream_sound.play()
        except:
            pass

    def _jumpPhysics(self, blocks):
        """
        Velocity-based jump physics shared by jump() and leftJump().
        • Parabolic arc via variable gravity (lighter rising, heavier falling).
        • Variable height: releasing Z early caps upward velocity at 3 px/frame.
        • Landing uses a frame-crossing check: did feet move from above to
          at/below a block's top surface this frame? Works at any fall speed.
        """
        # Count down drop-through immunity timer
        if self._drop_timer > 0:
            self._drop_timer -= 1

        # Variable jump height – cut ascent when Z is released early
        if self.jumpVelocity > 3.0 and not pygame.key.get_pressed()[pygame.K_z]:
            self.jumpVelocity = 3.0

        # Record feet position BEFORE moving so we can detect surface crossing
        prev_feet = self.y + 100

        # Move bear vertically (positive velocity = moving up)
        self.y -= int(round(self.jumpVelocity))

        # Gravity: gentler on the way up (floaty peak), stronger on the way down
        if self.jumpVelocity > 0:
            self.jumpVelocity -= 0.65   # decelerating rise
        else:
            self.jumpVelocity -= 0.85   # accelerating fall (snappier landing)

        self.comingUp = self.jumpVelocity > 0

        # Clear stale onPlatform flags every frame
        for block in blocks:
            block.setOnPlatform(False)

        bx2  = self.x + 100   # bear's right edge
        feet = self.y + 100   # bear's feet (after move)

        jumped_from_floor = (self.initialHeight == 300)

        def _land(block, bty):
            """Snap bear onto block and end the jump."""
            self.y = bty - 100
            block.setOnPlatform(True)
            for b in blocks:
                b.setDropStatus(False)
            self.setJumpStatus(False)
            self.setLeftJumpStatus(False)
            self.initialHeight = self.y
            self.sourceBlock = block
            self.jumpVelocity = 0.0
            self.trigger_land_squash()
            if self.thud_sound:
                self.thud_sound.play()
            if self.consume_jump_buffer():
                self.setJumpStatus(True)
                self.startJump()

        # ------------------------------------------------------------------ #
        # Platform landing – downstroke only.                                 #
        #                                                                     #
        # Primary check: did bear's feet cross a block's top surface this     #
        # frame?  prev_feet < bty means feet were above it; feet >= bty means #
        # they've reached or passed it.  No fixed window – works at any speed.#
        #                                                                     #
        # Secondary: isBoundaryPresent fallback for exact-pixel cases.        #
        # ------------------------------------------------------------------ #
        if self.jumpVelocity <= 0:

            if jumped_from_floor:
                # ---- Case 1: launched from the floor -------------------------
                for block in blocks:
                    bty = block.getBlockYPosition()
                    blx = block.getBlockXPosition()
                    brx = blx + block.getWidth()

                    # Guard: require at least one side strictly crossing so that
                    # the degenerate walk-off case (prev_feet == bty == feet)
                    # doesn't snap the bear back onto the block she just left.
                    if (prev_feet <= bty and feet >= bty
                            and (prev_feet < bty or feet > bty)
                            and bx2 > blx and self.x < brx):
                        _land(block, bty)
                        return

                # Secondary fallback - also check isBoundaryPresent for fall-off-ledge cases
                for block in blocks:
                    block.isBoundaryPresent(self.x, self.y)
                    if block.getOnPlatform():
                        bty = block.getBlockYPosition()
                        _land(block, bty)
                        return

            else:
                # ---- Case 2: launched from platform -------------------------
                # Allow landing on sourceBlock if it's a real jump (prev_feet < bty).
                # Only skip if it's a walk-off (prev_feet == bty == feet).
                for block in blocks:
                    bty = block.getBlockYPosition()
                    blx = block.getBlockXPosition()
                    brx = blx + block.getWidth()
                    
                    # Skip sourceBlock during a drop-through or walk-off
                    if block == self.sourceBlock and (self._drop_timer > 0 or (prev_feet == bty and feet == bty)):
                        continue

                    if (prev_feet <= bty and feet >= bty
                            and (prev_feet < bty or feet > bty)
                            and bx2 > blx and self.x < brx):
                        _land(block, bty)
                        return

                # Secondary fallback
                for block in blocks:
                    block.isBoundaryPresent(self.x, self.y)
                    if block.getOnPlatform():
                        if block == self.sourceBlock and self._drop_timer > 0:
                            continue
                        bty = block.getBlockYPosition()
                        _land(block, bty)
                        return

        # Continuous block check during fall – catch any block in path while falling
        if self.jumpVelocity <= 0 and (self.getJumpStatus() or self.getLeftJumpStatus()):
            bx2 = self.x + 100
            for block in blocks:
                if block == self.sourceBlock and self._drop_timer > 0:
                    continue
                bty = block.getBlockYPosition()
                blx = block.getBlockXPosition()
                brx = blx + block.getWidth()
                # If bear is falling and horizontally overlaps with block, and feet would pass through top
                if (bx2 > blx and self.x < brx and feet >= bty and feet <= bty + 20):
                    _land(block, bty)
                    return
        
        if self.y + 100 >= 400:
            self.y = 300
            self.setJumpStatus(False)
            self.setLeftJumpStatus(False)
            self.jumpVelocity = 0.0
            self.sourceBlock = None
            self.trigger_land_squash()
            if self.thud_sound:
                self.thud_sound.play()
            if self.consume_jump_buffer():
                self.setJumpStatus(True)
                self.startJump()

    def jump(self, blocks):
        """Right-facing jump (also handles neutral/vertical jump)."""
        if self.comingUp:
            sprite = (self.bearJumpingLeft1 if self.getLeftDirection()
                      else self.bearJumping1)
        else:
            sprite = (self.bearJumpingLeft2 if self.getLeftDirection()
                      else self.bearJumping2)
        self.screen.blit(sprite, (self.getXPosition(), self.y))
        self._jumpPhysics(blocks)

    def leftJump(self, blocks):
        """Left-facing jump – identical physics, reuses jump()."""
        self.jump(blocks)

    def is_bear_hurt(self, positionRelative, bearXPosition, bearYPosition,
                   objectXPosition, objectYPosition, objectName):
        return is_bear_hurt(positionRelative, bearXPosition, bearYPosition,
                          objectXPosition, objectYPosition, objectName)

    def boundaryExtraCheck(self):
        floorHeight = 400
        if self.getXPosition() <= 30:
            self.setXPosition(self.getXPosition() + STEP)
        if self.getYPosition() + 100 >= floorHeight:
            self.setYPosition(floorHeight - 100)   # snap flush to floor
            self.initialHeight = self.getYPosition()
            self.setJumpStatus(False)
            self.setLeftJumpStatus(False)
        if self.getXPosition() < 60:
            self.setXPosition(self.getXPosition() + 120)

    def setDisplayTimer(self, displayTimer):
        self.displayTimer = displayTimer

    def getDisplayTimer(self):
        return self.displayTimer

    def displayDamageOnBear(self, damage, source_name=None):
        render_damage_text(self.screen, _FONT_DAMAGE, damage,
                            self.getXPosition() + 60, self.getYPosition() - 60)
        if source_name == "spikes" and getattr(self, 'spike_hit_sound', None):
            self.spike_hit_sound.play()
        elif getattr(self, 'grunt_sound', None):
            self.grunt_sound.play()

    def displayBearHp(self):
        PX, PY, PW, PH = 8, 6, 218, 60
        hp = self.getHp()
        maxHp = self.getMaxHp()
        ratio = max(0.0, hp / maxHp)
        if ratio > 0.6:
            bar_color = (80, 210, 80)
        elif ratio > 0.25:
            bar_color = (230, 210, 50)
        else:
            bar_color = (220, 55, 55)
        render_hud_panel(self.screen, PX, PY, PW, PH, (190, 40, 40))
        render_hud_text_outlined(self.screen, _FONT_HUD_LABEL, "HP",
                           PX + 9, PY + 9, (255, 230, 50))
        render_hud_bar(self.screen, PX + 44, PY + 11, PW - 54, 18, ratio, bar_color)
        val = str(hp) + "/" + str(maxHp)
        render_hud_text_outlined(self.screen, _FONT_HUD_VAL, val,
                           PX + 44, PY + 34, (255, 255, 255))
        render_hud_text_outlined(self.screen, _FONT_HUD_VAL, "X:FIRE",
                           PX + 124, PY + 34, (255, 140, 30))

    def displayBearExp(self):
        self.levelUpCheck()
        EX, EY, EW, EH = 236, 6, 198, 60
        exp = self.getCurrentExp()
        maxExp = self.getMaxExp()
        ratio = max(0.0, min(1.0, exp / maxExp)) if maxExp > 0 else 0.0
        render_hud_panel(self.screen, EX, EY, EW, EH, (60, 100, 220))
        render_hud_text_outlined(self.screen, _FONT_HUD_LABEL, "EXP",
                           EX + 8, EY + 9, (120, 200, 255))
        render_hud_bar(self.screen, EX + 50, EY + 11, EW - 60, 18,
                 ratio, (255, 195, 30))
        val = str(exp) + "/" + str(maxExp)
        render_hud_text_outlined(self.screen, _FONT_HUD_VAL, val,
                           EX + 50, EY + 34, (255, 255, 255))
        LX, LY, LW, LH = 444, 6, 170, 60
        render_hud_panel(self.screen, LX, LY, LW, LH, (160, 60, 220))
        render_hud_text_outlined(self.screen, _FONT_HUD_VAL, "POWER LVL",
                           LX + 8, LY + 9, (200, 160, 255))
        lvl_surf = _FONT_HUD_LVL.render(str(self.level), True, (255, 230, 50))
        lvl_x = LX + (LW - lvl_surf.get_width()) // 2
        lvl_outline = _FONT_HUD_LVL.render(str(self.level), True, (0, 0, 0))
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            self.screen.blit(lvl_outline, (lvl_x + dx, LY + 28 + dy))
        self.screen.blit(lvl_surf, (lvl_x, LY + 28))

    def displayBearCoins(self):
        CX, CY, CW, CH = 8, 92, 280, 52
        render_hud_panel(self.screen, CX, CY, CW, CH, (200, 180, 80))
        pygame.draw.circle(self.screen, (255, 215, 0), (CX + 24, CY + 28), 12)
        pygame.draw.circle(self.screen, (255, 245, 130), (CX + 24, CY + 28), 6)
        render_hud_text_outlined(self.screen, _FONT_HUD, str(self.coins),
                           CX + 50, CY + 8, (255, 255, 160))
        extras = []
        if getattr(self, 'has_shield', False):
            extras.append('🛡')
        if getattr(self, 'has_aimer', False):
            extras.append('⚔')
        if getattr(self, 'has_50pct_protection', False):
            extras.append('✦')
        if extras:
            render_hud_text_outlined(self.screen, _FONT_HUD_VAL,
                               ' '.join(extras), CX + 8, CY + 30,
                               (200, 240, 200))

    def setMaxHp(self, maxHp):
        self.maxHp = maxHp

    def getMaxHp(self):
        return self.maxHp

    def setCurrentExp(self, exp):
        self.exp = exp

    def getCurrentExp(self):
        return self.exp

    def setCoins(self, coins):
        self.coins = max(0, coins)

    def getCoins(self):
        return self.coins

    def setHasShield(self, value):
        self.has_shield = bool(value)

    def hasShield(self):
        return getattr(self, 'has_shield', False)

    def setHasAimer(self, value):
        self.has_aimer = bool(value)

    def hasAimer(self):
        return getattr(self, 'has_aimer', False)

    def applyDamage(self, amount):
        if getattr(self, 'has_50pct_protection', False):
            amount = max(1, int(round(amount * 0.5)))
        elif getattr(self, 'has_shield', False):
            amount = max(1, int(round(amount * 0.8)))
        self.hp = max(0, self.hp - amount)
        return amount

    def setMaxExp(self, maxExp):
        self.maxExp = maxExp

    def getMaxExp(self):
        return self.maxExp

    def setAttack(self, attack):
        self.attack = attack

    def getAttack(self):
        return self.attack

    def setEndText(self, endText):
        self.endText = endText

    def getEndText(self):
        return self.endText

    def displayTextBox(self):
        if not self.getEndText():
            cur_line_text = (self.textArray[self.tupleIndex][self.line]
                             if self.line < len(self.textArray[self.tupleIndex]) else None)
            if (self.line != len(self.textArray[self.tupleIndex])
                    and (len(cur_line_text) == 0
                         or self.indexArray >= len(cur_line_text))):
                self.indexArray = 0
                self.line += 1
                if self.line == 1:
                    self.text2 = self.textArray[self.tupleIndex][self.line]
                elif self.line == 2:
                    self.text3 = self.textArray[self.tupleIndex][self.line]
            elif self.line == 0:
                self.text1 = self.textArray[self.tupleIndex][0]

            self.blinkTimer += 1
            _show_bear = False  # Remove bear face from popup
            popup_img = self.talkingNoBear
            self.screen.blit(popup_img, (0, 0))
            if self.blinkTimer > self.randomBlink:
                self.randomBlink = random.randint(100, 250)
                self.blinkTimer = 0

            self.textTimer += 1
            text1 = _FONT_POPUP.render(self.totalText1, False, (0, 0, 0))
            self.screen.blit(text1, (430, 125))
            text2 = _FONT_POPUP.render(self.totalText2, False, (0, 0, 0))
            self.screen.blit(text2, (430, 152))
            text3 = _FONT_POPUP.render(self.totalText3, False, (0, 0, 0))
            self.screen.blit(text3, (430, 179))
            self.xText += 5

            if self.textTimer % 3 < 2:
                if self.line == 0 and self.indexArray < len(self.text1):
                    self.totalText1 += self.text1[self.indexArray]
                    self.indexArray += 1
                elif self.line == 1 and self.indexArray < len(self.text2):
                    self.totalText2 += self.text2[self.indexArray]
                    self.indexArray += 1
                elif self.line == 2 and self.indexArray < len(self.text3):
                    self.totalText3 += self.text3[self.indexArray]
                    self.indexArray += 1

                for ev in pygame.event.get():
                    if ev.type == pygame.QUIT:
                        pygame.quit()
                        return
                    if ev.type == pygame.KEYDOWN and ev.key == pygame.K_s:
                        if self.tupleIndex + 1 == len(self.textArray):
                            self.setEndText(True)
                            self.tupleIndex = 0
                            self.textArray = []
                            self.clearArray()
                            self.indexArray = 0
                            self.totalText1 = ""
                            self.totalText2 = ""
                            self.totalText3 = ""
                            self.line = 0
                            self.setEndText(True)
                        else:
                            self.tupleIndex += 1
                            self.totalText1 = ""
                            self.totalText2 = ""
                            self.totalText3 = ""
                            self.line = 0
                            self.indexArray = 0

    def levelUpCheck(self):
        if self.maxExp <= self.exp:
            if hasattr(self, 'level_up_sound') and self.level_up_sound:
                self.level_up_sound.play()
            self.setEndText(False)
            self.level += 1
            self.maxExp += 20
            self.exp = 0
            self.maxHp += random.randint(5, 15)
            if self.hp < self.maxHp * 0.25:
                self.hp = min(self.maxHp, int(self.maxHp * 0.90))
            else:
                self.hp = min(self.maxHp, int(self.maxHp * 0.85))
            self.attack += random.randint(2, 5)
            self.damageAttack += random.randint(2, 5)
            self.fireballDamage = int(self.fireballDamage * 1.20) + 1
            self.textArray = []
            self.showBearArray = []
            self.textArray.append(['LEVEL UP!', '', 'Press "s" to continue'])
            self.showBearArray.append(False)
            self.textArray.append([
                'Max HP is now: ' + str(self.maxHp),
                'Attack is now: ' + str(self.damageAttack),
                'Press "s" to continue'
            ])
            self.showBearArray.append(False)
            if self.level % 2 == 0:
                self.textArray.append(['Firing is faster now!', '', 'Press "s" to continue'])
                self.showBearArray.append(False)
            if self.level == 14:
                self.textArray.append(['SILVER MODE ACTIVATED!', 'Speed increased by 50%!', 'Press "s" to continue'])
                self.showBearArray.append(False)
                self.textArray.append(['Firing rate MASSIVELY increased!', 'Rapid fire unlocked!', 'Press "s" to continue'])
                self.showBearArray.append(False)
            self.line = 0
            self.tupleIndex = 0
            self.indexArray = 0
            self.totalText1 = ""
            self.totalText2 = ""
            self.totalText3 = ""
            self.text1 = ""
            self.text2 = ""
            self.text3 = ""


# ---------------------------------------------------------------------------
class HealthPowerItem():
    def __init__(self, x, y, width, height, screen):
        self.damageAttack = 2
        self.hp = 100

    def setIsMonsterHurtAnimation(self, v):
        self.isMonsterHurtAnimation = v


# ---------------------------------------------------------------------------
class Door:
    def __init__(self, screen, xPosition):
        self.screen = screen
        self.x = xPosition
        self.door = pygame.image.load("Game/Images/door.png")
        self.door = pygame.transform.scale(self.door, (200, 550))
        self.isOpen = False

    def setXPosition(self, x):
        self.x = x

    def getXPosition(self):
        return self.x

    def getYPosition(self):
        return 250

    def setIsOpen(self, isOpen):
        self.isOpen = isOpen

    def getIsOpen(self):
        return self.isOpen

    def getName(self):
        return "door"

    def drawRectangle(self):
        self.screen.blit(self.door, (self.x, 0))


# ---------------------------------------------------------------------------
class KeyItem:
    def __init__(self, screen, xPosition, yPosition):
        self.screen = screen
        self.x = xPosition
        self.y = yPosition
        self.key = pygame.image.load("Game/Images/key.png")
        self.key = pygame.transform.scale(self.key, (50, 50))
        self.isOpen = False
        self.initialHeight = yPosition

    def setXPosition(self, x):
        self.x = x

    def getXPosition(self):
        return self.x

    def setYPosition(self, y):
        self.y = y

    def getYPosition(self):
        return self.y

    def setIsOpen(self, isOpen):
        self.isOpen = isOpen

    def getIsOpen(self):
        return self.isOpen

    def drawKey(self):
        self.screen.blit(self.key, (self.x, self.y))

    def isKeyGrabbed(self, bearXPosition, bearYPosition, objectXPosition, objectYPosition):
        bear_rect = pygame.Rect(bearXPosition + 5, bearYPosition + 5,
                                BEAR_W - 10, BEAR_H - 10)
        key_rect  = pygame.Rect(objectXPosition, objectYPosition, 60, 100)
        if bear_rect.colliderect(key_rect):
            self.isOpen = True
            return True
        return False

    def boundaryExtraCheck(self):
        if self.getYPosition() + 50 < 400:
            self.setYPosition(self.getYPosition() + JUMP_STEP)


# ---------------------------------------------------------------------------
class SpikeBlock():
    def __init__(self, x, y, screen):
        self.x = x
        self.y = y
        self.screen = screen
        self.stunned = False
        self.health = 1
        self.damageAttack = random.randint(13, 26)
        self.spike = pygame.image.load("Game/Images/spikes.png")
        self.spike = pygame.transform.scale(self.spike, (100, 60))
        self.isHurtAnimationStarted = False
        self.isHurtTimer = 0

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer

    def getHurtTimer(self):
        return self.isHurtTimer

    def setIsHurtAnimationStarted(self, v):
        self.isHurtAnimationStarted = v

    def getIsHurtAnimationStarted(self):
        return self.isHurtAnimationStarted

    def setDamageAttack(self, v):
        self.damageAttack = v

    def getDamageAttack(self):
        return self.damageAttack // 2

    def setXPosition(self, x):
        self.x = x

    def getXPosition(self):
        return self.x

    def setYPosition(self, y):
        self.y = y

    def getYPosition(self):
        return self.y

    def getName(self):
        return "spikes"

    def setStunned(self, stunned):
        self.stunned = stunned

    def getStunned(self):
        return self.stunned

    def setHealth(self, health):
        self.health = health

    def getHealth(self):
        return self.health

    def draw(self):
        for i in range(6):
            self.screen.blit(self.spike, (self.x + i * 100, self.y))


# ---------------------------------------------------------------------------
class ShadowShaman():
    @staticmethod
    def _build_shaman_sprite(w, h, hurt=False):
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2

        robe_col = (140, 40, 40) if hurt else (30, 10, 50)
        robe_hi  = (180, 60, 60) if hurt else (50, 20, 80)
        pygame.draw.ellipse(surf, robe_col, (cx - 30, cy + 5, 60, 55))
        pygame.draw.polygon(surf, robe_col, [
            (cx - 35, cy + 10), (cx + 35, cy + 10),
            (cx + 45, h - 5), (cx - 45, h - 5)])
        for i in range(3):
            _fy = cy + 25 + i * 14
            pygame.draw.arc(surf, robe_hi,
                            (cx - 38 + i * 3, _fy, 76 - i * 6, 10), 0, 3.14, 2)

        hood_col = (20, 8, 40) if not hurt else (120, 30, 30)
        pygame.draw.ellipse(surf, hood_col, (cx - 28, cy - 30, 56, 50))
        pygame.draw.polygon(surf, hood_col, [
            (cx, cy - 45), (cx - 18, cy - 25), (cx + 18, cy - 25)])

        skull_col = (200, 200, 180) if not hurt else (255, 180, 180)
        pygame.draw.ellipse(surf, skull_col, (cx - 18, cy - 22, 36, 32))

        eye_glow = (0, 255, 100) if not hurt else (255, 80, 80)
        eye_core = (180, 255, 200) if not hurt else (255, 200, 200)
        for ex in [cx - 8, cx + 8]:
            pygame.draw.circle(surf, eye_glow, (ex, cy - 10), 5)
            pygame.draw.circle(surf, eye_core, (ex, cy - 10), 2)

        pygame.draw.polygon(surf, (40, 40, 40), [
            (cx - 3, cy - 2), (cx + 3, cy - 2), (cx, cy + 2)])
        pygame.draw.line(surf, (60, 20, 20), (cx - 8, cy + 6), (cx + 8, cy + 6), 2)

        staff_col = (80, 50, 20)
        sx = cx + 30
        pygame.draw.line(surf, staff_col, (sx, cy - 20), (sx, h - 5), 3)
        pygame.draw.line(surf, (60, 35, 10), (sx - 1, cy - 20), (sx - 1, h - 5), 1)
        orb_col = (100, 0, 200) if not hurt else (255, 60, 60)
        orb_glow = (160, 80, 255) if not hurt else (255, 150, 150)
        pygame.draw.circle(surf, orb_glow, (sx, cy - 25), 10)
        pygame.draw.circle(surf, orb_col, (sx, cy - 25), 7)
        pygame.draw.circle(surf, (255, 255, 255), (sx - 2, cy - 28), 2)

        _mist = pygame.Surface((w, h), pygame.SRCALPHA)
        for _ in range(6):
            _mx = cx + random.randint(-35, 35)
            _my = random.randint(h - 25, h - 5)
            _mr = random.randint(8, 18)
            _ma = random.randint(30, 70)
            mc = (80, 40, 120, _ma) if not hurt else (200, 80, 80, _ma)
            pygame.draw.circle(_mist, mc, (_mx, _my), _mr)
        surf.blit(_mist, (0, 0))

        return surf

    def __init__(self, x, y, witch1Image, witch2Image, screen):
        _w, _h = 120, 120
        self.witch  = ShadowShaman._build_shaman_sprite(_w, _h, hurt=False)
        self.witch2 = ShadowShaman._build_shaman_sprite(_w, _h, hurt=False)
        self.hurtWitch = ShadowShaman._build_shaman_sprite(_w, _h, hurt=True)
        self.directionX = -1 * random.randint(1, 2)
        self.x = x
        self.y = y
        self.destructionAnimation = 0
        self.stunned = 0
        self.screen = screen
        self.rand = random.choice([1, 1, 2])
        self.health = int(random.randint(40, 60) * 1.20)
        self.max_health = self.health
        self._defense = random.randint(1, 10) / 100.0
        self.fire = pygame.image.load("Game/Images/fire2.png")
        self.fire = pygame.transform.scale(self.fire, (60, 60))
        self.changeDirectionX = random.randint(200, 400)
        self.changeDirectionY = random.randint(60, 100)
        self.storeDirection = 1
        self.directionY = 1
        self.setThrowsFireBall = False
        self.fireBallAnimationCounter = 0
        self.damageAttack = 13
        self.hp = 120
        self.isMonsterHurtAnimation = 0
        self.damageReceived = 0
        self.exp = 100
        self.isHurtAnimationStarted = False
        self.isHurtTimer = 0
        self._bear_x = 400
        self._bear_y = 300
        self._preferred_dist = random.randint(150, 280)
        self._strafe_timer = random.randint(0, 60)
        self._sep_offset = 0.0
        self.startDestructionAnimation = False

    def setStartDestructionAnimation(self, v):
        self.startDestructionAnimation = v

    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer

    def updateHurtTimer(self):
        if self.isHurtTimer > 0:
            self.isHurtTimer -= 1

    def getHurtTimer(self):
        return self.isHurtTimer

    def takeDamage(self, damage):
        self.health -= damage
        self.isHurtAnimationStarted = True
        self.isHurtTimer = 30

    def setHealth(self, health):
        self.health = health

    def getHealth(self):
        return self.health

    def getExp(self):
        return self.exp

    def getXPosition(self):
        return self.x

    def getYPosition(self):
        return self.y

    def setXPosition(self, x):
        self.x = x

    def setYPosition(self, y):
        self.y = y

    def getDestructionAnimationCount(self):
        return self.destructionAnimation

    def getName(self):
        return "shadowShaman"

    def getDamageAttack(self):
        return self.damageAttack

    def setDamageReceived(self, damage):
        self.damageReceived = damage

    def getDamageReceived(self):
        return self.damageReceived

    def displayDamageOnMonster(self, damage):
        stunned_val = getattr(self, 'stunned', 1)
        try:
            s = int(stunned_val)
        except Exception:
            s = 1
        fade_frames = 8
        alpha = int(255 * min(max(0, s), fade_frames) / float(fade_frames))
        render_damage_text(self.screen, _FONT_DAMAGE, damage,
                            self.getXPosition() + 60, self.getYPosition() - 60,
                            alpha=alpha)

    def setStunned(self, value):
        self.stunned = value

    def drawMonster(self):
        if getattr(self, '_popup_frozen', False):
            self.screen.blit(self.witch, (self.x, self.y))
            if self.health < self.max_health:
                render_enemy_health_bar(self.screen, self.x, self.y - 15, self.health, self.max_health)
            return

        if self.stunned == 0:
            self._strafe_timer += 1
            _dx = self._bear_x - self.x
            _dy_b = self._bear_y - self.y
            _dist = abs(_dx)
            if _dist < self._preferred_dist - 30:
                _mx = -1 if _dx > 0 else 1
            elif _dist > self._preferred_dist + 30:
                _mx = 1 if _dx > 0 else -1
            else:
                _mx = 1 if self._strafe_timer % 100 < 50 else -1
            _my = -1 if self.y > 80 and _dy_b < -30 else (1 if self.y < 300 and _dy_b > 30 else 0)
            self.x += _mx * self.rand + self._sep_offset
            self._sep_offset *= 0.9
            self.y += _my * self.rand
            self.x = max(-50, min(860, self.x))
            self.y = max(30, min(350, self.y))
        elif self.stunned > 0:
            self.stunned += 1
            if self.stunned >= 20:
                self.stunned = 0
        self.screen.blit(self.witch, (self.x, self.y))
        if self.health < self.max_health:
            render_enemy_health_bar(self.screen, self.x, self.y - 15, self.health, self.max_health)

    def drawDestruction(self, damage):
        self.destructionAnimation += 1
        self.screen.blit(self.witch2, (self.x, self.y))

    def draw(self):
        self.screen.blit(self.witch, (self.x, self.y))


# ---------------------------------------------------------------------------
class Waterfall():
    def __init__(self, x, y, width, height, screen):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.screen = screen
        self.particles = []
        self.spawn_rate = 2
        self.frame = 0
        for _ in range(20):
            self._spawn_particle()
    
    def _spawn_particle(self):
        px = self.x + random.randint(0, self.width)
        py = self.y
        vy = random.uniform(1.5, 3.5)
        self.particles.append({'x': px, 'y': py, 'vy': vy, 'life': 255})
    
    def draw(self):
        self.frame += 1
        if self.frame % self.spawn_rate == 0:
            for _ in range(2):
                self._spawn_particle()
        
        to_remove = []
        for p in self.particles:
            p['y'] += p['vy']
            p['life'] = max(0, p['life'] - 8)
            
            if p['y'] > self.y + self.height or p['life'] <= 0:
                to_remove.append(p)
            else:
                alpha = int(p['life'])
                s = pygame.Surface((4, 8), pygame.SRCALPHA)
                pygame.draw.line(s, (100, 180, 255, alpha), (2, 0), (2, 8), 2)
                self.screen.blit(s, (int(p['x']), int(p['y'])))
        
        for p in to_remove:
            self.particles.remove(p)


# ---------------------------------------------------------------------------
class Laser():
    def __init__(self, start_x, end_x, y, screen):
        self.x = start_x
        self.y = y
        self.screen = screen
        self.vx = -6 if end_x < start_x else 6
        self.lifetime = 0
        self.max_lifetime = 120
        self.width = 40
        self.height = 12

    def draw(self):
        if self.lifetime < self.max_lifetime:
            self.lifetime += 1
            self.x += self.vx
            _alpha = max(80, int(255 * (1 - self.lifetime / self.max_lifetime)))

            _glow = pygame.Surface((self.width + 16, self.height + 16), pygame.SRCALPHA)
            pygame.draw.ellipse(_glow, (100, 255, 100, min(120, _alpha)), (0, 0, self.width + 16, self.height + 16))
            self.screen.blit(_glow, (self.x - 8, self.y - 8))

            _core = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.ellipse(_core, (180, 255, 80, _alpha), (0, 0, self.width, self.height))
            pygame.draw.ellipse(_core, (255, 255, 200, _alpha), (8, 2, self.width - 16, self.height - 4))
            self.screen.blit(_core, (self.x, self.y))

            _trail = pygame.Surface((20, 6), pygame.SRCALPHA)
            _trail.fill((100, 200, 50, max(30, _alpha // 3)))
            self.screen.blit(_trail, (self.x - self.vx * 2, self.y + 3))

            if self.x < -60 or self.x > 960:
                return False
            return True
        return False

    def draw_frozen(self):
        _alpha = max(80, int(255 * (1 - self.lifetime / self.max_lifetime)))
        _glow = pygame.Surface((self.width + 16, self.height + 16), pygame.SRCALPHA)
        pygame.draw.ellipse(_glow, (100, 255, 100, min(120, _alpha)), (0, 0, self.width + 16, self.height + 16))
        self.screen.blit(_glow, (self.x - 8, self.y - 8))
        _core = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.ellipse(_core, (180, 255, 80, _alpha), (0, 0, self.width, self.height))
        self.screen.blit(_core, (self.x, self.y))

    def getYPosition(self):
        return self.y

    def getStartX(self):
        return self.x

    def getEndX(self):
        return self.x + self.width

    def setXPosition(self, x):
        self.x = x

    def getXPosition(self):
        return self.x

    def isActive(self):
        return self.lifetime < self.max_lifetime


class MiniFrankenBear():
    _shared_sprites = None

    @classmethod
    def _load_sprites(cls):
        if cls._shared_sprites is not None:
            return
        _size = (80, 80)

        def _draw_mini_bear(surf, body_col, eye_col, bolt_col):
            _dark = tuple(max(0, c - 30) for c in body_col)
            pygame.draw.ellipse(surf, body_col, (15, 25, 50, 50))
            pygame.draw.ellipse(surf, _dark, (15, 25, 50, 50), 2)
            pygame.draw.circle(surf, body_col, (40, 22), 20)
            pygame.draw.circle(surf, _dark, (40, 22), 20, 2)
            pygame.draw.circle(surf, body_col, (25, 8), 10)
            pygame.draw.circle(surf, _dark, (25, 8), 10, 2)
            pygame.draw.circle(surf, body_col, (55, 8), 10)
            pygame.draw.circle(surf, _dark, (55, 8), 10, 2)
            pygame.draw.circle(surf, (20, 20, 20), (25, 8), 4)
            pygame.draw.circle(surf, (20, 20, 20), (55, 8), 4)
            pygame.draw.circle(surf, eye_col, (33, 18), 5)
            pygame.draw.circle(surf, eye_col, (47, 18), 5)
            pygame.draw.circle(surf, (220, 220, 0), (33, 18), 3)
            pygame.draw.circle(surf, (220, 220, 0), (47, 18), 3)
            pygame.draw.circle(surf, (255, 50, 50), (33, 18), 1)
            pygame.draw.circle(surf, (255, 50, 50), (47, 18), 1)
            pygame.draw.line(surf, (40, 40, 40), (34, 28), (46, 28), 2)
            for _tx in [34, 36, 38, 40, 42, 44]:
                pygame.draw.line(surf, (40, 40, 40), (_tx, 27), (_tx, 29), 1)
            pygame.draw.ellipse(surf, (80, 60, 50), (35, 30, 10, 6))
            pygame.draw.circle(surf, bolt_col, (10, 22), 6)
            pygame.draw.circle(surf, bolt_col, (70, 22), 6)
            pygame.draw.rect(surf, bolt_col, (6, 17, 8, 10))
            pygame.draw.rect(surf, bolt_col, (66, 17, 8, 10))
            pygame.draw.circle(surf, (200, 200, 200), (10, 22), 3)
            pygame.draw.circle(surf, (200, 200, 200), (70, 22), 3)
            pygame.draw.line(surf, (30, 30, 30), (28, 10), (28, 34), 2)
            pygame.draw.line(surf, (30, 30, 30), (52, 10), (52, 34), 2)
            pygame.draw.line(surf, (30, 30, 30), (23, 40), (57, 40), 2)
            for _sx in [28, 35, 42, 49]:
                pygame.draw.line(surf, (30, 30, 30), (_sx, 43), (_sx + 4, 50), 2)
                pygame.draw.line(surf, (30, 30, 30), (_sx + 4, 50), (_sx + 8, 43), 2)
            pygame.draw.line(surf, (60, 60, 60), (20, 20), (25, 35), 2)
            pygame.draw.line(surf, (60, 60, 60), (55, 20), (60, 35), 2)
            pygame.draw.ellipse(surf, body_col, (10, 55, 18, 22))
            pygame.draw.ellipse(surf, _dark, (10, 55, 18, 22), 2)
            pygame.draw.ellipse(surf, body_col, (52, 55, 18, 22))
            pygame.draw.ellipse(surf, _dark, (52, 55, 18, 22), 2)
            pygame.draw.ellipse(surf, _dark, (12, 68, 14, 8))
            pygame.draw.ellipse(surf, _dark, (54, 68, 14, 8))
            pygame.draw.ellipse(surf, body_col, (18, 38, 12, 18))
            pygame.draw.ellipse(surf, body_col, (50, 38, 12, 18))
            pygame.draw.circle(surf, _dark, (20, 52), 3)
            pygame.draw.circle(surf, _dark, (22, 52), 3)
            pygame.draw.circle(surf, _dark, (54, 52), 3)
            pygame.draw.circle(surf, _dark, (56, 52), 3)

        _normal = pygame.Surface(_size, pygame.SRCALPHA)
        _draw_mini_bear(_normal, (50, 140, 50), (20, 20, 20), (160, 160, 160))

        _hurt = pygame.Surface(_size, pygame.SRCALPHA)
        _draw_mini_bear(_hurt, (180, 60, 60), (40, 10, 10), (200, 160, 160))

        cls._shared_sprites = {
            "normal": _normal,
            "hurt": _hurt,
            "flipped": pygame.transform.flip(_normal, True, False),
            "hurt_flip": pygame.transform.flip(_hurt, True, False),
        }

    def __init__(self, x, y, screen):
        MiniFrankenBear._load_sprites()
        self.x = x
        self.y = y
        self.screen = screen
        self.health = int(45 * 1.20)
        self.max_health = self.health
        self._defense = random.randint(1, 10) / 100.0
        self.direction = -1 if random.random() > 0.5 else 1
        self.walk_speed = random.choice([2, 3, 3, 4])
        self.walk_timer = 0
        self.change_direction_timer = random.randint(80, 150)
        self.laser_timer = random.randint(0, 30)
        self.laser_interval = random.randint(40, 80)
        self.destructionAnimation = 0
        self.stunned = 0
        self.damageAttack = 11
        self.damageReceived = 0
        self.exp = 35
        self.isHurtAnimationStarted = False
        self.isHurtTimer = 0
        self.startDestructionAnimation = False
        self.has_thrown_laser = False
        self._bear_x = 400
        self._bear_y = 300
        self._sep_offset = 0.0
        self._chase_range = random.randint(250, 450)
        self._personality = random.choice(['aggressive', 'cautious', 'flanker'])
        self._preferred_gap = random.randint(40, 100)
        self._turn_timer_scale = random.uniform(0.7, 1.5)
        
    def walk(self):
        _dx = self._bear_x - self.x
        _dist = abs(_dx)
        if _dist < self._chase_range and _dist > 20:
            if self._personality == 'cautious' and _dist < self._preferred_gap:
                _want_dir = -1 if _dx > 0 else 1
            elif self._personality == 'flanker' and _dist < 80:
                _want_dir = 1 if id(self) % 2 == 0 else -1
            else:
                _want_dir = 1 if _dx > 0 else -1
            if _want_dir != self.direction:
                self.direction = _want_dir
            _spd = self.walk_speed + (1 if _dist < 120 else 0)
        else:
            _spd = self.walk_speed
        self.x += self.direction * _spd + self._sep_offset
        self._sep_offset *= 0.9
        self.walk_timer += 1
        if self.walk_timer > self.change_direction_timer and _dist >= 350:
            self.direction *= -1
            self.walk_timer = 0
            _base_timer = random.randint(80, 150)
            _scale = getattr(self, '_turn_timer_scale', 1.0)
            self.change_direction_timer = int(_base_timer * _scale)
    
    def update_laser_timer(self):
        self.laser_timer += 1
    
    def should_throw_laser(self):
        return self.laser_timer >= self.laser_interval and not self.has_thrown_laser
    
    def throw_laser(self, bear_x=None):
        self.has_thrown_laser = True
        self.laser_timer = 0
        self.laser_interval = random.randint(60, 100)
        _cx = self.x + 40
        if bear_x is not None:
            _end = bear_x if bear_x < _cx else bear_x + 100
        else:
            _end = _cx - 300 if self.direction < 0 else _cx + 300
        _laser = Laser(_cx, _end, self.y + 10, self.screen)
        _laser._owner = self
        return _laser
    
    def draw(self):
        sp = MiniFrankenBear._shared_sprites
        if self.isHurtTimer > 0:
            img = sp["hurt_flip"] if self.direction < 0 else sp["hurt"]
        else:
            img = sp["flipped"] if self.direction < 0 else sp["normal"]
        self.screen.blit(img, (self.x, self.y))

    def drawMonster(self):
        if getattr(self, '_popup_frozen', False):
            self.draw()
            if self.health < self.max_health:
                render_enemy_health_bar(self.screen, self.x, self.y - 10, self.health, self.max_health)
            return

        if self.stunned == 0:
            self.walk()
        elif self.stunned > 0:
            self.stunned += 1
            if self.stunned >= 20:
                self.stunned = 0
                self.damageReceived = 0
        self.update_laser_timer()
        self.draw()
        if self.health < self.max_health:
            render_enemy_health_bar(self.screen, self.x, self.y - 10, self.health, self.max_health)

    def drawDestruction(self, damage):
        self.destructionAnimation += 1
        alpha = max(0, int(255 * (1 - self.destructionAnimation / 30)))
        sp = MiniFrankenBear._shared_sprites
        img = sp["normal"].copy()
        img.set_alpha(alpha)
        self.screen.blit(img, (self.x, self.y))
    
    def getHealth(self):
        return self.health
    
    def setHealth(self, health):
        self.health = health
    
    def getXPosition(self):
        return self.x
    
    def getYPosition(self):
        return self.y
    
    def setXPosition(self, x):
        self.x = x
    
    def setYPosition(self, y):
        self.y = y
    
    def getDestructionAnimationCount(self):
        return self.destructionAnimation
    
    def getName(self):
        return "miniFrankenBear"
    
    def getDamageAttack(self):
        return self.damageAttack
    
    def getExp(self):
        return self.exp
    
    def setDamageReceived(self, damage):
        self.damageReceived = damage

    def getDamageReceived(self):
        return self.damageReceived

    def displayDamageOnMonster(self, damage):
        stunned_val = getattr(self, 'stunned', 1)
        try:
            s = int(stunned_val)
        except Exception:
            s = 1
        fade_frames = 8
        alpha = int(255 * min(max(0, s), fade_frames) / float(fade_frames))
        render_damage_text(self.screen, _FONT_DAMAGE, damage,
                            self.x + 40, self.y - 40,
                            alpha=alpha)

    def setStunned(self, value):
        self.stunned = value

    def setStartDestructionAnimation(self, v):
        self.startDestructionAnimation = v
    
    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation
    
    def setHurtTimer(self, timer):
        self.isHurtTimer = timer
    
    def getHurtTimer(self):
        return self.isHurtTimer


# ---------------------------------------------------------------------------
class FrankenBear():
    def __init__(self, x, y, screen):
        self.destructionAnimation = 0
        self.x = x
        self.y = y
        self.screen = screen
        self.stunned = False
        self.health = int(1000 * 1.20)
        self.max_health = self.health
        self._defense = random.randint(1, 10) / 100.0
        self.startDestructionAnimation = False
        self.boss1 = pygame.image.load("Game/Images/boss1.png")
        self.boss1 = pygame.transform.scale(self.boss1, (300, 300))
        self.boss2 = pygame.image.load("Game/Images/boss2.png")
        self.boss2 = pygame.transform.scale(self.boss2, (300, 300))
        self.boss3 = pygame.image.load("Game/Images/boss3.png")
        self.boss3 = pygame.transform.scale(self.boss3, (300, 300))
        self.exp = 0
        self.boss3Flipped = pygame.transform.flip(self.boss3, True, False)
        self.flipped = random.randint(1, 2)
        self.isHurtAnimationStarted = False
        self.isHurtTimer = 0
        self.blinkTimer = 0
        self.attackTimer = 0
        self.randomBlink = random.randint(50, 150)
        self.randomAttack = random.randint(60, 100)
        self.bossDisplay = self.boss3
        self.blinked = False
        self.attacked = False
        self.throwFireBallLeft = False
        self.throwFireBallRight = False
        self.damageAttack = 20
        self.damageReceived = 0
        self.fire = pygame.image.load("Game/Images/fire2.png")
        self.fire = pygame.transform.scale(self.fire, (100, 100))

    def getDamageReceived(self):
        return self.damageReceived

    def setDamageReceived(self, v):
        self.damageReceived = v

    def setThrowFireBallLeft(self, v):
        self.throwFireBallLeft = v

    def getThrowFireBallLeft(self):
        return self.throwFireBallLeft

    def setThrowFireBallRight(self, v):
        self.throwFireBallRight = v

    def getThrowFireBallRight(self):
        return self.throwFireBallRight

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer

    def getHurtTimer(self):
        return self.isHurtTimer

    def setIsHurtAnimationStarted(self, v):
        self.isHurtAnimationStarted = v

    def getIsHurtAnimationStarted(self):
        return self.isHurtAnimationStarted

    def setDamageAttack(self, v):
        self.damageAttack = v

    def getDamageAttack(self):
        return self.damageAttack

    def setXPosition(self, x):
        self.x = x

    def getXPosition(self):
        return self.x

    def setYPosition(self, y):
        self.y = y

    def getYPosition(self):
        return self.y

    def getName(self):
        return "frankenbears"

    def setStunned(self, stunned):
        self.stunned = stunned

    def getStunned(self):
        return self.stunned

    def setHealth(self, health):
        self.health = health

    def getHealth(self):
        return self.health

    def displayDamageOnMonster(self, damage):
        stunned_val = getattr(self, 'stunned', 1)
        try:
            s = int(stunned_val)
        except Exception:
            s = 1
        fade_frames = 12
        alpha = int(255 * min(max(0, s), fade_frames) / float(fade_frames))
        render_damage_text(self.screen, _FONT_BOSS_DAMAGE, damage,
                            int(self.x) + 120, int(self.y) - 30,
                            alpha=alpha)

    def _draw_boss_details(self):
        _bx, _by = int(self.x), int(self.y)
        pygame.draw.circle(self.screen, (160, 160, 160), (_bx + 70, _by + 100), 14)
        pygame.draw.circle(self.screen, (160, 160, 160), (_bx + 230, _by + 100), 14)
        pygame.draw.rect(self.screen, (140, 140, 140), (_bx + 64, _by + 90, 12, 20))
        pygame.draw.rect(self.screen, (140, 140, 140), (_bx + 224, _by + 90, 12, 20))
        pygame.draw.line(self.screen, (50, 50, 50), (_bx + 110, _by + 60), (_bx + 110, _by + 170), 3)
        pygame.draw.line(self.screen, (50, 50, 50), (_bx + 190, _by + 60), (_bx + 190, _by + 170), 3)
        pygame.draw.line(self.screen, (50, 50, 50), (_bx + 100, _by + 110), (_bx + 200, _by + 110), 3)
        for _sx in [120, 140, 160, 180]:
            pygame.draw.line(self.screen, (40, 40, 40), (_bx + _sx, _by + 175), (_bx + _sx + 8, _by + 195), 2)
            pygame.draw.line(self.screen, (40, 40, 40), (_bx + _sx + 8, _by + 195), (_bx + _sx + 16, _by + 175), 2)
        _pulse = abs((pygame.time.get_ticks() // 100) % 20 - 10)
        _eye_glow = min(255, 180 + _pulse * 7)
        if self.health <= 3:
            _eye_col = (_eye_glow, 50, 50)
        else:
            _eye_col = (_eye_glow, _eye_glow, 50)
        pygame.draw.circle(self.screen, _eye_col, (_bx + 130, _by + 140), 6)
        pygame.draw.circle(self.screen, _eye_col, (_bx + 170, _by + 140), 6)

    def drawMonster(self):
        if getattr(self, '_popup_frozen', False):
            _bx = int(self.x)
            _by = int(self.y)
            self.screen.blit(self.boss1, (_bx, _by))
            self._draw_boss_details()
            if self.health < self.max_health:
                render_enemy_health_bar(self.screen, _bx + 40, _by + 280, self.health, self.max_health, w=160, h=14)
            return

        self.blinkTimer += 1
        self.attackTimer += 1

        if self.x > 300:
            self.x -= 3

        _bx = int(self.x)
        _by = int(self.y)

        if (self.blinkTimer < self.randomBlink
                and self.attackTimer < self.randomAttack):
            self.screen.blit(self.boss1, (_bx, _by))
        elif (self.blinkTimer >= self.randomBlink
              and self.blinkTimer <= self.randomBlink + 10
              and not self.attacked):
            self.screen.blit(self.boss2, (_bx, _by))
            self.bossDisplay = self.boss2
            self.blinked = True
        elif (self.attackTimer >= self.randomAttack
              and self.attackTimer <= self.randomAttack + 30):
            self.screen.blit(self.bossDisplay, (_bx, _by))
            self.attacked = True
        else:
            if self.blinked:
                self.randomBlink = random.randint(50, 150)
                self.blinked = False
                self.blinkTimer = 0
            if self.attacked:
                if self.health <= 3:
                    self.randomAttack = random.randint(60, 100)
                else:
                    self.randomAttack = random.randint(90, 140)
                self.attackTimer = 0
                self.blinkTimer = 0
                self.flipped = random.randint(1, 2)
                if self.flipped == 1:
                    self.bossDisplay = self.boss3
                    self.setThrowFireBallLeft(True)
                else:
                    self.bossDisplay = self.boss3Flipped
                    self.setThrowFireBallRight(True)
                self.attacked = False
            self.screen.blit(self.boss1, (_bx, _by))

        self._draw_boss_details()

        if self.stunned > 0:
            self.stunned += 1
            self.displayDamageOnMonster(self.damageReceived)
            if self.stunned == 20:
                self.stunned = 0

        if self.health < self.max_health:
            render_enemy_health_bar(self.screen, int(self.x) + 40, int(self.y) + 280, self.health, self.max_health, w=160, h=14)

    def setStartDestructionAnimation(self, v):
        self.startDestructionAnimation = v

    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation

    def drawDestruction(self, damage):
        self.displayDamageOnMonster(damage)
        self.destructionAnimation += 1
        if self.destructionAnimation < 70 and self.destructionAnimation % 2 == 0:
            _num_fires = 3 if self.destructionAnimation < 30 else 2
            for _ in range(_num_fires):
                self.screen.blit(self.fire,
                                 (self.x + random.randint(-300, 50),
                                  self.y + random.randint(-300, 50)))

    def getDestructionAnimationCount(self):
        return self.destructionAnimation

    def getExp(self):
        return self.exp
# Temporary file with new classes - will be appended to mainGame.py

class Snake:
    """Snake enemy that poisons the player on contact."""

    FLOOR_Y = 400

    def __init__(self, x, y, screen):
        """Initialize a snake at position (x, y)."""
        self.x = x
        self.screen = screen
        self.direction = -1 if random.random() > 0.5 else 1
        self.width = 220
        self.height = 100
        self.y = self.FLOOR_Y - self.height
        self.health = int(15 * 1.80)
        self.max_health = self.health
        self._defense = random.randint(1, 10) / 100.0
        self.speed = random.choice([1, 1, 2, 2])
        self.stunned = 0
        self.damageReceived = 0
        self.exp = 8
        self.damageAttack = 0
        self.isHurtTimer = 0
        self.destructionAnimation = 0
        self._anim_timer = 0
        self._bear_x = 400
        self._bear_y = 300
        self._sep_offset = 0.0
        self._chase_range = random.randint(200, 400)
        self._personality = random.choice(['aggressive', 'cautious', 'flanker'])
        self._preferred_gap = random.randint(60, 140)

        try:
            _base = pygame.image.load("Game/Images/snake.png").convert_alpha()
            _base = pygame.transform.scale(_base, (self.width, self.height))
        except (FileNotFoundError, Exception):
            _base = self._draw_procedural_snake()

        _ex = int(self.width * 0.72)
        _ey = int(self.height * 0.18)
        pygame.draw.circle(_base, (255, 255, 50), (_ex, _ey), 6)
        pygame.draw.circle(_base, (200, 200, 0), (_ex, _ey), 6, 1)
        pygame.draw.ellipse(_base, (20, 20, 20), (_ex - 2, _ey - 5, 4, 10))
        pygame.draw.circle(_base, (255, 255, 200), (_ex - 2, _ey - 2), 2)

        self._frame1_right = _base
        self._frame1_left = pygame.transform.flip(_base, True, False)
        _f2 = pygame.transform.rotate(_base, 4)
        _f2w, _f2h = _f2.get_size()
        _f2_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        _f2_surf.blit(_f2, ((self.width - _f2w) // 2, (self.height - _f2h) // 2))
        self._frame2_right = _f2_surf
        self._frame2_left = pygame.transform.flip(_f2_surf, True, False)
        self.snake_img = _base
        self.snake_img_left = self._frame1_left

        self.poison_cooldown = 0
        self.walk_timer = 0
        self.change_direction_timer = random.randint(100, 200)
        self.startDestructionAnimation = False
        self._venom_timer = 0
        self._venom_interval = random.randint(90, 160)
        self._venom_spit_anim = 0

    def _draw_procedural_snake(self):
        _sw, _sh = self.width, self.height
        surf = pygame.Surface((_sw, _sh), pygame.SRCALPHA)
        _DARK   = (18, 72, 28)
        _MID    = (38, 120, 50)
        _LIGHT  = (68, 185, 80)
        _PAT    = (195, 165, 12)
        _PAT2   = (130, 105, 5)
        _HCOL   = (25, 88, 38)
        _EYE    = (215, 25, 12)
        _PUPIL  = (8, 4, 4)
        _FANG   = (242, 242, 252)
        _TONGUE = (210, 18, 28)
        _BELLY  = (58, 150, 65)
        _by = _sh - 30
        _segs = [
            (12,  _by, 14),
            (34,  _by - 5, 15),
            (58,  _by - 12, 16),
            (82,  _by - 20, 17),
            (106, _by - 24, 18),
            (130, _by - 20, 17),
            (152, _by - 14, 16),
            (174, _by - 8, 15),
            (194, _by - 3, 14),
        ]
        for _cx, _cy, _r in _segs:
            pygame.draw.circle(surf, _DARK, (_cx + 2, _cy + 3), _r)
        for _cx, _cy, _r in _segs:
            pygame.draw.circle(surf, _MID, (_cx, _cy), _r)
            pygame.draw.circle(surf, _BELLY, (_cx, _cy + 4), max(3, _r - 4))
            pygame.draw.circle(surf, _LIGHT, (_cx - 3, _cy - 4), max(2, _r // 3))
        _diamonds = [(34, _by - 2), (62, _by - 14), (90, _by - 22),
                     (118, _by - 18), (146, _by - 10), (172, _by - 4)]
        for _dx, _dy in _diamonds:
            _pts = [(_dx, _dy - 9), (_dx + 9, _dy), (_dx, _dy + 9), (_dx - 9, _dy)]
            pygame.draw.polygon(surf, _PAT,  _pts)
            pygame.draw.polygon(surf, _PAT2, _pts, 1)
        _hx = 180
        _hy = _by - 5
        _head_pts = [
            (_hx, _hy + 12), (_hx + 8, _hy + 18), (_hx + 22, _hy + 18),
            (_hx + 28, _hy + 2), (_hx + 22, _hy - 14), (_hx + 8, _hy - 14),
            (_hx, _hy - 6),
        ]
        pygame.draw.polygon(surf, _HCOL, _head_pts)
        pygame.draw.polygon(surf, _DARK, _head_pts, 2)
        pygame.draw.arc(surf, _LIGHT, (_hx + 6, _hy - 12, 16, 12), 0.1, 3.05, 2)
        pygame.draw.line(surf, _DARK, (_hx + 8, _hy - 10), (_hx + 24, _hy), 1)
        pygame.draw.line(surf, _DARK, (_hx + 8, _hy + 14), (_hx + 24, _hy + 4), 1)
        pygame.draw.circle(surf, _EYE, (_hx + 14, _hy), 7)
        pygame.draw.ellipse(surf, _PUPIL, (_hx + 12, _hy - 5, 4, 10))
        pygame.draw.circle(surf, (255, 200, 190), (_hx + 13, _hy - 3), 2)
        pygame.draw.line(surf, _FANG, (_hx + 22, _hy + 12), (_hx + 24, _hy + 22), 3)
        pygame.draw.line(surf, _FANG, (_hx + 18, _hy + 14), (_hx + 19, _hy + 22), 3)
        pygame.draw.line(surf, _TONGUE, (_hx + 26, _hy + 2), (_hx + 32, _hy + 2), 2)
        pygame.draw.line(surf, _TONGUE, (_hx + 32, _hy + 2), (_hx + 35, _hy - 2), 2)
        pygame.draw.line(surf, _TONGUE, (_hx + 32, _hy + 2), (_hx + 35, _hy + 6), 2)
        return surf

    def setXPosition(self, x):
        self.x = x

    def getXPosition(self):
        return self.x

    def setYPosition(self, y):
        self.y = y

    def getYPosition(self):
        return self.y

    def setHealth(self, health):
        self.health = health

    def getHealth(self):
        return self.health

    def getWidth(self):
        return self.width

    def getHeight(self):
        return self.height

    def setStunned(self, value):
        self.stunned = value

    def getStunned(self):
        return self.stunned

    def setDamageReceived(self, damage):
        self.damageReceived = damage

    def getDamageReceived(self):
        return self.damageReceived

    def getExp(self):
        return self.exp

    def getName(self):
        return "snake"

    def getDamageAttack(self):
        return self.damageAttack

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer

    def getHurtTimer(self):
        return self.isHurtTimer

    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation

    def setStartDestructionAnimation(self, v):
        self.startDestructionAnimation = v

    def getDestructionAnimationCount(self):
        return self.destructionAnimation

    def displayDamageOnMonster(self, damage):
        """Display damage number above snake."""
        stunned_val = getattr(self, 'stunned', 1)
        try:
            s = int(stunned_val)
        except Exception:
            s = 1
        fade_frames = 8
        alpha = int(255 * min(max(0, s), fade_frames) / float(fade_frames))
        render_damage_text(self.screen, _FONT_DAMAGE, damage,
                         self.getXPosition() + 40, self.getYPosition() - 40,
                         alpha=alpha)

    def _get_current_frame(self):
        use_frame2 = (self._anim_timer // 20) % 2 == 1
        if self.direction > 0:
            return self._frame2_right if use_frame2 else self._frame1_right
        else:
            return self._frame2_left if use_frame2 else self._frame1_left

    def should_spit_venom(self):
        return self._venom_timer >= self._venom_interval and self.stunned == 0

    def spit_venom(self):
        self._venom_timer = 0
        self._venom_interval = random.randint(100, 180)
        self._venom_spit_anim = 12
        _head_x = self.x + (self.width - 20) if self.direction > 0 else self.x + 20
        _head_y = self.y + 15
        return VenomBall(_head_x, _head_y, self._bear_x + 40, self._bear_y + 50, self.screen)

    def drawMonster(self):
        """Draw the snake and handle movement."""
        if getattr(self, '_popup_frozen', False):
            frame = self._get_current_frame()
            self.screen.blit(frame, (self.x, self.y))
            if self.health < self.max_health:
                render_enemy_health_bar(self.screen, self.x + 20, self.y - 15, self.health, self.max_health)
            return

        if self.y + self.height > self.FLOOR_Y:
            self.y = self.FLOOR_Y - self.height
        if self.stunned == 0:
            self._anim_timer += 1
            self._venom_timer += 1

            if self._venom_spit_anim > 0:
                self._venom_spit_anim -= 1
                frame = self._get_current_frame()
                _stretch = pygame.transform.scale(frame, (self.width + 10, self.height - 5))
                self.screen.blit(_stretch, (self.x - 5, self.y + 5))
                _hx = self.x + (self.width - 10) if self.direction > 0 else self.x + 5
                _hy = self.y + 12
                for _ in range(3):
                    _px = _hx + random.randint(-8, 8)
                    _py = _hy + random.randint(-5, 5)
                    pygame.draw.circle(self.screen, (60, 220, 40), (_px, _py), random.randint(2, 4))
            else:
                frame = self._get_current_frame()
                self.screen.blit(frame, (self.x, self.y))

            _dx = self._bear_x - self.x
            _dist = abs(_dx)
            if _dist < self._chase_range:
                if self._personality == 'cautious' and _dist < self._preferred_gap:
                    _want_dir = -1 if _dx > 0 else 1
                elif self._personality == 'flanker' and _dist < 80:
                    _want_dir = 1 if id(self) % 2 == 0 else -1
                else:
                    _want_dir = 1 if _dx > 0 else -1
                if _want_dir != self.direction:
                    self.direction = _want_dir
                _spd = self.speed + (2 if _dist < 120 else 1)
            else:
                _spd = self.speed

            self.x += self.direction * _spd + self._sep_offset
            self._sep_offset *= 0.9
            self.walk_timer += 1

            if self.walk_timer >= self.change_direction_timer and _dist >= self._chase_range:
                self.direction *= -1
                self.walk_timer = 0
                _base_timer = random.randint(100, 200)
                _scale = getattr(self, '_turn_timer_scale', 1.0)
                self.change_direction_timer = int(_base_timer * _scale)
        else:
            self.stunned += 1
            frame = self._get_current_frame()
            hurt_img = frame.copy()
            red_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            red_overlay.fill((255, 0, 0, 100))
            hurt_img.blit(red_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(hurt_img, (self.x, self.y))

            if self.stunned >= 20:
                self.stunned = 0

        if self.health < self.max_health:
            render_enemy_health_bar(self.screen, self.x + 20, self.y - 15, self.health, self.max_health)

    def drawDestruction(self, damage):
        """Draw snake destruction animation."""
        self.destructionAnimation += 1
        self.displayDamageOnMonster(damage)
        
        if self.destructionAnimation < 30:
            alpha = int(255 * (1 - self.destructionAnimation / 30))
            img = self.snake_img.copy()
            img.set_alpha(alpha)
            self.screen.blit(img, (self.x, self.y))

    def get_poison_cooldown(self):
        """Get current poison cooldown."""
        return self.poison_cooldown

    def set_poison_cooldown(self, value):
        """Set poison cooldown."""
        self.poison_cooldown = value

    def update_poison_cooldown(self):
        """Update poison cooldown timer."""
        if self.poison_cooldown > 0:
            self.poison_cooldown -= 1


class VenomBall:
    def __init__(self, x, y, target_x, target_y, screen):
        self.screen = screen
        self.x = float(x)
        self.y = float(y)
        _dx = target_x - x
        _dy = target_y - y
        _dist = max(1, math.sqrt(_dx * _dx + _dy * _dy))
        _speed = 5.0
        self.vel_x = (_dx / _dist) * _speed
        self.vel_y = (_dy / _dist) * _speed - 3.0
        self.gravity = 0.12
        self.alive = True
        self.timer = 0
        self._trail = []
        self._size = 10

    def update(self):
        if not self.alive:
            return False
        self.timer += 1
        self._trail.append((int(self.x), int(self.y)))
        if len(self._trail) > 8:
            self._trail.pop(0)
        self.vel_y += self.gravity
        self.x += self.vel_x
        self.y += self.vel_y
        if self.y > 410 or self.x < -50 or self.x > 950 or self.timer > 180:
            self.alive = False
            return False
        for i, (tx, ty) in enumerate(self._trail):
            _a = int(80 * (i + 1) / len(self._trail))
            _r = max(2, self._size * (i + 1) // len(self._trail) - 1)
            _s = pygame.Surface((_r * 2, _r * 2), pygame.SRCALPHA)
            pygame.draw.circle(_s, (60, 200, 40, _a), (_r, _r), _r)
            self.screen.blit(_s, (tx - _r, ty - _r))
        _bx, _by = int(self.x), int(self.y)
        pygame.draw.circle(self.screen, (30, 160, 20), (_bx, _by), self._size)
        pygame.draw.circle(self.screen, (80, 230, 60), (_bx, _by), self._size - 2)
        pygame.draw.circle(self.screen, (150, 255, 120), (_bx - 2, _by - 2), 3)
        _drip_y = _by + self._size
        for _ in range(2):
            _rx = _bx + random.randint(-4, 4)
            _ry = _drip_y + random.randint(0, 6)
            pygame.draw.circle(self.screen, (50, 200, 30, 120), (_rx, _ry), random.randint(1, 3))
        return True

    def draw_frozen(self):
        _bx, _by = int(self.x), int(self.y)
        pygame.draw.circle(self.screen, (30, 160, 20), (_bx, _by), self._size)
        pygame.draw.circle(self.screen, (80, 230, 60), (_bx, _by), self._size - 2)
        pygame.draw.circle(self.screen, (150, 255, 120), (_bx - 2, _by - 2), 3)
        return True

    def get_rect(self):
        return pygame.Rect(int(self.x) - self._size, int(self.y) - self._size, self._size * 2, self._size * 2)


class Coin:
    """Collectible coin item."""
    
    def __init__(self, x, y, screen):
        self.x = x
        self.y = y
        self.screen = screen
        self.width = 30
        self.height = 30
        self.bounce_height = 0
        self.bounce_velocity = 0
        self.gravity = 0.6
        self.fall_speed = 0.0
        self.blocks = []
        self.landed = False
        
        self.coin_img = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        pygame.draw.circle(self.coin_img, (255, 210, 0), (15, 15), 15)
        pygame.draw.circle(self.coin_img, (255, 245, 120), (15, 15), 11)
        pygame.draw.circle(self.coin_img, (255, 215, 60), (18, 12), 6)
        pygame.draw.polygon(self.coin_img, (255, 255, 255), [(22, 8), (26, 10), (24, 14), (20, 12)])
        pygame.draw.line(self.coin_img, (255, 255, 255), (10, 8), (18, 8), 2)
        pygame.draw.line(self.coin_img, (255, 240, 150), (12, 4), (20, 4), 2)
    
    def setBlocks(self, blocks):
        self.blocks = blocks
        self._clamp_above_blocks()
    
    def _clamp_above_blocks(self):
        for blk in self.blocks:
            bx = blk.getBlockXPosition()
            bw = blk.getWidth() if hasattr(blk, 'getWidth') else 100
            by = blk.getBlockYPosition()
            bh = blk.getHeight() if hasattr(blk, 'getHeight') else 50
            if self.x + self.width > bx and self.x < bx + bw:
                if self.y + self.height > by and self.y < by + bh:
                    self.y = by - self.height
                    self.fall_speed = 0
                    self.landed = True

    def getXPosition(self):
        return self.x
    
    def getYPosition(self):
        return int(self.y - self.bounce_height)
    
    def setXPosition(self, x):
        self.x = x
    
    def setYPosition(self, y):
        self.y = y
    
    def update(self):
        """Update coin falling animation."""
        floor_y = 400 - self.height
        landing_y = floor_y
        for blk in self.blocks:
            bx = blk.getBlockXPosition()
            bw = blk.getWidth() if hasattr(blk, 'getWidth') else 100
            by = blk.getBlockYPosition()
            if self.x + self.width > bx and self.x < bx + bw:
                if by - self.height < landing_y and by - self.height >= self.y - 5:
                    landing_y = by - self.height
        if self.landed and abs(self.y - landing_y) > 5:
            self.landed = False
        if self.landed:
            return
        if self.y < landing_y:
            self.fall_speed += self.gravity
            self.y = min(landing_y, self.y + self.fall_speed)
        else:
            self.y = landing_y
            self.fall_speed = 0
            self.landed = True
        self.bounce_height += self.bounce_velocity
        self.bounce_velocity += self.gravity if self.bounce_height > 0 else 0
        if self.bounce_height <= 0:
            self.bounce_height = 0
            self.bounce_velocity = 0
    
    def draw(self):
        """Draw the coin."""
        self.screen.blit(self.coin_img, (self.x, self.getYPosition()))
    
    def is_grabbed(self, bear_x, bear_y, bear_w=100, bear_h=100):
        """Check if coin is grabbed by bear."""
        coin_rect = pygame.Rect(self.x, self.getYPosition(), self.width, self.height)
        bear_rect = pygame.Rect(bear_x, bear_y, bear_w, bear_h)
        return coin_rect.colliderect(bear_rect)


class DestroyableBlock:
    """Destructible block that drops a weapon on destruction."""
    
    def __init__(self, x, y, width, height, screen, secret=False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.screen = screen
        self.health = 1
        self.max_health = 1
        self.stunned = 0
        self.damageReceived = 0
        self.startDestructionAnimation = False
        self.destructionAnimation = 0
        self.isHurtTimer = 0
        self.secret = secret
    
    def getBlockXPosition(self):
        return self.x
    
    def getBlockYPosition(self):
        return self.y
    
    def setblockXPosition(self, x):
        self.x = x
    
    def setBlockYPosition(self, y):
        self.y = y
    
    def getWidth(self):
        return self.width
    
    def getHeight(self):
        return self.height
    
    def getHealth(self):
        return self.health
    
    def setHealth(self, health):
        self.health = health
    
    def getStunned(self):
        return self.stunned
    
    def setStunned(self, value):
        self.stunned = value
    
    def setDamageReceived(self, damage):
        self.damageReceived = damage
    
    def getDamageReceived(self):
        return self.damageReceived
    
    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation
    
    def setStartDestructionAnimation(self, v):
        self.startDestructionAnimation = v
    
    def getDestructionAnimationCount(self):
        return self.destructionAnimation
    
    def setHurtTimer(self, timer):
        self.isHurtTimer = timer
    
    def getHurtTimer(self):
        return self.isHurtTimer
    
    def getName(self):
        return "destroyable_block"
    
    def getExp(self):
        return 0
    
    def isBoundaryPresent(self, bear_x, bear_y):
        """Check boundary for compatibility with existing code."""
        pass
    
    def drawRectangle(self):
        """Draw the destructible block."""
        color = (180, 140, 220) if getattr(self, 'secret', False) else (200, 150, 100)
        border = (140, 80, 190) if getattr(self, 'secret', False) else (150, 100, 50)
        pygame.draw.rect(self.screen, color, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(self.screen, border, (self.x, self.y, self.width, self.height), 3)
        pygame.draw.line(self.screen, (255, 255, 255) if getattr(self, 'secret', False) else (100, 80, 60),
                         (self.x + 10, self.y + 10), (self.x + self.width - 10, self.y + self.height - 10), 2)
        pygame.draw.line(self.screen, (255, 255, 255) if getattr(self, 'secret', False) else (100, 80, 60),
                         (self.x + self.width - 10, self.y + 10), (self.x + 10, self.y + self.height - 10), 2)


class MonkeyMummy:
    """Agile monkey enemy - jumps in parabolic arcs unpredictably."""
    
    FLOOR_Y = 400

    def __init__(self, x, y, width, height, mummy1Image, mummy2Image, screen, screech_sound=None):
        self.startX = x
        self.startY = y
        self.x = x
        self.y = self.FLOOR_Y - height
        self.width = width
        self.height = height
        self.screen = screen
        self.screech_sound = screech_sound
        self._screech_cooldown = 0
        try:
            _monkey_img = pygame.image.load("Game/Images/monkey.png").convert_alpha()
            _base = pygame.transform.scale(_monkey_img, (width, height))
        except (FileNotFoundError, Exception):
            _base = pygame.transform.scale(mummy1Image, (width, height))
        self._frames_right = [_base]
        self._frames_left = [pygame.transform.flip(_base, True, False)]
        for angle in [5, -5, 8, -8]:
            rotated = pygame.transform.rotate(_base, angle)
            rw, rh = rotated.get_size()
            frame = pygame.Surface((width, height), pygame.SRCALPHA)
            frame.blit(rotated, ((width - rw) // 2, (height - rh) // 2))
            self._frames_right.append(frame)
            self._frames_left.append(pygame.transform.flip(frame, True, False))
        _squash = pygame.transform.scale(_base, (int(width * 1.2), int(height * 0.8)))
        _sq_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        _sq_surf.blit(_squash, ((width - _squash.get_width()) // 2, height - _squash.get_height()))
        self._land_frame_right = _sq_surf
        self._land_frame_left = pygame.transform.flip(_sq_surf, True, False)
        _stretch = pygame.transform.scale(_base, (int(width * 0.85), int(height * 1.15)))
        _st_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        _st_surf.blit(_stretch, ((width - _stretch.get_width()) // 2, height - _stretch.get_height()))
        self._jump_frame_right = _st_surf
        self._jump_frame_left = pygame.transform.flip(_st_surf, True, False)
        self.mummy1 = _base
        self.mummy2 = pygame.transform.flip(_base, True, False)
        self._anim_timer = 0
        self._land_timer = 0
        self.health = int(20 * 1.15)
        self.max_health = self.health
        self._defense = random.randint(1, 10) / 100.0
        self.damageAttack = 11
        self.walk_speed = random.choice([2, 3, 3, 4])
        self.rand = random.randint(25, 55)
        self._bear_x = 400
        self._bear_y = 300
        self._sep_offset = 0.0
        self._chase_range = random.randint(350, 600)
        self._preferred_gap = random.randint(40, 100)
        self.direction = 1
        self.stunned = 0
        self.blocks = []
        self.damageReceived = 0
        self.exp = 25
        self.changeDirectionX = 0
        self.isHurtTimer = 0
        self.destructionAnimation = 0
        self.startDestructionAnimation = False
        self.jump_timer = 0
        self.can_jump = True
        self.jump_velocity = 0
        self.jump_h_speed = 0
        self.gravity = 0.5
        self._bob_offset = 0
    
    def setXPosition(self, x):
        self.x = x
    
    def getXPosition(self):
        return self.x
    
    def setYPosition(self, y):
        self.y = y
    
    def getYPosition(self):
        return self.y
    
    def setHealth(self, health):
        self.health = health
    
    def getHealth(self):
        return self.health
    
    def getWidth(self):
        return self.width
    
    def getHeight(self):
        return self.height
    
    def setBlocks(self, blocks):
        self.blocks = blocks
    
    def setStunned(self, stunned):
        self.stunned = stunned
    
    def getStunned(self):
        return self.stunned
    
    def setDamageReceived(self, damage):
        self.damageReceived = damage
    
    def getDamageReceived(self):
        return self.damageReceived
    
    def getExp(self):
        return self.exp
    
    def getName(self):
        return "monkeyMummy"

    def getDamageAttack(self):
        return self.damageAttack

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer
    
    def getHurtTimer(self):
        return self.isHurtTimer
    
    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation
    
    def setStartDestructionAnimation(self, v):
        self.startDestructionAnimation = v
    
    def getDestructionAnimationCount(self):
        return self.destructionAnimation
    
    def displayDamageOnMonster(self, damage):
        """Display damage number above monkey mummy."""
        stunned_val = getattr(self, 'stunned', 1)
        try:
            s = int(stunned_val)
        except Exception:
            s = 1
        fade_frames = 8
        alpha = int(255 * min(max(0, s), fade_frames) / float(fade_frames))
        render_damage_text(self.screen, _FONT_DAMAGE, damage,
                         self.getXPosition() + 40, self.getYPosition() - 40,
                         alpha=alpha)
    
    def _get_anim_frame(self):
        if self._land_timer > 0:
            return self._land_frame_left if self.direction < 0 else self._land_frame_right
        if not self.can_jump:
            return self._jump_frame_left if self.direction < 0 else self._jump_frame_right
        idx = (self._anim_timer // 8) % len(self._frames_right)
        return self._frames_left[idx] if self.direction < 0 else self._frames_right[idx]

    def drawMonster(self):
        """Draw monkey mummy with jumping behavior."""
        if getattr(self, '_popup_frozen', False):
            frame = self._get_anim_frame()
            self.screen.blit(frame, (self.x, self.y))
            if self.health < self.max_health:
                render_enemy_health_bar(self.screen, self.x + 10, self.y - 15, self.health, self.max_health)
            return

        if self._screech_cooldown > 0:
            self._screech_cooldown -= 1
        if self.stunned == 0:
            self._anim_timer += 1
            if self._land_timer > 0:
                self._land_timer -= 1

            if self.can_jump:
                self._bob_offset = int(2 * math.sin(self._anim_timer * 0.15))
            else:
                self._bob_offset = 0

            frame = self._get_anim_frame()
            self.screen.blit(frame, (self.x, self.y + self._bob_offset))

            self.changeDirectionX += 1
            self.jump_timer += 1

            if self.jump_timer > random.randint(30, 70) and self.can_jump:
                self.jump_timer = 0
                self.jump_velocity = random.uniform(-16, -11)
                _dx = self._bear_x - self.x
                _dist = abs(_dx)
                if _dist < 500:
                    _toward = 1 if _dx > 0 else -1
                    self.jump_h_speed = _toward * random.choice([4, 5, 6])
                else:
                    self.jump_h_speed = random.choice([-5, -3, 3, 5])
                self.can_jump = False
                if self.screech_sound and self._screech_cooldown <= 0:
                    self.screech_sound.play()
                    self._screech_cooldown = 60

            was_airborne = not self.can_jump
            self.jump_velocity += self.gravity
            self.y += self.jump_velocity
            if not self.can_jump:
                self.x += self.jump_h_speed

            for block in self.blocks:
                block_rect = pygame.Rect(block.getBlockXPosition(),
                                        block.getBlockYPosition(),
                                        block.getWidth(),
                                        block.getHeight())
                monkey_rect = pygame.Rect(self.x, self.y, self.width, self.height)
                if monkey_rect.colliderect(block_rect) and self.jump_velocity > 0:
                    self.y = block_rect.top - self.height
                    self.jump_velocity = 0
                    if was_airborne and not self.can_jump:
                        self._land_timer = 6
                    self.can_jump = True
                    self.jump_h_speed = 0

            if self.y + self.height >= self.FLOOR_Y:
                self.y = self.FLOOR_Y - self.height
                self.jump_velocity = 0
                if was_airborne and not self.can_jump:
                    self._land_timer = 6
                self.can_jump = True
                self.jump_h_speed = 0

            if self.can_jump:
                _dx_g = self._bear_x - self.x
                _dist_g = abs(_dx_g)
                if _dist_g < self._chase_range:
                    if _dist_g < self._preferred_gap:
                        self.direction = -1 if _dx_g > 0 else 1
                    else:
                        self.direction = 1 if _dx_g > 0 else -1
                elif self.changeDirectionX > self.rand:
                    self.direction = random.choice([-1, 1])
                    self.changeDirectionX = 0
                    self.rand = random.randint(20, 60)
                self.x += self.direction * self.walk_speed + self._sep_offset
                self._sep_offset *= 0.9

            if self.x < -50:
                self.x = 900
            elif self.x > 900:
                self.x = -50
        else:
            self.stunned += 1
            frame = self._get_anim_frame()
            hurt_img = frame.copy()
            red_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            red_overlay.fill((255, 0, 0, 100))
            hurt_img.blit(red_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(hurt_img, (self.x, self.y))

            if self.stunned >= 15:
                self.stunned = 0

        if self.health < self.max_health:
            render_enemy_health_bar(self.screen, self.x + 10, self.y - 15, self.health, self.max_health)

    def drawDestruction(self, damage):
        """Draw destruction animation."""
        self.destructionAnimation += 1
        self.displayDamageOnMonster(damage)
        
        if self.destructionAnimation < 30:
            alpha = int(255 * (1 - self.destructionAnimation / 30))
            img = self.mummy1.copy() if self.direction < 0 else self.mummy2.copy()
            img.set_alpha(alpha)
            self.screen.blit(img, (self.x, self.y))


class Lion:
    FLOOR_Y = 400

    def __init__(self, x, y, screen, roar_sound=None):
        self.x = x
        self.width = 250
        self.height = 170
        self.y = self.FLOOR_Y - self.height
        self.screen = screen
        self.roar_sound = roar_sound
        self._roar_cooldown = 0
        self.health = int(25 * 1.20)
        self.max_health = self.health
        self._defense = random.randint(1, 10) / 100.0
        self.speed = random.choice([4, 5, 5, 6])
        self.direction = -1 if random.random() > 0.5 else 1
        self.stunned = 0
        self.damageReceived = 0
        self.exp = 20
        self.damageAttack = 13
        self.isHurtTimer = 0
        self.destructionAnimation = 0
        self.startDestructionAnimation = False
        self.walk_timer = 0
        self.change_direction_timer = random.randint(60, 140)
        self.charge_speed = random.choice([7, 8, 8, 9])
        self._bear_x = 400
        self._bear_y = 300
        self._sep_offset = 0.0
        self._charge_cooldown = random.randint(0, 60)
        self._charge_chance = random.uniform(0.01, 0.03)
        self._pounce_chance = random.uniform(0.03, 0.08)
        self.is_charging = False
        self.charge_timer = 0
        self._anim_timer = 0
        self._bob_offset = 0
        self._pounce_vy = 0
        self._is_airborne = False

        try:
            _base = pygame.image.load("Game/Images/lion.png").convert_alpha()
            _base = pygame.transform.scale(_base, (self.width, self.height))
            _lex = int(self.width * 0.78)
            _ley = int(self.height * 0.28)
            pygame.draw.circle(_base, (255, 200, 50), (_lex, _ley), 6)
            pygame.draw.circle(_base, (180, 140, 20), (_lex, _ley), 6, 1)
            pygame.draw.circle(_base, (30, 30, 30), (_lex + 1, _ley), 3)
            pygame.draw.circle(_base, (255, 255, 220), (_lex - 1, _ley - 2), 2)
        except (FileNotFoundError, Exception):
            _w, _h = self.width, self.height
            _base = pygame.Surface((_w, _h), pygame.SRCALPHA)
            _body_y = _h - 70
            pygame.draw.ellipse(_base, (210, 160, 60), (20, _body_y, _w - 60, 60))
            pygame.draw.ellipse(_base, (180, 130, 40), (20, _body_y, _w - 60, 60), 2)
            for _lx in [45, 65, _w - 85, _w - 65]:
                pygame.draw.rect(_base, (190, 140, 50), (_lx, _body_y + 40, 14, 28))
                pygame.draw.rect(_base, (160, 110, 30), (_lx, _body_y + 40, 14, 28), 2)
            _mx = _w - 50
            _my = _body_y - 20
            for _a in range(0, 360, 30):
                _rad = math.radians(_a)
                _rx = _mx + int(28 * math.cos(_rad))
                _ry = _my + int(28 * math.sin(_rad))
                pygame.draw.circle(_base, (180, 110, 30), (_rx, _ry), 10)
            pygame.draw.circle(_base, (230, 180, 80), (_mx, _my), 24)
            pygame.draw.circle(_base, (200, 150, 50), (_mx, _my), 24, 2)
            pygame.draw.circle(_base, (40, 40, 40), (_mx + 6, _my - 4), 5)
            pygame.draw.circle(_base, (255, 255, 255), (_mx + 5, _my - 5), 2)
            pygame.draw.ellipse(_base, (160, 100, 40), (_mx - 4, _my + 6, 16, 8))
            _tx = 10
            _ty = _body_y + 20
            for _i in range(8):
                pygame.draw.circle(_base, (190, 140, 50), (_tx - _i * 1, _ty + _i * 2), max(2, 4 - _i // 2))
        self._walk_frames_right = [_base]
        self._walk_frames_left = [pygame.transform.flip(_base, True, False)]
        for angle in [3, -3, 5, -5]:
            rotated = pygame.transform.rotate(_base, angle)
            rw, rh = rotated.get_size()
            frame = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            frame.blit(rotated, ((self.width - rw) // 2, (self.height - rh) // 2))
            self._walk_frames_right.append(frame)
            self._walk_frames_left.append(pygame.transform.flip(frame, True, False))
        _charge = pygame.transform.scale(_base, (int(self.width * 1.1), int(self.height * 0.9)))
        _ch_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        _ch_surf.blit(_charge, ((self.width - _charge.get_width()) // 2, self.height - _charge.get_height()))
        self._charge_frame_right = _ch_surf
        self._charge_frame_left = pygame.transform.flip(_ch_surf, True, False)
        self.lion_img = _base
        self.lion_img_left = pygame.transform.flip(_base, True, False)

    def setXPosition(self, x):
        self.x = x

    def getXPosition(self):
        return self.x

    def setYPosition(self, y):
        self.y = y

    def getYPosition(self):
        return self.y

    def setHealth(self, health):
        self.health = health

    def getHealth(self):
        return self.health

    def getWidth(self):
        return self.width

    def getHeight(self):
        return self.height

    def setStunned(self, value):
        self.stunned = value

    def getStunned(self):
        return self.stunned

    def setDamageReceived(self, damage):
        self.damageReceived = damage

    def getDamageReceived(self):
        return self.damageReceived

    def getExp(self):
        return self.exp

    def getName(self):
        return "lion"

    def getDamageAttack(self):
        return self.damageAttack

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer

    def getHurtTimer(self):
        return self.isHurtTimer

    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation

    def setStartDestructionAnimation(self, v):
        self.startDestructionAnimation = v

    def getDestructionAnimationCount(self):
        return self.destructionAnimation

    def displayDamageOnMonster(self, damage):
        stunned_val = getattr(self, 'stunned', 1)
        try:
            s = int(stunned_val)
        except Exception:
            s = 1
        fade_frames = 8
        alpha = int(255 * min(max(0, s), fade_frames) / float(fade_frames))
        render_damage_text(self.screen, _FONT_DAMAGE, damage,
                         self.getXPosition() + 45, self.getYPosition() - 30,
                         alpha=alpha)

    def _get_anim_frame(self):
        if self.is_charging:
            return self._charge_frame_left if self.direction < 0 else self._charge_frame_right
        idx = (self._anim_timer // 10) % len(self._walk_frames_right)
        return self._walk_frames_left[idx] if self.direction < 0 else self._walk_frames_right[idx]

    def drawMonster(self):
        if getattr(self, '_popup_frozen', False):
            frame = self._get_anim_frame()
            self.screen.blit(frame, (self.x, self.y))
            if self.health < self.max_health:
                render_enemy_health_bar(self.screen, self.x + 20, self.y - 15, self.health, self.max_health)
            return

        if self._roar_cooldown > 0:
            self._roar_cooldown -= 1
        if self.stunned == 0:
            self._anim_timer += 1

            if not self._is_airborne:
                self._bob_offset = int(1.5 * math.sin(self._anim_timer * 0.12))
            else:
                self._bob_offset = 0

            frame = self._get_anim_frame()
            self.screen.blit(frame, (self.x, self.y + self._bob_offset))

            self.walk_timer += 1

            _dx = self._bear_x - self.x
            _dist = abs(_dx)
            _face_dir = 1 if _dx > 0 else -1
            if _face_dir != self.direction:
                self.direction = _face_dir

            if self._charge_cooldown > 0:
                self._charge_cooldown -= 1

            if not self.is_charging and not self._is_airborne and _dist < 400 and self._charge_cooldown <= 0 and random.random() < self._charge_chance:
                self.is_charging = True
                self.charge_timer = random.randint(30, 60)
                self._charge_cooldown = random.randint(40, 100)
                if self.roar_sound and self._roar_cooldown <= 0:
                    self.roar_sound.play()
                    self._roar_cooldown = 90

            if not self._is_airborne and self.is_charging and _dist < 200 and random.random() < self._pounce_chance:
                self._pounce_vy = -10
                self._is_airborne = True

            if self._is_airborne:
                self._pounce_vy += 0.6
                self.y += self._pounce_vy
                self.x += self.direction * self.charge_speed + self._sep_offset
                if self.y + self.height >= self.FLOOR_Y:
                    self.y = self.FLOOR_Y - self.height
                    self._pounce_vy = 0
                    self._is_airborne = False
            elif self.is_charging:
                self.x += self.direction * self.charge_speed + self._sep_offset
                self.charge_timer -= 1
                if self.charge_timer <= 0:
                    self.is_charging = False
            else:
                if _dist > 30:
                    self.x += self.direction * self.speed + self._sep_offset
                    if _dist < 200:
                        self.x += self.direction * 2
            self._sep_offset *= 0.9

            if self.y + self.height >= self.FLOOR_Y:
                self.y = self.FLOOR_Y - self.height
                self._pounce_vy = 0
                self._is_airborne = False

            if self.x < -50:
                self.x = 900
            elif self.x > 900:
                self.x = -50
        else:
            self.stunned += 1
            frame = self._get_anim_frame()
            hurt_img = frame.copy()
            red_overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            red_overlay.fill((255, 0, 0, 100))
            hurt_img.blit(red_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(hurt_img, (self.x, self.y))

            if self.stunned >= 15:
                self.stunned = 0

        if self.health < self.max_health:
            render_enemy_health_bar(self.screen, self.x + 20, self.y - 15, self.health, self.max_health)

    def drawDestruction(self, damage):
        self.destructionAnimation += 1
        self.displayDamageOnMonster(damage)

        if self.destructionAnimation < 30:
            alpha = int(255 * (1 - self.destructionAnimation / 30))
            img = self.lion_img.copy()
            img.set_alpha(alpha)
            self.screen.blit(img, (self.x, self.y))
