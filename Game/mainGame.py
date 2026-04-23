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
    "frankenbears":   (240, 240),
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
        m_w, m_h = 240, 240
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

            # ── MMX JUMP BLIP: short ascending sine "boop" ──────────────
            _n = int(_RATE * 0.10)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _f = 520 + 380 * (_t / 0.10)
                _sq = 1.0 if (_math.sin(2*_math.pi*_f*_t) > 0) else -1.0
                _s = (_math.sin(2*_math.pi*_f*_t) * 0.55
                      + _sq * 0.18
                      + _math.sin(2*_math.pi*_f*2*_t) * 0.10)
                _env = min(1.0, _i/(_RATE*0.005)) * max(0.0, 1.0 - _t/0.10) ** 1.5
                _smp.append(_s * _env * 0.85)
            self.mmx_jump_sound = _make_snd(_smp)
            self.mmx_jump_sound.set_volume(1.0)
            # Alternate jump sound (cartoon boing) — plays 30% of the time
            try:
                self.mmx_jump_sound_alt = pygame.mixer.Sound(
                    "Game/Sounds/samples/jump_cartoon_boing.wav")
                self.mmx_jump_sound_alt.set_volume(1.0)
            except Exception:
                self.mmx_jump_sound_alt = None

            # ── MMX LAND TAP: low click + soft thump ────────────────────
            _n = int(_RATE * 0.13)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _click = (_rnd.gauss(0, 1) * max(0.0, 1.0 - _t * 40)) * 0.6
                _thump = _math.sin(2*_math.pi*(110 - 60*_t/0.13)*_t) * max(0.0, 1.0 - _t/0.13) ** 1.4 * 0.55
                _smp.append((_click + _thump) * 0.95)
            self.mmx_land_sound = _make_snd(_smp)
            self.mmx_land_sound.set_volume(1.0)

            # ── MMX DASH: sharp filtered noise sweep ────────────────────
            _n = int(_RATE * 0.22)
            _smp = []
            _prev = 0.0
            for _i in range(_n):
                _t = _i / _RATE
                _noise = _rnd.gauss(0, 1)
                _alpha = 0.18 + 0.55 * (_t / 0.22)
                _filt = _prev + _alpha * (_noise - _prev)
                _prev = _filt
                _whoosh = _math.sin(2*_math.pi*(180 + 360*_t/0.22)*_t) * 0.30
                _env = min(1.0, _i/(_RATE*0.008)) * max(0.0, 1.0 - _t/0.22) ** 0.9
                _smp.append((_filt * 0.55 + _whoosh) * _env * 0.95)
            self.mmx_dash_sound = _make_snd(_smp)
            self.mmx_dash_sound.set_volume(1.0)

            # ── SLIDE SCRAPE: longer gritty floor scrape with whoosh ────
            _n = int(_RATE * 0.55)
            _smp = []
            _prev = 0.0
            _prev2 = 0.0
            for _i in range(_n):
                _t = _i / _RATE
                _noise = _rnd.gauss(0, 1)
                # band-pass-ish: two cascaded one-pole filters
                _alpha = 0.35
                _prev = _prev + _alpha * (_noise - _prev)
                _prev2 = _prev2 + 0.55 * (_prev - _prev2)
                _grit = (_prev - _prev2)
                # falling whoosh swept down
                _fhz = 480 - 380 * (_t / 0.55)
                _whoosh = _math.sin(2*_math.pi*_fhz*_t) * 0.18
                # envelope: quick attack, slow decay
                _env = min(1.0, _i/(_RATE*0.012)) * max(0.0, 1.0 - _t/0.55) ** 1.4
                _smp.append((_grit * 1.8 + _whoosh) * _env * 0.85)
            self.slide_scrape_sound = _make_snd(_smp)
            self.slide_scrape_sound.set_volume(0.85)

            # ── DANGER ALARM: classic two-tone "low HP" beep, loops ────
            _n = int(_RATE * 0.55)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                # Two beeps inside 0.55s: 0.00-0.18s and 0.28-0.46s
                _in_beep1 = 0.0 <= _t < 0.18
                _in_beep2 = 0.28 <= _t < 0.46
                _val = 0.0
                if _in_beep1:
                    _bt = _t - 0.0
                    _env = min(1.0, _bt / 0.012) * max(0.0, 1.0 - _bt / 0.18) ** 0.6
                    # Square-ish wave at 880 Hz with slight detune
                    _sq = 1.0 if (_bt * 880) % 1.0 < 0.5 else -1.0
                    _val = _sq * _env * 0.55
                elif _in_beep2:
                    _bt = _t - 0.28
                    _env = min(1.0, _bt / 0.012) * max(0.0, 1.0 - _bt / 0.18) ** 0.6
                    _sq = 1.0 if (_bt * 988) % 1.0 < 0.5 else -1.0
                    _val = _sq * _env * 0.55
                _smp.append(_val)
            self.danger_alarm_sound = _make_snd(_smp)
            self.danger_alarm_sound.set_volume(0.55)
            try:
                self.danger_alarm_channel = pygame.mixer.Channel(6)
            except Exception:
                self.danger_alarm_channel = None
            self._danger_alarm_playing = False

            # ── MMX CHARGED SHOT: rising whir + release boom ────────────
            _n = int(_RATE * 0.55)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                if _t < 0.20:
                    # Charge ramp
                    _f = 240 + 600 * (_t / 0.20)
                    _s = (_math.sin(2*_math.pi*_f*_t) * 0.40
                          + _math.sin(2*_math.pi*_f*1.5*_t) * 0.22
                          + _math.sin(2*_math.pi*_f*2*_t) * 0.15)
                    _env = min(1.0, _i/(_RATE*0.010))
                else:
                    # Release: descending power chord + noise burst
                    _td = _t - 0.20
                    _f = 880 - 720 * (_td / 0.35)
                    _s = (_math.sin(2*_math.pi*_f*_t) * 0.55
                          + _math.sin(2*_math.pi*_f*0.5*_t) * 0.40
                          + _math.sin(2*_math.pi*_f*2*_t) * 0.20
                          + _rnd.gauss(0, 1) * max(0.0, 1.0 - _td * 8) * 0.35)
                    _env = max(0.0, 1.0 - _td/0.35) ** 1.1
                _smp.append(_s * _env * 0.85)
            self.mmx_charged_shot_sound = _make_snd(_smp)
            self.mmx_charged_shot_sound.set_volume(1.0)

            # ── MMX POWER-UP / CAPSULE jingle: ascending blip arpeggio ──
            _n = int(_RATE * 0.55)
            _smp = []
            _notes = [(0.00, 523), (0.10, 659), (0.20, 784),
                      (0.30, 1047), (0.42, 1319)]
            for _i in range(_n):
                _t = _i / _RATE
                _s = 0.0
                for _onset, _f in _notes:
                    if _t >= _onset:
                        _td = _t - _onset
                        if _td < 0.13:
                            _ne = (1.0 - _td/0.13) ** 1.2
                            _s += (_math.sin(2*_math.pi*_f*_td) * 0.40
                                   + _math.sin(2*_math.pi*_f*2*_td) * 0.18) * _ne
                _env = max(0.0, 1.0 - _t/0.55) ** 0.6
                _smp.append(_s * _env * 0.85)
            self.mmx_powerup_sound = _make_snd(_smp)
            self.mmx_powerup_sound.set_volume(1.0)

            # ── MMX HURT SPARK: harsh noise + pitched ring ──────────────
            _n = int(_RATE * 0.18)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _spark = _rnd.gauss(0, 1) * max(0.0, 1.0 - _t/0.05) * 0.55
                _ring = _math.sin(2*_math.pi*(680 - 280*_t/0.18)*_t) * max(0.0, 1.0 - _t/0.18) * 0.35
                _smp.append((_spark + _ring) * 0.55)
            self.mmx_spark_sound = _make_snd(_smp)
            self.mmx_spark_sound.set_volume(1.0)

            # ── MMX COIN PLUCK: short two-tone "ting" ───────────────────
            _n = int(_RATE * 0.12)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _f = 1320 if _t < 0.045 else 1760
                _s = (_math.sin(2*_math.pi*_f*_t) * 0.55
                      + _math.sin(2*_math.pi*_f*2*_t) * 0.20)
                _env = max(0.0, 1.0 - _t/0.12) ** 1.3
                _smp.append(_s * _env * 0.85)
            self.mmx_coin_sound = _make_snd(_smp)
            self.mmx_coin_sound.set_volume(1.0)
            # Alternate coin sound (cha-ching) — plays 30% of the time
            try:
                self.mmx_coin_sound_alt = pygame.mixer.Sound(
                    "Game/Sounds/samples/coin_chaching.wav")
                self.mmx_coin_sound_alt.set_volume(1.0)
            except Exception:
                self.mmx_coin_sound_alt = None

            # ── MMX LEMON SHOT: short "pew" pellet ──────────────────────
            _n = int(_RATE * 0.09)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _f = 1100 - 700 * (_t / 0.09)
                _s = (_math.sin(2*_math.pi*_f*_t) * 0.55
                      + _math.sin(2*_math.pi*_f*2*_t) * 0.18)
                _env = min(1.0, _i/(_RATE*0.004)) * max(0.0, 1.0 - _t/0.09) ** 1.4
                _smp.append(_s * _env * 0.90)
            self.mmx_lemon_shot_sound = _make_snd(_smp)
            self.mmx_lemon_shot_sound.set_volume(1.0)

            # ── MMX ENEMY EXPLODE: short pop + noise burst ──────────────
            _n = int(_RATE * 0.28)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _pop = _math.sin(2*_math.pi*(220 - 160*_t/0.28)*_t) * max(0.0, 1.0 - _t/0.18) * 0.55
                _noise = _rnd.gauss(0, 1) * max(0.0, 1.0 - _t/0.28) ** 1.2 * 0.45
                _ring = _math.sin(2*_math.pi*(880 - 600*_t/0.28)*_t) * max(0.0, 1.0 - _t/0.20) * 0.22
                _smp.append((_pop + _noise + _ring) * 0.95)
            self.mmx_enemy_explode_sound = _make_snd(_smp)
            self.mmx_enemy_explode_sound.set_volume(1.0)

            # ── MMX PAUSE: classic two-tone "wuh-wuh" ───────────────────
            _n = int(_RATE * 0.32)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                if _t < 0.14:
                    _f = 660
                    _ne = min(1.0, _i/(_RATE*0.005)) * max(0.0, 1.0 - _t/0.14) ** 0.8
                else:
                    _td = _t - 0.14
                    _f = 440
                    _ne = min(1.0, (_i - _RATE*0.14)/(_RATE*0.005)) * max(0.0, 1.0 - _td/0.18) ** 0.8
                _sq = 1.0 if (_math.sin(2*_math.pi*_f*_t) > 0) else -1.0
                _s = (_math.sin(2*_math.pi*_f*_t) * 0.45 + _sq * 0.20) * _ne
                _smp.append(_s * 0.40)
            self.mmx_pause_sound = _make_snd(_smp)
            self.mmx_pause_sound.set_volume(1.0)

            # ── MMX LOW HEALTH WARNING: pulsing high beep ───────────────
            _n = int(_RATE * 0.22)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _f = 1760
                _pulse = 1.0 if (int(_t * 22) % 2 == 0) else 0.4
                _s = _math.sin(2*_math.pi*_f*_t) * 0.45 * _pulse
                _env = min(1.0, _i/(_RATE*0.004)) * max(0.0, 1.0 - _t/0.22) ** 1.0
                _smp.append(_s * _env * 0.40)
            self.mmx_low_health_sound = _make_snd(_smp)
            self.mmx_low_health_sound.set_volume(0.35)

            # ── MMX 1-UP / LIFE GAIN: bright ascending arpeggio ─────────
            _n = int(_RATE * 0.70)
            _smp = []
            _notes = [(0.00, 784), (0.10, 988), (0.20, 1175),
                      (0.30, 1568), (0.42, 1976), (0.55, 2349)]
            for _i in range(_n):
                _t = _i / _RATE
                _s = 0.0
                for _onset, _f in _notes:
                    if _t >= _onset:
                        _td = _t - _onset
                        if _td < 0.14:
                            _ne = (1.0 - _td/0.14) ** 1.1
                            _s += (_math.sin(2*_math.pi*_f*_td) * 0.36
                                   + _math.sin(2*_math.pi*_f*2*_td) * 0.16) * _ne
                _env = max(0.0, 1.0 - _t/0.70) ** 0.5
                _smp.append(_s * _env * 0.42)
            self.mmx_life_up_sound = _make_snd(_smp)
            self.mmx_life_up_sound.set_volume(1.0)

            # ── MMX BOSS DOOR: low rising drone with metal clank ────────
            _n = int(_RATE * 0.85)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _f = 60 + 90 * (_t / 0.85)
                _drone = (_math.sin(2*_math.pi*_f*_t) * 0.50
                          + _math.sin(2*_math.pi*_f*1.5*_t) * 0.25
                          + _math.sin(2*_math.pi*_f*2*_t) * 0.18)
                _clank = 0.0
                if 0.45 < _t < 0.52:
                    _clank = _rnd.gauss(0, 1) * 0.45 + _math.sin(2*_math.pi*440*_t) * 0.30
                _env = min(1.0, _i/(_RATE*0.020)) * max(0.0, 1.0 - _t/0.85) ** 0.7
                _smp.append((_drone + _clank) * _env * 0.45)
            self.mmx_boss_door_sound = _make_snd(_smp)
            self.mmx_boss_door_sound.set_volume(1.0)

            # ── MMX MENU SELECT: tiny "tik" cursor blip ─────────────────
            _n = int(_RATE * 0.04)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _f = 1480
                _s = _math.sin(2*_math.pi*_f*_t) * 0.55
                _env = max(0.0, 1.0 - _t/0.04) ** 1.6
                _smp.append(_s * _env * 0.38)
            self.mmx_select_sound = _make_snd(_smp)
            self.mmx_select_sound.set_volume(1.0)

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
            try:
                self.fancy_death_bang_sound = pygame.mixer.Sound("Game/Sounds/fancy_death_bang.wav")
                self.fancy_death_bang_sound.set_volume(1.0)
            except Exception:
                self.fancy_death_bang_sound = None

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
                # Clean explosive boom: pure low sines, no FM wobble (no "wawawa")
                _boom = (_math.sin(2*_math.pi*55*_t) * 1.0
                         + _math.sin(2*_math.pi*32*_t) * 0.85
                         + _math.sin(2*_math.pi*80*_t) * 0.45)
                _crackle = _rnd.gauss(0, 0.8) * max(0.0, 1.0 - _t * 2.5) * 0.7
                _s = (_initial_blast + _boom * _env + _crackle)
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

            _n = int(_RATE * 0.7)
            _smp = []
            for _i in range(_n):
                _t = _i / _RATE
                _dur = 0.7
                _f_base = 900 - 500 * (_t / _dur)
                _cackle = _math.sin(2 * _math.pi * 12.0 * _t) * 80
                _waver = _math.sin(2 * _math.pi * 5.5 * _t) * 40
                _f = _f_base + _cackle + _waver
                _shriek = _math.sin(2*_math.pi*_f*_t) * 0.35
                _harm2 = _math.sin(2*_math.pi*_f*2.01*_t) * 0.18
                _harm3 = _math.sin(2*_math.pi*_f*3.03*_t) * 0.10
                _sub = _math.sin(2*_math.pi*_f*0.49*_t) * 0.12
                _hiss = _rnd.gauss(0, 0.12) * max(0.0, 1.0 - _t/_dur) ** 0.5
                _crackle_burst = 0.0
                if _rnd.random() < 0.08:
                    _crackle_burst = _rnd.gauss(0, 0.25)
                _echo = _math.sin(2*_math.pi*(_f*0.75)*_t + _math.sin(2*_math.pi*3.0*_t)*2.0) * 0.08
                _env = min(_i/(_RATE*0.015), 1.0) * max(0.0, 1.0 - _t/_dur) ** 0.6
                _s = (_shriek + _harm2 + _harm3 + _sub + _hiss + _crackle_burst + _echo) * _env
                _smp.append(max(-1.0, min(1.0, _s * 0.75)))
            self.witch_beam_sound = _make_snd(_smp)
            self.witch_beam_sound.set_volume(0.55)

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

            pygame.mixer.set_num_channels(21)

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

            _smp = []
            _melody_freqs = [130.8, 146.8, 164.8, 174.6, 196.0, 220.0, 246.9, 261.6]
            for _i in range(_LN):
                _t = _i / _RATE
                _beat_pos = _math.fmod(_t, 0.5)
                _sub = _math.fmod(_t, 0.25)
                _note_idx = int(_t * 2) % len(_melody_freqs)
                _f = _melody_freqs[_note_idx]
                _kick = _math.exp(-_beat_pos * 20) * _math.sin(2 * _math.pi * _f * _t) * 0.5
                _ghost = _math.exp(-max(0, _sub - 0.12) * 25) * _math.sin(2 * _math.pi * (_f * 1.5) * _t) * 0.25
                _rim = _math.exp(-max(0, _sub - 0.06) * 35) * _rnd.gauss(0, 0.15) * (1 if _sub > 0.06 else 0)
                _s = _kick + _ghost + _rim
                _fade = min(1.0, _i / (_RATE * 0.3)) * min(1.0, (_LN - _i) / (_RATE * 0.3))
                _smp.append(max(-1.0, min(1.0, _s * _fade)))
            self._layer_melody_drums = _make_snd(_smp)

            # Replacement bonus drum layers (loaded from disk).
            # Per-sound volumes: pulse is the strongest hit so kept lowest (30%);
            # heart and swell are softer but get a bit more presence (50%).
            try:
                self._layer_drum_pulse = pygame.mixer.Sound("Game/Sounds/layer_drum_pulse.wav")
                self._layer_drum_pulse.set_volume(0.30)
            except Exception:
                self._layer_drum_pulse = None
            try:
                self._layer_drum_heart = pygame.mixer.Sound("Game/Sounds/layer_drum_heart.wav")
                self._layer_drum_heart.set_volume(0.50)
            except Exception:
                self._layer_drum_heart = None
            try:
                self._layer_drum_swell = pygame.mixer.Sound("Game/Sounds/layer_drum_swell.wav")
                self._layer_drum_swell.set_volume(0.50)
            except Exception:
                self._layer_drum_swell = None

            pygame.mixer.set_num_channels(21)

            self._tension_layers = [
                {'sound': self._layer_heartbeat, 'channel': pygame.mixer.Channel(12),
                 'threshold': 500,  'max_vol': 0.18, 'current_vol': 0.0, 'active': False},
                {'sound': self._layer_drums,     'channel': pygame.mixer.Channel(14),
                 'threshold': 4000, 'max_vol': 0.32, 'current_vol': 0.0, 'active': False},
                {'sound': self._layer_choir,     'channel': pygame.mixer.Channel(15),
                 'threshold': 8000, 'max_vol': 0.13, 'current_vol': 0.0, 'active': False},
                {'sound': self._layer_melody_drums, 'channel': pygame.mixer.Channel(19),
                 'threshold': 36000, 'max_vol': 0.18, 'current_vol': 0.0, 'active': False},
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
        # First 4 enemies in a fresh run get 50% HP for an easier start
        self._easy_start_remaining = 4
        # Death animation state (-1 = not dying)
        self._death_anim_frame = -1
        self._death_anim_x = 0
        self._death_anim_y = 0
        self._death_anim_dir = 1
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
        self._bomb_wave_30 = False
        self._bomb_wave_60 = False
        self.heart_drops = []
        self.shaman_orbs = []
        self._shaman_orb_timer = 0
        self.witch_beams = []
        self._toasts = []
        self._paused = False
        self._paused_snapshot = None
        self._muted = False
        self._saved_music_vol = 1.0
        self._combo = 0
        self._combo_timer = 0
        self._combo_max_session = 0
        self._combo_bonus_display = None
        self._kill_total = 0
        self._intro_banner = None
        self._mummy_arrow_frames = 0

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
        # Tier-1 RED fireball — comet-style: tapered tail, hot white core,
        # crimson outer glow with scalloped flame edges.
        def _redFireball(size=54):
            import math as _m
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            cx, cy = size // 2, size // 2
            # Soft outer halo
            for _r, _a in [(size//2, 60), (size//2 - 4, 110), (size//2 - 8, 170)]:
                _g = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.circle(_g, (255, 60, 20, _a), (cx, cy), _r)
                s.blit(_g, (0, 0))
            # Flame petals around the body for a flickery silhouette
            for _ang in range(0, 360, 30):
                _rad = _m.radians(_ang)
                _px = cx + int((size//2 - 6) * _m.cos(_rad))
                _py = cy + int((size//2 - 6) * _m.sin(_rad))
                pygame.draw.circle(s, (255, 110, 30, 220), (_px, _py), 6)
            # Mid body — bright orange
            pygame.draw.circle(s, (255, 150,  40, 255), (cx, cy), size // 3)
            # Hot inner core — yellow→white
            pygame.draw.circle(s, (255, 230, 120, 255), (cx, cy), size // 5)
            pygame.draw.circle(s, (255, 255, 240, 255), (cx, cy), size // 9)
            # Tiny dark crescent for that cartoon "shaded" look
            pygame.draw.circle(s, (180,  20,  10, 120),
                               (cx + size//8, cy + size//8), size // 7)
            return s
        self.fireBossBall = _redFireball()
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
        self._bigMummy_alert_shown = False
        self._bigMummy_first_hit = False
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
        self._konami_unlocked = False
        self._konami_seq = []
        self._word_buffer = ''
        self._word_bear_unlocked = False
        self._word_dash_unlocked = False
        self._word_jump_unlocked = False
        self._rainbow_trail = []
        self._confetti_particles = []
        self._xp_popups = []
        self._rainbow_tick = 0
        self._combo_master_unlocked = False
        self._lucky_100_unlocked = False
        self._no_hit_run = True
        self._untouchable_unlocked = False
        self._jungle_unlocked = False
        self._monkey_level_active = False
        self._jungle_zone2_active = False
        self._triggerJungleTransition = False
        self._triggerNewGamePlus = False
        self._intro_shown = False
        self._100_coin_milestone = False
        self._last_coin_milestone = 0
        self._first_coin_popup_shown = False
        self._shop_afford_hinted = False
        self._shop_free_voucher_used = False
        self._shop_low_hp_hinted = False
        self._beam_uses_total = 0
        self._kills_since_beam_use = 0
        self.boot_pickups = []
        self._boots_spawned = False
        self._zone_min_distance = 0
        self._last_zone_idx = 0
        self._zone_lock_toasted = False
        self._zone_wall_world_x = -10000
        self._head_alerts = []
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
        self._bomb_wave_30 = False; self._bomb_wave_60 = False
        self._bomb_gauntlet_started = False
        self._bomb_gauntlet_active = False
        self._bomb_gauntlet_timer = 0
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

    def _update_and_draw_bear_trail(self, bear):
        """Render a rainbow afterimage trail behind the bear whenever it
        moves (walking, sliding, jumping, etc).  Unlocks at level 5;
        length scales 3% per level beyond that."""
        try:
            if bear.getLevel() < 5:
                return
        except Exception:
            return
        if not hasattr(bear, '_move_trail'):
            bear._move_trail = []
            bear._last_trail_x = bear.getXPosition()
            bear._last_trail_y = bear.getYPosition()
        _bx = bear.getXPosition(); _by = bear.getYPosition()
        _moved = (abs(_bx - bear._last_trail_x) > 0.5 or
                  abs(_by - bear._last_trail_y) > 0.5)
        if _moved:
            bear._move_trail.append((_bx, _by))
        else:
            # Bear is standing still — let the trail decay so it disappears.
            if bear._move_trail:
                bear._move_trail.pop(0)
        bear._last_trail_x = _bx; bear._last_trail_y = _by
        try:
            _lvl = bear.getLevel()
        except Exception:
            _lvl = 0
        _max_len = max(8, int(round(16 * (1 + 0.03 * _lvl))))
        if len(bear._move_trail) > _max_len:
            bear._move_trail = bear._move_trail[-_max_len:]
        if not bear._move_trail:
            return
        _rainbow = [
            (255, 60,  60),
            (255, 150, 50),
            (255, 230, 60),
            (80,  220, 90),
            (60,  160, 255),
            (160, 80,  220),
        ]
        _n = len(bear._move_trail)
        for _i, (_tx, _ty) in enumerate(bear._move_trail[:-1]):
            _frac = (_i + 1) / _n
            _alpha = int(200 * _frac)
            _radius = max(5, int(20 * _frac))
            _col = _rainbow[_i % len(_rainbow)]
            _gs = pygame.Surface((_radius * 2, _radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(_gs, (*_col, _alpha),
                               (_radius, _radius), _radius)
            pygame.draw.circle(_gs, (255, 255, 255, min(255, _alpha + 40)),
                               (_radius, _radius), max(1, _radius // 3))
            # Center the circle on the bear's torso area
            self.screen.blit(_gs, (_tx + 60 - _radius, _ty + 60 - _radius))

    def _draw_idle_bear(self, bear):
        if getattr(self, '_death_anim_frame', -1) >= 0:
            return
        if getattr(bear, 'slide_frames', 0) > 0:
            return
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
        if hurtTimer > 75 or hurtTimer < 0:
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
        bear._mmx_jump_sound = getattr(self, 'mmx_jump_sound', None)
        bear._mmx_jump_sound_alt = getattr(self, 'mmx_jump_sound_alt', None)
        bear._mmx_land_sound = getattr(self, 'mmx_land_sound', None)
        bear._mmx_dash_sound = getattr(self, 'mmx_dash_sound', None)
        bear._mmx_powerup_sound = getattr(self, 'mmx_powerup_sound', None)
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
                            _dmg = self._roll_attack_bonus(bear.getDamageAttack())
                            enemy.setDamageReceived(_dmg)
                            enemy.setStunned(1)
                            enemy.setHealth(enemy.getHealth() - _apply_defense(enemy, _dmg))

            for enemy in [monkey, lion]:
                if hasattr(enemy, 'getHealth') and enemy.getHealth() > 0:
                    er = pygame.Rect(enemy.getXPosition(), enemy.getYPosition(),
                                     enemy.width, enemy.height)
                    br = pygame.Rect(bear.getXPosition(), bear.getYPosition(), 100, 100)
                    if er.colliderect(br) and hurtTimer > 75:
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

            # Spookier title backdrop: deep blood-purple gradient + drifting fog
            self.screen.fill((14, 6, 20))
            # Vertical gradient (top deep purple → bottom near-black)
            for _gy in range(0, 700, 4):
                _gt = _gy / 700.0
                _gr = int(20 - _gt * 12)
                _gg = int(8 - _gt * 5)
                _gb = int(28 - _gt * 18)
                pygame.draw.rect(self.screen,
                                 (max(0, _gr), max(0, _gg), max(0, _gb)),
                                 (0, _gy, 900, 4))

            # Drifting fog bands
            _t_titlefog = anim_tick * 0.012
            for _fi in range(8):
                _fx = int((140 * _fi + math.sin(_t_titlefog + _fi) * 100) % 1100) - 100
                _fy = 80 + _fi * 80 + int(math.sin(_t_titlefog * 1.4 + _fi) * 22)
                _fa = 35 + int(18 * math.sin(_t_titlefog * 2.1 + _fi))
                _fog_s = pygame.Surface((320, 80), pygame.SRCALPHA)
                pygame.draw.ellipse(_fog_s,
                                    (90, 60, 130, _fa),
                                    (0, 0, 320, 80))
                self.screen.blit(_fog_s, (_fx, _fy))

            for sp in _sparkles:
                sp['y'] -= sp['speed']
                if sp['y'] < -5:
                    sp['y'] = 710
                    sp['x'] = random.randint(0, 900)
                twinkle = abs(((anim_tick + sp['phase']) % 120) / 60.0 - 1.0)
                brightness = int(100 + 155 * twinkle)
                # Greenish-white spook stars instead of cool-blue
                color = (int(brightness * 0.7), brightness, int(brightness * 0.6))
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

        _sel_text = "NORMAL" if selected == 0 else "HARD"
        _sel_color = (100, 220, 140) if selected == 0 else (255, 80, 80)
        _effect_font = pygame.font.SysFont(None, 72, bold=True)
        _effect_len = 50
        _particles = []
        for _pi in range(30):
            _angle = random.uniform(0, 2 * math.pi)
            _spd = random.uniform(2.0, 6.0)
            _particles.append({
                'x': 450.0, 'y': 400.0,
                'vx': math.cos(_angle) * _spd,
                'vy': math.sin(_angle) * _spd,
                'life': random.randint(25, 50),
                'size': random.randint(3, 8),
                'color': (min(255, _sel_color[0] + random.randint(-30, 60)),
                          min(255, _sel_color[1] + random.randint(-30, 60)),
                          min(255, _sel_color[2] + random.randint(-30, 60)))
            })

        for _ef in range(_effect_len):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return None
            self.screen.fill((10, 8, 20))

            _progress = _ef / float(_effect_len)
            _scale = 0.3 + _progress * 0.7 if _ef < 15 else 1.0
            _font_size = max(20, int(72 * _scale))
            _dyn_font = pygame.font.SysFont(None, _font_size, bold=True)
            _flash = max(0, 1.0 - _ef / 10.0)
            _r = min(255, int(_sel_color[0] + 155 * _flash))
            _g = min(255, int(_sel_color[1] + 155 * _flash))
            _b = min(255, int(_sel_color[2] + 155 * _flash))
            _txt_s = _dyn_font.render(_sel_text, True, (_r, _g, _b))
            _txt_x = 450 - _txt_s.get_width() // 2
            _txt_y = 340 - _txt_s.get_height() // 2

            if _ef < 8:
                _glow_size = int(120 + 40 * (1.0 - _ef / 8.0))
                _glow_s = pygame.Surface((_glow_size * 2, _glow_size * 2), pygame.SRCALPHA)
                _glow_alpha = int(180 * (1.0 - _ef / 8.0))
                pygame.draw.circle(_glow_s, (_sel_color[0], _sel_color[1], _sel_color[2], _glow_alpha),
                                   (_glow_size, _glow_size), _glow_size)
                self.screen.blit(_glow_s, (450 - _glow_size, 340 - _glow_size))

            for _p in _particles:
                if _p['life'] > 0:
                    _p['x'] += _p['vx']
                    _p['y'] += _p['vy']
                    _p['vy'] += 0.1
                    _p['life'] -= 1
                    _pa = min(255, _p['life'] * 8)
                    _ps = pygame.Surface((_p['size'] * 2, _p['size'] * 2), pygame.SRCALPHA)
                    pygame.draw.circle(_ps, (_p['color'][0], _p['color'][1], _p['color'][2], _pa),
                                       (_p['size'], _p['size']), _p['size'])
                    self.screen.blit(_ps, (int(_p['x']) - _p['size'], int(_p['y']) - _p['size']))

            self.screen.blit(_txt_s, (_txt_x, _txt_y))

            if _ef > 5:
                _sub_font = pygame.font.SysFont(None, 24)
                _sub_alpha = min(255, (_ef - 5) * 12)
                _sub_s = _sub_font.render("Get ready...", True, (180, 170, 200))
                _sub_s.set_alpha(_sub_alpha)
                self.screen.blit(_sub_s, (450 - _sub_s.get_width() // 2, 390))

            pygame.display.update()
            clock.tick(60)

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
        SpikeBlock._bear_ref = bear
        # Reset spike sprite cache so the new procedural design is used
        if hasattr(SpikeBlock, '_cached_sprite'):
            try: del SpikeBlock._cached_sprite
            except Exception: pass
        # Cheat-code buffer for "777" -> god mode
        self._cheat_seq = []
        bear.grunt_sound = self.grunt_sound
        bear.jump_scream_sound = getattr(self, 'jump_scream_sound', None)
        bear._mmx_jump_sound = getattr(self, 'mmx_jump_sound', None)
        bear._mmx_jump_sound_alt = getattr(self, 'mmx_jump_sound_alt', None)
        bear._mmx_land_sound = getattr(self, 'mmx_land_sound', None)
        bear._mmx_dash_sound = getattr(self, 'mmx_dash_sound', None)
        bear._mmx_powerup_sound = getattr(self, 'mmx_powerup_sound', None)
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
        # Per-zone HP scaling: each new zone bumps remaining monsters' HP by 15%
        self._zone_count = 0
        self._prev_active_zones = 0

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

        # Intro welcome toast removed — controls are shown as floating text
        # at the bottom of the screen during the READY phase below.
        if not self._intro_shown:
            self._intro_shown = True

        for mummy in self.mummys:
            mummy.setStunned(0)
        for witch in self.witches:
            witch.setStunned(0)
        self.door = []
        self.spikes = []

        triggerWitchFireBallAnimation = 0

        # Kick off the slow drum layer so it plays from the very start.
        try:
            self._update_bonus_instrument_layer(self._current_music)
        except Exception:
            pass

        # ----- "READY" + persistent controls strip (always visible) ---------
        if not getattr(self, '_ready_banner_shown', False):
            self._ready_banner_shown = True
            self._i_press_count = 0
            self._percent_show_until = 0
            self._hud_total_distance = 60
            self._hud_total_max = 56500
            _orig_flip = pygame.display.flip
            _orig_update = pygame.display.update
            _ready_state = {'timer': 180, 'frame': 0}
            _BRIGHT_FRAMES = 900  # 15 s at 60 fps – ultra-visible intro

            def _draw_overlay():
                _ready_state['frame'] += 1
                _ff = _ready_state['frame']
                # ---------- READY banner (first 180 frames only) ----------
                if _ready_state['timer'] > 0:
                    _f = 180 - _ready_state['timer']
                    _font_main = pygame.font.SysFont(None, 36, bold=True)
                    _pulse = 1.0 + 0.18 * math.sin(_f * 0.30)
                    _g = max(180, min(255, int(220 * _pulse)))
                    _txt = _font_main.render('READY!', True, (255, _g, 120))
                    _sh  = _font_main.render('READY!', True, (0, 0, 0))
                    _cx = (900 - _txt.get_width()) // 2
                    self.screen.blit(_sh, (_cx + 2, 10))
                    self.screen.blit(_txt, (_cx, 8))
                    _ready_state['timer'] -= 1
                # ---------- Controls strip (always visible at bottom) -----
                _bright = _ff < _BRIGHT_FRAMES
                if _bright:
                    _font_info = pygame.font.SysFont(None, 26, bold=True)
                    _bg_alpha = 200
                    _txt_col = (255, 255, 200)
                    _pulse = 0.6 + 0.4 * abs(math.sin(_ff * 0.08))
                    _border_col = (255, int(220 * _pulse), 80)
                    _border_w = 3
                else:
                    _font_info = pygame.font.SysFont(None, 18, bold=True)
                    _bg_alpha = 130
                    _txt_col = (235, 235, 245)
                    _border_col = (90, 90, 120)
                    _border_w = 1
                _info_lines = [
                    'Z: Attack    X: Fireball    SPACE: Jump    DOWN+SPACE: Slide',
                    'ENTER: Shop    P: Pause/Menu    I (x3): Show Progress %',
                ]
                _line_h = _font_info.get_height() + 2
                _strip_h = _line_h * len(_info_lines) + 10
                _strip_y = 700 - _strip_h - 4
                _strip = pygame.Surface((900, _strip_h), pygame.SRCALPHA)
                _strip.fill((10, 10, 25, _bg_alpha))
                self.screen.blit(_strip, (0, _strip_y))
                pygame.draw.rect(self.screen, _border_col,
                                 (0, _strip_y, 900, _strip_h), _border_w)
                _y = _strip_y + 5
                for _line in _info_lines:
                    _ts = _font_info.render(_line, True, _txt_col)
                    _sx = _font_info.render(_line, True, (0, 0, 0))
                    _ix = (900 - _ts.get_width()) // 2
                    self.screen.blit(_sx, (_ix + 1, _y + 1))
                    self.screen.blit(_ts, (_ix, _y))
                    _y += _line_h
                # ---------- Progress percentage popup (when triggered) ----
                if pygame.time.get_ticks() < self._percent_show_until:
                    _td = max(0, getattr(self, '_hud_total_distance', 60) - 60)
                    _tm = max(1, self._hud_total_max - 60)
                    _pct = max(0, min(100, int(_td * 100 / _tm)))
                    _pf = pygame.font.SysFont(None, 56, bold=True)
                    _pt = _pf.render(f'PROGRESS: {_pct}%', True, (255, 240, 120))
                    _ps = _pf.render(f'PROGRESS: {_pct}%', True, (0, 0, 0))
                    _px = (900 - _pt.get_width()) // 2
                    _py = 320
                    _box = pygame.Surface((_pt.get_width() + 40, _pt.get_height() + 20), pygame.SRCALPHA)
                    _box.fill((10, 10, 30, 220))
                    self.screen.blit(_box, (_px - 20, _py - 10))
                    pygame.draw.rect(self.screen, (255, 220, 100),
                                     (_px - 20, _py - 10, _pt.get_width() + 40, _pt.get_height() + 20), 3)
                    self.screen.blit(_ps, (_px + 2, _py + 2))
                    self.screen.blit(_pt, (_px, _py))

            def _wrap_flip(*a, **kw):
                _draw_overlay()
                return _orig_flip(*a, **kw)

            def _wrap_update(*a, **kw):
                _draw_overlay()
                return _orig_update(*a, **kw)

            pygame.display.flip = _wrap_flip
            pygame.display.update = _wrap_update

        # ===================================================================
        # Main game loop
        # ===================================================================
        while continueLoop:
            # --- Handle window close event ---------------------------------
            if self._paused:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        return
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_p:
                            self._paused = False
                            if not self._muted:
                                pygame.mixer.unpause()
                        elif event.key == pygame.K_m:
                            self._muted = not self._muted
                            if self._muted:
                                pygame.mixer.pause()
                            else:
                                pygame.mixer.unpause()
                if self._paused_snapshot is not None:
                    self.screen.blit(self._paused_snapshot, (0, 0))
                # Spookier pause: dim + green vignette tint + drifting fog
                _pov = pygame.Surface((900, 700), pygame.SRCALPHA)
                _pov.fill((10, 5, 20, 200))
                self.screen.blit(_pov, (0, 0))
                # Drifting smoky fog ovals
                _t_fog = pygame.time.get_ticks() * 0.0006
                for _fi in range(7):
                    _fx = int((150 * _fi + math.sin(_t_fog + _fi) * 80) % 1000) - 50
                    _fy = 140 + _fi * 70 + int(math.sin(_t_fog * 1.3 + _fi) * 18)
                    _fa = 55 + int(20 * math.sin(_t_fog * 2 + _fi))
                    _fog_s = pygame.Surface((280, 90), pygame.SRCALPHA)
                    pygame.draw.ellipse(_fog_s,
                                        (140, 200, 160, _fa),
                                        (0, 0, 280, 90))
                    self.screen.blit(_fog_s, (_fx, _fy))
                # Eerie green-cyan flicker title
                _pf_big = pygame.font.SysFont(None, 130, bold=True)
                _pf_sub = pygame.font.SysFont(None, 30, bold=True)
                _flicker = 1.0 + 0.15 * math.sin(pygame.time.get_ticks() * 0.04)
                _gv = max(120, min(255, int(200 * _flicker)))
                _pcol = (180, _gv, 140)
                _ptxt = _pf_big.render('PAUSED', True, _pcol)
                _shadow = _pf_big.render('PAUSED', True, (0, 0, 0))
                _glow = _pf_big.render('PAUSED', True, (40, 220, 120))
                # Thick black outline
                for _po_x, _po_y in [(-3,-3),(-3,3),(3,-3),(3,3),(-4,0),(4,0),(0,-4),(0,4)]:
                    self.screen.blit(_shadow, (450 - _ptxt.get_width()//2 + _po_x, 240 + _po_y))
                # Green outer glow
                _glow.set_alpha(120)
                for _go_x, _go_y in [(-2,0),(2,0),(0,-2),(0,2)]:
                    self.screen.blit(_glow, (450 - _ptxt.get_width()//2 + _go_x, 240 + _go_y))
                # Chromatic split (red/cyan)
                _pred = _pf_big.render('PAUSED', True, (220, 50, 70))
                _pcyan = _pf_big.render('PAUSED', True, (60, 220, 220))
                _pred.set_alpha(160); _pcyan.set_alpha(160)
                self.screen.blit(_pred, (450 - _ptxt.get_width()//2 - 4, 240))
                self.screen.blit(_pcyan, (450 - _ptxt.get_width()//2 + 4, 240))
                self.screen.blit(_ptxt, (450 - _ptxt.get_width() // 2, 240))
                # Subtitle with creepy bracketing
                _sub_text = ('[ Press P to awaken    M to ' +
                             ('unmute' if self._muted else 'silence') + ' ]')
                _stxt = _pf_sub.render(_sub_text, True, (180, 220, 200))
                _sshadow = _pf_sub.render(_sub_text, True, (0, 0, 0))
                self.screen.blit(_sshadow, (450 - _stxt.get_width()//2 + 2, 392))
                self.screen.blit(_stxt, (450 - _stxt.get_width() // 2, 390))
                pygame.display.flip()
                self.clock.tick(60)
                continue
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                # ─── QoL: auto-pause when window loses focus ───
                if (event.type == getattr(pygame, 'WINDOWFOCUSLOST', -999)
                        or (event.type == pygame.ACTIVEEVENT
                            and getattr(event, 'gain', 1) == 0
                            and getattr(event, 'state', 0) & 2)):
                    if not getattr(self, '_paused', False) and not shop_open:
                        self._paused = True
                        try:
                            self._paused_snapshot = self.screen.copy()
                        except Exception:
                            self._paused_snapshot = None
                        try:
                            pygame.mixer.pause()
                        except Exception:
                            pass
                        continue
                if event.type == pygame.KEYDOWN:
                    _kk = event.key
                    # ----- 777 god-mode cheat -------------------------------
                    if _kk == pygame.K_7:
                        self._cheat_seq.append('7')
                        if len(self._cheat_seq) > 5:
                            self._cheat_seq = self._cheat_seq[-5:]
                        if not getattr(bear, '_god_mode', False) and ''.join(self._cheat_seq[-3:]) == '777':
                            bear._god_mode = True
                            bear.setHp(bear.getMaxHp())
                            bear.setDamageAttack(9999)
                            try:
                                bear.fireballDamage = 9999
                            except Exception:
                                pass
                            self._push_toast('GOD MODE ACTIVATED - UNLIMITED HEALTH + 9999 ATK', duration=300, color=(255, 220, 100))
                    else:
                        # Reset cheat buffer on any non-7 keypress so '777' must be consecutive
                        self._cheat_seq = []
                    _ksym = None
                    if _kk == pygame.K_UP: _ksym = 'U'
                    elif _kk == pygame.K_DOWN: _ksym = 'D'
                    elif _kk == pygame.K_LEFT: _ksym = 'L'
                    elif _kk == pygame.K_RIGHT: _ksym = 'R'
                    elif _kk == pygame.K_b: _ksym = 'B'
                    elif _kk == pygame.K_a: _ksym = 'A'
                    if _ksym is not None:
                        self._konami_seq.append(_ksym)
                        if len(self._konami_seq) > 10:
                            self._konami_seq = self._konami_seq[-10:]
                        if (not self._konami_unlocked
                                and ''.join(self._konami_seq[-10:]) == 'UUDDLRLRBA'):
                            self._konami_unlocked = True
                            bear.setMaxHp(bear.getMaxHp() + 25)
                            bear.setHp(bear.getMaxHp())
                            bear.setCoins(bear.getCoins() + 30)
                            if getattr(self, 'mmx_life_up_sound', None):
                                try: self.mmx_life_up_sound.play()
                                except Exception: pass
                            self._push_toast('\u2605 KONAMI! +25 MAX HP, full heal, +30 coins! \u2605', duration=300, color=(255, 215, 0))
                            self._push_toast('Bear Form: Awakened.', duration=240, color=(255, 180, 220))
                            if getattr(self, 'level_up_sound', None):
                                try: self.level_up_sound.play()
                                except Exception: pass
                            if getattr(self, 'mmx_powerup_sound', None):
                                try: self.mmx_powerup_sound.play()
                                except Exception: pass

                    _letter_map = {
                        pygame.K_a: 'A', pygame.K_b: 'B', pygame.K_d: 'D',
                        pygame.K_e: 'E', pygame.K_h: 'H', pygame.K_j: 'J',
                        pygame.K_m: 'M', pygame.K_n: 'N', pygame.K_p: 'P',
                        pygame.K_r: 'R', pygame.K_s: 'S', pygame.K_t: 'T',
                        pygame.K_u: 'U',
                    }
                    _letter = _letter_map.get(event.key)
                    if _letter is not None:
                        self._word_buffer = (self._word_buffer + _letter)[-12:]
                        if (not self._word_bear_unlocked
                                and self._word_buffer.endswith('BEAR')):
                            self._word_bear_unlocked = True
                            bear.setMaxHp(bear.getMaxHp() + 10)
                            bear.setHp(bear.getMaxHp())
                            bear.setCoins(bear.getCoins() + 50)
                            self._push_toast('\u2605 SECRET WORD: BEAR! +10 MAX HP, +50 coins \u2605',
                                             duration=300, color=(255, 200, 120))
                            if getattr(self, 'level_up_sound', None):
                                try: self.level_up_sound.play()
                                except Exception: pass
                            if getattr(self, 'mmx_powerup_sound', None):
                                try: self.mmx_powerup_sound.play()
                                except Exception: pass
                        if (not self._word_jump_unlocked
                                and self._word_buffer.endswith('JUMP')):
                            self._word_jump_unlocked = True
                            bear.setMaxHp(bear.getMaxHp() + 15)
                            bear.setHp(bear.getMaxHp())
                            self._push_toast('\u2605 SECRET WORD: JUMP! +15 MAX HP \u2605',
                                             duration=300, color=(180, 255, 220))
                            if getattr(self, 'level_up_sound', None):
                                try: self.level_up_sound.play()
                                except Exception: pass
                            if getattr(self, 'mmx_powerup_sound', None):
                                try: self.mmx_powerup_sound.play()
                                except Exception: pass
                    if event.key == pygame.K_i:
                        _now_ms = pygame.time.get_ticks()
                        if _now_ms - getattr(self, '_i_last_press_ms', 0) > 1500:
                            self._i_press_count = 0
                        self._i_last_press_ms = _now_ms
                        self._i_press_count = getattr(self, '_i_press_count', 0) + 1
                        if self._i_press_count >= 3:
                            self._i_press_count = 0
                            self._percent_show_until = _now_ms + 2500
                    if event.key == pygame.K_p and not shop_open:
                        self._paused = True
                        try:
                            self._paused_snapshot = self.screen.copy()
                        except Exception:
                            self._paused_snapshot = None
                        _pause_cue_idx = -1
                        if getattr(self, 'mmx_pause_sound', None):
                            try:
                                _nch_total = pygame.mixer.get_num_channels()
                                for _ci_try in range(_nch_total):
                                    _ch_try = pygame.mixer.Channel(_ci_try)
                                    if not _ch_try.get_busy():
                                        _ch_try.play(self.mmx_pause_sound)
                                        _pause_cue_idx = _ci_try
                                        break
                            except Exception:
                                _pause_cue_idx = -1
                        try:
                            _nch = pygame.mixer.get_num_channels()
                            for _ci in range(_nch):
                                if _ci == _pause_cue_idx:
                                    continue
                                pygame.mixer.Channel(_ci).pause()
                        except Exception:
                            pygame.mixer.pause()
                        continue
                    elif event.key == pygame.K_m:
                        self._muted = not self._muted
                        if self._muted:
                            pygame.mixer.pause()
                            self._push_toast('Sound muted (M to unmute)', duration=180, color=(220, 220, 240))
                        else:
                            pygame.mixer.unpause()
                            self._push_toast('Sound on', duration=120, color=(200, 255, 200))
                        continue
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
                            if shop_selection != _prev_sel and getattr(self, 'mmx_select_sound', None):
                                try: self.mmx_select_sound.play()
                                except Exception: pass
                        elif event.key == pygame.K_DOWN:
                            _prev_sel = shop_selection
                            shop_selection = min(max(len(shop_items) - 1, 0), shop_selection + 1)
                            if shop_selection != _prev_sel and self.shop_navigate_sound: self.shop_navigate_sound.play()
                            if shop_selection != _prev_sel and getattr(self, 'mmx_select_sound', None):
                                try: self.mmx_select_sound.play()
                                except Exception: pass
                        elif event.key == pygame.K_x:
                            if shop_selection < len(shop_items):
                                item_type, cost = shop_items[shop_selection]
                                msg = _buy_msgs.get(item_type, 'Purchased!')
                                _is_free_voucher = (not self._shop_free_voucher_used)
                                _effective_cost = 0 if _is_free_voucher else cost
                                if bear.getCoins() >= _effective_cost:
                                    bear.setCoins(bear.getCoins() - _effective_cost)
                                    if _is_free_voucher:
                                        self._shop_free_voucher_used = True
                                        self._push_toast('FREE GIFT used! Welcome to the Bear Shop!',
                                                         duration=300, color=(255, 220, 120))
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
                                        self._push_toast('\u26A1 Lightning bought! Press UP+A to strike', duration=300, color=(255, 245, 140))
                                        self._push_toast('It stuns enemies and chains damage', duration=300, color=(220, 220, 255))
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
                                        self._push_toast('\u26A1 Lightning 2 bought! UP+A fires 3 bolts \u26A1', duration=300, color=(255, 245, 140))
                                        self._push_toast('Triple chain damage upgrade unlocked', duration=300, color=(220, 220, 255))
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
                                    if getattr(self, 'mmx_powerup_sound', None):
                                        try: self.mmx_powerup_sound.play()
                                        except Exception: pass
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

                _recommended_idx = -1
                if shop_items:
                    _hp_low = bear.getHp() < bear.getMaxHp() * 0.50
                    if _hp_low:
                        for _i, _it in enumerate(shop_items):
                            if _it[0] == 'health':
                                _recommended_idx = _i
                                break
                    if _recommended_idx < 0:
                        _affordable_non_health = [(_i, _it) for _i, _it in enumerate(shop_items)
                                                  if _it[0] != 'health' and bear.getCoins() >= _it[1]]
                        if _affordable_non_health:
                            _recommended_idx = max(_affordable_non_health, key=lambda p: p[1][1])[0]
                        else:
                            _unowned_perm = [(_i, _it) for _i, _it in enumerate(shop_items) if _it[0] != 'health']
                            if _unowned_perm:
                                _recommended_idx = min(_unowned_perm, key=lambda p: p[1][1])[0]

                _left_x = panel.x + 20
                _item_w = panel.width - 40
                _row_h = 48
                _cat_h = 24
                _cur_y = panel.y + 38

                if not self._shop_free_voucher_used and shop_items:
                    _gift_rect = pygame.Rect(_left_x, _cur_y, _item_w, 30)
                    _gift_pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
                    _gift_bg = (180 + int(_gift_pulse * 40), 80 + int(_gift_pulse * 40), 30)
                    pygame.draw.rect(self.screen, _gift_bg, _gift_rect, border_radius=8)
                    pygame.draw.rect(self.screen, (255, 235, 120), _gift_rect, 2, border_radius=8)
                    _gift_text = 'FIRST PURCHASE IS FREE! Pick anything below.'
                    _gs = _FONT_HUD_LABEL.render(_gift_text, True, (255, 250, 200))
                    self.screen.blit(_gs, (_gift_rect.x + (_item_w - _gs.get_width()) // 2, _gift_rect.y + 4))
                    _cur_y += 36

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
                    _afford = bear.getCoins() >= cost
                    _row_rect = pygame.Rect(_left_x, _cur_y, _item_w, _row_h)
                    if _sel:
                        _pulse = int(abs(math.sin(pygame.time.get_ticks() * 0.005)) * 20)
                        if _afford:
                            _bg = (40 + _pulse, 80 + _pulse // 2, 50 + _pulse)
                            _border = (140, 255, 170)
                        else:
                            _bg = (60 + _pulse, 38 + _pulse // 2, 110 + _pulse)
                            _border = (220, 180, 255)
                        pygame.draw.rect(self.screen, _bg, _row_rect, border_radius=10)
                        pygame.draw.rect(self.screen, _border, _row_rect, 2, border_radius=10)
                        _arrow_x = _left_x + 6
                        _arrow_y = _cur_y + _row_h // 2
                        pygame.draw.polygon(self.screen, (255, 220, 100),
                                            [(_arrow_x, _arrow_y - 5), (_arrow_x + 8, _arrow_y), (_arrow_x, _arrow_y + 5)])
                    else:
                        if _afford:
                            pygame.draw.rect(self.screen, (24, 44, 30), _row_rect, border_radius=10)
                            pygame.draw.rect(self.screen, (90, 160, 110), _row_rect, 1, border_radius=10)
                        else:
                            pygame.draw.rect(self.screen, (30, 20, 55), _row_rect, border_radius=10)
                            pygame.draw.rect(self.screen, (70, 55, 100), _row_rect, 1, border_radius=10)
                    if _afford:
                        _check_x = _left_x + _item_w - 16
                        _check_y = _cur_y + _row_h - 12
                        pygame.draw.circle(self.screen, (90, 220, 120), (_check_x, _check_y), 6)
                        pygame.draw.lines(self.screen, (20, 40, 25), False,
                                          [(_check_x - 3, _check_y), (_check_x - 1, _check_y + 2), (_check_x + 3, _check_y - 2)], 2)

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

                    if not self._shop_free_voucher_used:
                        _free_pulse = abs(math.sin(pygame.time.get_ticks() * 0.008))
                        _free_col = (255, 230 + int(_free_pulse * 25), 120)
                        _cost_str = 'FREE'
                        _cost_surf = _FONT_HUD_LABEL.render(_cost_str, True, _free_col)
                        _cost_x = _left_x + _item_w - _cost_surf.get_width() - 30
                        self.screen.blit(_cost_surf, (_cost_x, _cur_y + 8))
                    else:
                        _cost_str = f'{cost}'
                        _cost_surf = _FONT_HUD_LABEL.render(_cost_str, True, (255, 230, 80) if _sel else (200, 180, 60))
                        _cost_x = _left_x + _item_w - _cost_surf.get_width() - 30
                        self.screen.blit(_cost_surf, (_cost_x, _cur_y + 8))
                        _coin_r = 8
                        _coin_cx = _cost_x + _cost_surf.get_width() + 14
                        _coin_cy = _cur_y + 16
                        pygame.draw.circle(self.screen, (255, 215, 0), (_coin_cx, _coin_cy), _coin_r)
                        pygame.draw.circle(self.screen, (255, 245, 130), (_coin_cx, _coin_cy), 4)

                    if idx == _recommended_idx:
                        _rec_pulse = abs(math.sin(pygame.time.get_ticks() * 0.006))
                        _rec_col = (255, 200 + int(_rec_pulse * 55), 80)
                        _rec_surf = _FONT_HUD_VAL.render('* PICK ME *', True, _rec_col)
                        _rec_x = _left_x + _item_w - _rec_surf.get_width() - 8
                        self.screen.blit(_rec_surf, (_rec_x, _cur_y + 30))

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

            self._hud_total_distance = totalDistance
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
            bear._speed_lerp += (_target_step - bear._speed_lerp) * 0.22
            STEP = max(1, int(round(bear._speed_lerp)))
            # ---- Easy start: halve HP of the first 4 enemies a player sees ----
            if getattr(self, '_easy_start_remaining', 0) > 0:
                _easy_lists = (self.mummys, self.witches, self.greenBlobs,
                               self.shadowShamans, self.miniFrankenBears,
                               self.snakes, self.monkey_mummies, self.lions)
                for _elist in _easy_lists:
                    for _enemy in _elist:
                        if self._easy_start_remaining <= 0:
                            break
                        if getattr(_enemy, '_easy_applied', False):
                            continue
                        # Skip bosses / minibosses
                        _name = getattr(_enemy, 'getName', lambda: '')()
                        if _name in ('bigMummy', 'frankenBear'):
                            _enemy._easy_applied = True
                            continue
                        # Mummies: -50% HP. Other enemies: -75% HP.
                        _is_mummy = isinstance(_enemy, Mummy)
                        _factor = 0.5 if _is_mummy else 0.25
                        for _attr in ('hp', 'health'):
                            if hasattr(_enemy, _attr):
                                try:
                                    _v = getattr(_enemy, _attr)
                                    if isinstance(_v, (int, float)) and _v > 1:
                                        setattr(_enemy, _attr, max(1, int(_v * _factor)))
                                except Exception:
                                    pass
                        _enemy._easy_applied = True
                        self._easy_start_remaining -= 1
                    if self._easy_start_remaining <= 0:
                        break

            # ---- Deferred slide-hint after big-mummy kill ----
            if getattr(self, '_slide_hint_pending', 0) > 0:
                self._slide_hint_pending -= 1
                if self._slide_hint_pending == 0:
                    if not hasattr(self, '_head_alerts') or self._head_alerts is None:
                        self._head_alerts = []
                    self._head_alerts.append({
                        'text': 'TO SLIDE: PRESS SPACE  or  TAP RIGHT-RIGHT FAST',
                        'life': 480,
                        'max_life': 480,
                        'color': (120, 220, 255),
                        'tag': 'slide_hint'})

            # ---- Per-zone HP scaling: +15% per new zone for new monsters ----
            try:
                # Only main-path zones contribute (skip jungle [3]-when-monkey,
                # and the FrankenBear boss arena [9]).
                _MAIN_ZONES = (11, 1, 14, 10, 3, 2, 13, 4, 12, 5, 6, 7, 8, 15)
                _now_active = sum(1 for _i in _MAIN_ZONES if self.activeMonsters[_i])
                # If jungle (monkey level) currently owns flag [3], don't count it
                if getattr(self, '_monkey_level_active', False) and self.activeMonsters[3]:
                    _now_active -= 1
                _prev = getattr(self, '_prev_active_zones', 0)
                if _now_active > _prev:
                    self._zone_count = getattr(self, '_zone_count', 0) + (_now_active - _prev)
                    self._prev_active_zones = _now_active
                    # ── NG+: occasionally drop a wild lion or monkey on each new zone ──
                    if getattr(self, 'newGamePlusLevel', 0) >= 1:
                        try:
                            _spawn_x = random.randint(1100, 2400)
                            _ms = getattr(self, 'monkey_screech_sound', None)
                            _lr = getattr(self, 'lion_roar_sound', None)
                            if random.random() < 0.55:
                                self.monkey_mummies.append(MonkeyMummy(
                                    _spawn_x, 220, 180, 180,
                                    self.mummy1, self.mummy2, self.screen, _ms))
                            if random.random() < 0.45:
                                self.lions.append(Lion(
                                    random.randint(1100, 2400), 230,
                                    self.screen, _lr))
                        except Exception:
                            pass
                # Scale HP for any newly-spawned monster that isn't an easy-start one
                _zc = getattr(self, '_zone_count', 0)
                if _zc > 0:
                    # Smart scaling — anchored to player level, NOT compounded
                    # per zone (which would balloon to ~2x by the final zone).
                    # The "effective zones" = how deep we are, but capped at
                    # player_level + 1 so under-leveled players don't get
                    # crushed. Each effective zone adds a flat 8%.
                    try:
                        _plvl = bear.getLevel()
                    except Exception:
                        _plvl = 1
                    _eff = min(_zc, _plvl + 1)
                    if _plvl >= _zc + 2:
                        _per_zone = 0.10     # over-leveled: faster ramp
                    elif _plvl >= _zc:
                        _per_zone = 0.08     # on pace: moderate
                    else:
                        _per_zone = 0.05     # behind: very gentle
                    # Linear scaling, capped so the late game stays fair.
                    _mult = 1.0 + _per_zone * _eff
                    _mult = min(_mult, 1.0 + 0.10 * max(1, _plvl))
                    for _elist in (self.mummys, self.witches, self.greenBlobs,
                                   self.shadowShamans, self.miniFrankenBears,
                                   self.snakes, self.monkey_mummies, self.lions):
                        for _enemy in _elist:
                            if getattr(_enemy, '_zone_scaled', False):
                                continue
                            if getattr(_enemy, '_easy_applied', False):
                                _enemy._zone_scaled = True
                                continue
                            _name = getattr(_enemy, 'getName', lambda: '')()
                            if _name in ('bigMummy', 'frankenBear'):
                                _enemy._zone_scaled = True
                                continue
                            for _attr in ('hp', 'health', 'max_health'):
                                if hasattr(_enemy, _attr):
                                    try:
                                        _v = getattr(_enemy, _attr)
                                        if isinstance(_v, (int, float)) and _v > 0:
                                            setattr(_enemy, _attr, max(1, int(_v * _mult)))
                                    except Exception:
                                        pass
                            _enemy._zone_scaled = True
            except Exception:
                pass

            # ---- Slide trigger (SPACE held = continuous, or double-tap LR/RR) ----
            keys_slide = pygame.key.get_pressed()
            _space_now = keys_slide[pygame.K_SPACE]
            _space_prev = getattr(self, '_space_was_held', False)
            self._space_was_held = _space_now
            _right_now = keys_slide[pygame.K_RIGHT]
            _left_now = keys_slide[pygame.K_LEFT]
            _right_prev = getattr(self, '_right_was_held', False)
            _left_prev = getattr(self, '_left_was_held', False)
            self._right_was_held = _right_now
            self._left_was_held = _left_now
            # Double-tap detection (within ~18 frames / 0.3s)
            self._right_tap_window = max(0, getattr(self, '_right_tap_window', 0) - 1)
            self._left_tap_window = max(0, getattr(self, '_left_tap_window', 0) - 1)
            _double_tap_right = False
            _double_tap_left = False
            if _right_now and not _right_prev:
                if self._right_tap_window > 0:
                    _double_tap_right = True
                    self._right_tap_window = 0
                else:
                    self._right_tap_window = 18
            if _left_now and not _left_prev:
                if self._left_tap_window > 0:
                    _double_tap_left = True
                    self._left_tap_window = 0
                else:
                    self._left_tap_window = 18
            _on_ground_slide = (not bear.getJumpStatus() and not bear.getLeftJumpStatus())
            # Continuous slide while SPACE is held: re-trigger as soon as cooldown
            # expires (no need to release/repress). Also trigger via double-tap.
            _slide_trigger = ((_space_now and _on_ground_slide
                               and bear.slide_frames == 0 and bear.slide_cooldown == 0)
                              or (_double_tap_right and _on_ground_slide
                                  and bear.slide_frames == 0 and bear.slide_cooldown == 0)
                              or (_double_tap_left and _on_ground_slide
                                  and bear.slide_frames == 0 and bear.slide_cooldown == 0))
            if _slide_trigger:
                if _double_tap_right:
                    bear.slide_dir = 1
                elif _double_tap_left:
                    bear.slide_dir = -1
                elif keys_slide[pygame.K_LEFT]:
                    bear.slide_dir = -1
                elif keys_slide[pygame.K_RIGHT]:
                    bear.slide_dir = 1
                else:
                    bear.slide_dir = -1 if bear.getLeftDirection() else 1
                bear.setLeftDirection(bear.slide_dir < 0)
                bear.slide_frames = 22
                # Shorter cooldown when SPACE is held so it chains smoothly
                bear.slide_cooldown = 14 if _space_now else 36
                if getattr(self, 'slide_scrape_sound', None):
                    try: self.slide_scrape_sound.play()
                    except Exception: pass
                elif getattr(self, 'mmx_dash_sound', None):
                    try: self.mmx_dash_sound.play()
                    except Exception: pass
            if bear.slide_cooldown > 0:
                bear.slide_cooldown -= 1
            if bear.slide_frames > 0:
                bear.slide_frames -= 1
                STEP = max(STEP, 14)
                # Force the LR key in the slide direction so the existing
                # movement code carries the bear forward.
                class _SlideKeysWrapper:
                    def __init__(self, k, d):
                        self._k = k; self._d = d
                    def __getitem__(self, key):
                        if self._d > 0 and key == pygame.K_RIGHT: return True
                        if self._d < 0 and key == pygame.K_LEFT: return True
                        if self._d > 0 and key == pygame.K_LEFT: return False
                        if self._d < 0 and key == pygame.K_RIGHT: return False
                        return self._k[key]
                # Override pygame.key.get_pressed temporarily
                if not hasattr(self, '_orig_keys_get_pressed'):
                    self._orig_keys_get_pressed = pygame.key.get_pressed
                _real_keys = self._orig_keys_get_pressed()
                pygame.key.get_pressed = lambda w=_SlideKeysWrapper(_real_keys, bear.slide_dir): w
                # Slide+Jump: pressing Z during slide → jump with EXTRA momentum
                # Each consecutive slide-jump (chained while still airborne or
                # within 30 frames of landing) builds extra carry, capped.
                if keys_slide[pygame.K_z] and _on_ground_slide:
                    _chain = getattr(bear, 'slide_jump_chain', 0)
                    bear.slide_jump_chain = min(_chain + 1, 5)
                    # Base 50 frames + up to +25 from chain bonus
                    bear.slide_jump_carry = 50 + bear.slide_jump_chain * 5
                    bear.slide_jump_dir = bear.slide_dir
                    bear.slide_jump_speed = 8 + bear.slide_jump_chain  # 9..13 px/frame
                    bear.slide_chain_grace = 30
                    bear.slide_frames = 0
                    pygame.key.get_pressed = self._orig_keys_get_pressed
            else:
                if hasattr(self, '_orig_keys_get_pressed'):
                    pygame.key.get_pressed = self._orig_keys_get_pressed
            # Apply slide-jump horizontal carry while airborne
            if bear.slide_jump_carry > 0 and (bear.getJumpStatus() or bear.getLeftJumpStatus()):
                _carry_step = getattr(bear, 'slide_jump_speed', 8)
                _new_x = bear.getXPosition() + bear.slide_jump_dir * _carry_step
                _new_x = max(0, min(800, _new_x))
                bear.setXPosition(_new_x)
                bear.slide_jump_carry -= 1
            elif _on_ground_slide:
                bear.slide_jump_carry = 0
            # Track grace window for chaining slide-jumps
            if _on_ground_slide:
                _grace = getattr(bear, 'slide_chain_grace', 0)
                if _grace > 0:
                    bear.slide_chain_grace = _grace - 1
                    if bear.slide_chain_grace == 0:
                        bear.slide_jump_chain = 0
                elif getattr(bear, 'slide_jump_chain', 0) > 0 and bear.slide_frames == 0:
                    # Reset chain only after a full landed beat with no slide
                    bear.slide_jump_chain = 0

            # ─── QoL: slide cooldown indicator under the bear ───
            if (bear.slide_cooldown > 0 and bear.slide_frames == 0
                    and not _popup_active):
                _cd_max = 36
                _cd_pct = max(0.0, min(1.0, bear.slide_cooldown / _cd_max))
                _bar_w = 40
                _bar_h = 4
                _bar_x = bear.getXPosition() + 50 - _bar_w // 2
                _bar_y = bear.getYPosition() + 122
                pygame.draw.rect(self.screen, (30, 30, 30),
                                 (_bar_x - 1, _bar_y - 1, _bar_w + 2, _bar_h + 2))
                pygame.draw.rect(self.screen, (60, 60, 80),
                                 (_bar_x, _bar_y, _bar_w, _bar_h))
                _fill_w = int(_bar_w * (1.0 - _cd_pct))
                if _fill_w > 0:
                    pygame.draw.rect(self.screen, (120, 220, 255),
                                     (_bar_x, _bar_y, _fill_w, _bar_h))

            _cur_zone_idx = min(2, max(0, totalDistance // 4500))
            if _cur_zone_idx > self._last_zone_idx:
                self._last_zone_idx = _cur_zone_idx
                self._zone_min_distance = max(self._zone_min_distance, _cur_zone_idx * 4500)
                self._zone_lock_toasted = False
                # Plant the wall just behind the player at the moment the zone
                # locks, so it's visible on screen briefly then scrolls offscreen.
                self._zone_wall_world_x = totalDistance - 220
            if (totalDistance > self._zone_min_distance + 60
                    and totalDistance <= self._zone_min_distance + 90
                    and not self._zone_lock_toasted):
                self._zone_lock_toasted = True
                self._push_toast('Zone barrier sealed! No turning back.',
                                 duration=240, color=(220, 200, 255))

            _on_ground = (not bear.getJumpStatus() and not bear.getLeftJumpStatus())
            bear.update_coyote(_on_ground)
            bear.tick_jump_buffer()

            if bear.getEndText():

                keys = pygame.key.get_pressed()
                if (self._zone_wall_world_x > -9000
                        and totalDistance <= self._zone_wall_world_x):
                    class _ZoneLeftLock:
                        def __init__(self, k): self._k = k
                        def __getitem__(self, key):
                            if key == pygame.K_LEFT: return False
                            return self._k[key]
                        def __len__(self): return len(self._k)
                    keys = _ZoneLeftLock(keys)

                # ---- X: throw fireball at full health --------------------
                playerFireCooldown = max(0, playerFireCooldown - 1)
                if (keys[pygame.K_x]
                        and not (keys[pygame.K_UP] and keys[pygame.K_a])
                        and not (keys[pygame.K_a] and keys[pygame.K_DOWN] and beamCharge >= 100.0 and beamCooldown == 0)
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
                    # Enable fiery trail; length grows 3% per bear level
                    self.playerFires[-1]._trail_enabled = True
                    self.playerFires[-1]._trail_max_len = max(3, int(round(8 * (1 + 0.03 * bear.getLevel()))))
                    if getattr(self, 'mmx_lemon_shot_sound', None):
                        try: self.mmx_lemon_shot_sound.play()
                        except Exception: pass
                    if getattr(bear, 'has_big_fireball', False):
                        self.playerFires[-1].damageAttack = int(self.playerFires[-1].damageAttack * 1.2)
                    if self.fire_sound:
                        self.fire_sound.play()
                    attackingAnimationCounter = 1

                # ---- C: beam super attack ---------------------------------
                beamCooldown = max(0, beamCooldown - 1)
                beamCharge = min(100.0, beamCharge + 0.10 * getattr(self, '_ng_beam_mult', 1.0))
                if beamCharge >= 100.0 and not beamReadyPopupShown:
                    beamReadyPopupShown = True
                    self._beam_ever_shown = True
                    _show_beam_hint = (self._beam_uses_total == 0 or self._kills_since_beam_use >= 10)
                    if _show_beam_hint:
                        self._push_toast('\u26A1 BEAM READY! Press A+DOWN \u26A1', duration=240, color=(180, 255, 220))
                        bear._level_up_float = 210
                        bear._level_up_float_max = 210
                        bear._level_up_text = 'BEAM READY! PRESS A + DOWN'
                        self._kills_since_beam_use = 0
                _beam_combo = (keys[pygame.K_a] and keys[pygame.K_DOWN])
                if (keys[pygame.K_c] or _beam_combo) and beamCharge >= 100.0 and beamCooldown == 0:
                    beamCharge = 0.0
                    beamCooldown = 60
                    beamReadyPopupShown = False
                    self._beam_uses_total += 1
                    self._kills_since_beam_use = 0
                    _beam_dmg = self._roll_attack_bonus(bear.getDamageAttack()) * 4
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
                    if getattr(self, 'mmx_charged_shot_sound', None):
                        self.mmx_charged_shot_sound.play()
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
                elif (keys[pygame.K_DOWN]
                      and not keys[pygame.K_a]
                      and not bear.getJumpStatus()
                      and not bear.getLeftJumpStatus()
                      and bear.getYPosition() + 100 >= 400):
                    bear.set_crouch(True)
                elif keys[pygame.K_d] and self.weapon_cooldown > 0:
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
                        bear_top = bear.getYPosition()
                        bear_feet = bear.getYPosition() + 100
                        for blk in self.blocks:
                            if blk is ignore:
                                continue
                            blk_top = blk.getBlockYPosition()
                            blk_bottom = blk_top + blk.getHeight()
                            # Skip overhead platforms (bear can pass under)
                            if blk_bottom <= bear_top + 10:
                                continue
                            # Skip blocks the bear can step onto
                            if blk_top > bear_feet - 10:
                                continue
                            if ((bear_right + STEP) >= blk.getBlockXPosition()
                                    and bear_right < blk.getBlockXPosition() + blk.getWidth()
                                    and blk_bottom >= 380):
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
                        _plat_block = None
                        for block in self.blocks:
                            if block.getOnPlatform():
                                _plat_block = block
                                break
                        if bear.getXPosition() < self.rightBoundary:
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                            if _plat_block:
                                _plat_block.setIsLeftBoundary(False)
                                _plat_block.setIsRightBoundary(False)
                            if any(b.getIsLeftBoundary() for b in self.blocks):
                                totalDistance -= STEP
                                _jump_moved = False
                            if _jump_moved and _tall_wall_ahead(bear.getXPosition(), _plat_block):
                                totalDistance -= STEP
                                _jump_moved = False
                            backgroundScrollX = bear.getXPosition() - STEP
                            background.setXPosition(backgroundScrollX)
                            if _jump_moved:
                                bear.setXPosition(bear.getXPosition() + STEP)
                        else:
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                            if _plat_block:
                                _plat_block.setIsLeftBoundary(False)
                                _plat_block.setIsRightBoundary(False)
                            if (any(b.getIsLeftBoundary() for b in self.blocks)
                                    or _tall_wall_ahead(bear.getXPosition(), _plat_block)):
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
                                            monster.getName()) and hurtTimer > 75):
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
                                                monster.getName()) and hurtTimer > 75):
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
                            _base_dmg = self._roll_attack_bonus(bear.getDamageAttack())
                            _is_crit = random.random() < 0.20
                            _dmg = _base_dmg * 2 if _is_crit else _base_dmg
                            if monster.getName() == "bigMummy":
                                if is_monster_forehead_hit(bear.getXPosition(), bear.getYPosition(),
                                                        monster.getXPosition(), monster.getYPosition(),
                                                        bear.getLeftDirection()):
                                    monster.setDamageReceived(_dmg)
                                    monster.setStunned(1)
                                    monster.setHealth(monster.getHealth() - _apply_defense(monster, _dmg))
                                    self._bigMummy_first_hit = True
                                    self._head_alerts = [
                                        _ha for _ha in getattr(self, '_head_alerts', [])
                                        if _ha.get('tag') != 'bigmummy']
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
                            _base_dmg = self._roll_attack_bonus(bear.getDamageAttack())
                            _is_crit = random.random() < 0.20
                            _dmg = _base_dmg * 2 if _is_crit else _base_dmg
                            if monster.getName() == "bigMummy":
                                if is_monster_forehead_hit(bear.getXPosition(), bear.getYPosition(),
                                                        monster.getXPosition(), monster.getYPosition(),
                                                        bear.getLeftDirection()):
                                    monster.setDamageReceived(_dmg)
                                    monster.setStunned(1)
                                    monster.setHealth(monster.getHealth() - _apply_defense(monster, _dmg))
                                    self._bigMummy_first_hit = True
                                    self._head_alerts = [
                                        _ha for _ha in getattr(self, '_head_alerts', [])
                                        if _ha.get('tag') != 'bigmummy']
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

                        if bear.slide_frames == 0:
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
                                                monster.getName()) and hurtTimer > 75):
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

                        if bear.slide_frames == 0:
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
                                                monster.getName()) and hurtTimer > 75):
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
                                    self._bigMummy_first_hit = True
                                    self._head_alerts = [
                                        _ha for _ha in getattr(self, '_head_alerts', [])
                                        if _ha.get('tag') != 'bigmummy']
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
                                            monster.getName()) and hurtTimer > 75):
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

            # ---- Movement rainbow trail (always-on while moving) -----------
            self._update_and_draw_bear_trail(bear)

            # ---- Slide pose (Mega-Man-X style) ---------------------------------
            if bear.slide_frames <= 0 and getattr(bear, '_slide_trail', None):
                bear._slide_trail = []  # reset between slides
            if bear.slide_frames > 0:
                # Floor anchor: bottom of standing sprite = bear.y + 115
                _attack_h = self.bearAttacking.get_height()  # 105
                # Sit attack sprite flush with the floor (its bottom = standing bottom)
                _slide_y = bear.getYPosition() + 115 - _attack_h
                _slide_x = bear.getXPosition() - (90 if bear.slide_dir < 0 else 0)
                # ----- Rainbow slide trail (length scales 3% per level) -----
                if not hasattr(bear, '_slide_trail'):
                    bear._slide_trail = []
                bear._slide_trail.append((bear.getXPosition(), bear.getYPosition()))
                _slide_max = max(6, int(round(12 * (1 + 0.03 * bear.getLevel()))))
                if len(bear._slide_trail) > _slide_max:
                    bear._slide_trail = bear._slide_trail[-_slide_max:]
                _rainbow = [
                    (255, 60,  60),   # red
                    (255, 150, 50),   # orange
                    (255, 230, 60),   # yellow
                    (80,  220, 90),   # green
                    (60,  160, 255),  # blue
                    (160, 80,  220),  # purple
                ]
                _n = len(bear._slide_trail)
                for _i, (_tx, _ty) in enumerate(bear._slide_trail[:-1]):
                    _frac = (_i + 1) / _n
                    _alpha = int(220 * _frac)
                    _radius = max(4, int(22 * _frac))
                    _col = _rainbow[_i % len(_rainbow)]
                    _gs = pygame.Surface((_radius * 2, _radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(_gs, (*_col, _alpha),
                                       (_radius, _radius), _radius)
                    pygame.draw.circle(_gs, (255, 255, 255, min(255, _alpha + 30)),
                                       (_radius, _radius), max(1, _radius // 3))
                    self.screen.blit(_gs, (_tx + 50 - _radius,
                                           _ty + 80 - _radius))
                if bear.slide_dir < 0:
                    self.screen.blit(self.bearAttackingLeft, (_slide_x, _slide_y))
                else:
                    self.screen.blit(self.bearAttacking, (_slide_x, _slide_y))
                # dust puffs behind the slide
                for _i in range(3):
                    _dx = bear.getXPosition() + (50 - bear.slide_dir * (20 + _i * 8))
                    _dy = bear.getYPosition() + 110 + _i * 2
                    pygame.draw.circle(self.screen, (220, 210, 190),
                                       (int(_dx), int(_dy)), 6 - _i)
            # ---- Attack animation (always runs, fixes 1-frame flicker gap) ------
            elif 1 <= attackingAnimationCounter < 12:
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
                            'Press "d" to unleash the shockwave.',
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
                        # Roll for a "fancy" death (~30%) — different sound + visual.
                        # Bosses always use their normal big explosion.
                        if not hasattr(monster, '_fancy_death'):
                            monster._fancy_death = (
                                monster.getName() != "bigMummy"
                                and random.random() < 0.30)
                        if getattr(self, 'enemy_hit_sound', None):
                            self.enemy_hit_sound.play()
                        if monster._fancy_death:
                            _bang = getattr(self, 'fancy_death_bang_sound', None)
                            if _bang:
                                try: _bang.play()
                                except Exception: pass
                        else:
                            if getattr(self, 'mmx_enemy_explode_sound', None):
                                try: self.mmx_enemy_explode_sound.play()
                                except Exception: pass
                    if monster.getDestructionAnimationCount() == 5:
                        _is_boss_monster = monster.getName() == "bigMummy"
                        if _is_boss_monster and getattr(self, 'boss_explosion_sound', None):
                            self.boss_explosion_sound.play()
                        elif getattr(monster, '_fancy_death', False):
                            pass
                        elif self.explosion_sound:
                            self.explosion_sound.play()
                    # ---- Fancy-death visual: expanding sparkle ring ----
                    if getattr(monster, '_fancy_death', False):
                        try:
                            _dc = monster.getDestructionAnimationCount()
                            _cx = monster.getXPosition() + 50
                            _cy = monster.getYPosition() + 50
                            # 2 expanding rings + center burst
                            _r1 = 12 + _dc * 6
                            _r2 = 4 + _dc * 4
                            _alpha = max(0, 220 - _dc * 8)
                            _ring = pygame.Surface((_r1*2+8, _r1*2+8), pygame.SRCALPHA)
                            pygame.draw.circle(_ring, (255, 120, 220, _alpha),
                                               (_r1+4, _r1+4), _r1, 3)
                            pygame.draw.circle(_ring, (180, 240, 255, _alpha),
                                               (_r1+4, _r1+4), _r2, 2)
                            self.screen.blit(_ring, (_cx - _r1 - 4, _cy - _r1 - 4))
                            # Sparkle particles (deterministic per monster)
                            _seed = id(monster) & 0xFFFF
                            for _i in range(6):
                                _ang = ((_seed >> _i) & 0xFF) / 255.0 * 6.28318
                                _spd = 4 + ((_seed >> (_i+3)) & 0x7)
                                _px = _cx + int(math.cos(_ang) * _dc * _spd)
                                _py = _cy + int(math.sin(_ang) * _dc * _spd)
                                _pc = (255, 240, 120) if _i % 2 == 0 else (180, 255, 240)
                                pygame.draw.circle(self.screen, _pc, (_px, _py), max(1, 4 - _dc // 6))
                        except Exception:
                            pass
                    _death_dmg = monster.getDamageReceived() if monster.getDamageReceived() > 0 else bear.getDamageAttack()
                    monster.drawDestruction(_death_dmg) if hasattr(monster, 'drawDestruction') else None
                    _destroy_limit = 60 if monster.getName() == "bigMummy" else 30
                    if monster.getDestructionAnimationCount() >= _destroy_limit:
                        monster.setStartDestructionAnimation(False)
                        _base_exp = monster.getExp()
                        _hard_mult = 1.50 if self._hardMode else 1.0
                        _combo_cap = 0.7 if self._hardMode else 1.0
                        _combo_step = 0.07 if self._hardMode else 0.10
                        _raw_combo_mult = 1.0 + min(_combo_cap, max(0, self._combo) * _combo_step)
                        _stacked = _hard_mult * _raw_combo_mult
                        if _stacked > 1.0:
                            _soft_mult = 1.0 + (_stacked - 1.0) ** 0.65
                        else:
                            _soft_mult = _stacked
                        _grind_bonus = 1.0
                        if max(0, self._combo) <= 1 and self.newGamePlusLevel == 0 and not self._hardMode:
                            _grind_bonus = 1.0 + min(0.50, self._kill_total / 250.0)
                        _exp_gain = max(1, int(round(_base_exp * _soft_mult * _grind_bonus)))
                        bear.setCurrentExp(bear.getCurrentExp() + _exp_gain)
                        try:
                            if self._combo >= 3 and _soft_mult > 1.15:
                                _pop_color = (255, 230, 140)
                            elif _grind_bonus > 1.05:
                                _pop_color = (180, 255, 200)
                            else:
                                _pop_color = (255, 245, 140)
                            _pop_x = int(monster.getXPosition() + 40)
                            _pop_y = int(monster.getYPosition() - 10)
                            # Show base xp + the combo bonus separately so the
                            # player sees exactly how much extra they earned.
                            # Baseline = what they'd get with NO combo bonus
                            # (still includes hard-mode and grind multipliers).
                            _baseline_stacked = _hard_mult * _grind_bonus
                            if _baseline_stacked > 1.0:
                                _baseline_soft = 1.0 + (_baseline_stacked - 1.0) ** 0.65
                            else:
                                _baseline_soft = _baseline_stacked
                            _baseline_xp = max(1, int(round(_base_exp * _baseline_soft)))
                            _bonus_xp = max(0, _exp_gain - _baseline_xp)
                            _txt = '+%d' % _exp_gain
                            self._xp_popups.append([float(_pop_x), float(_pop_y),
                                                    _txt, _pop_color, 70])
                            # Stash combo bonus info for the upper-right HUD
                            if self._combo >= 3 and _bonus_xp > 0:
                                self._combo_bonus_display = {
                                    'bonus': _bonus_xp,
                                    'combo': max(1, self._combo + 1),
                                    'frames': 90,
                                }
                        except Exception:
                            pass
                        to_remove.append(monster)

            for monster in to_remove:
                self._combo += 1
                self._kill_total += 1
                self._kills_since_beam_use += 1
                try:
                    self._spawn_confetti(int(monster.getXPosition() + 40),
                                         int(monster.getYPosition() + 40))
                except Exception:
                    pass
                self._combo_timer = 150
                if self._combo > self._combo_max_session:
                    self._combo_max_session = self._combo
                if getattr(monster, '_elite', False):
                    bear.setCoins(bear.getCoins() + 5)
                    self._push_toast('\u2728 ELITE KILL! +5 coins \u2728', duration=120, color=(255, 215, 0))
                if random.random() < getattr(self, '_ng_lucky_drop_chance', 0.0):
                    self.coins.append(Coin(int(monster.getXPosition() + 40), int(monster.getYPosition()), self.screen))
                if self._combo >= 30 and not self._combo_master_unlocked:
                    self._combo_master_unlocked = True
                    bear.setMaxHp(bear.getMaxHp() + 15)
                    bear.setHp(bear.getMaxHp())
                    self._push_toast('\U0001F525 COMBO MASTER! 30-kill streak! \U0001F525', duration=300, color=(255, 100, 200))
                    self._push_toast('+15 Max HP permanently. Full heal!', duration=240, color=(255, 230, 140))
                    if getattr(self, 'level_up_sound', None):
                        try: self.level_up_sound.play()
                        except Exception: pass
                _hp_ratio = bear.getHp() / max(1, bear.getMaxHp())
                if self._hardMode:
                    _heart_chance = 0.65 if _hp_ratio < 0.15 else (0.40 if _hp_ratio < 0.30 else (0.22 if _hp_ratio < 0.50 else 0.08))
                else:
                    _heart_chance = 0.85 if _hp_ratio < 0.15 else (0.60 if _hp_ratio < 0.30 else (0.40 if _hp_ratio < 0.50 else 0.18))
                if random.random() < _heart_chance:
                    # After 50% of the run, hearts have a chance to be SUPER hearts.
                    _heal_amt = 25
                    if totalDistance >= 28250:
                        _hr = random.random()
                        if _hr < 0.05:
                            _heal_amt = 150
                        elif _hr < 0.35:
                            _heal_amt = 100
                        elif _hr < 0.70:
                            _heal_amt = 75
                    self.heart_drops.append({
                        'x': float(monster.getXPosition() + 40),
                        'y': float(monster.getYPosition()),
                        'vy': -2.0, 'landed': False, 'life': 420,
                        'heal': _heal_amt,
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
                    for _ci in range(6):
                        self.coins.append(Coin(monster.getXPosition() + 10 + _ci * 16,
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
                    self._bigMummy_first_hit = True
                    self._head_alerts = [
                        _ha for _ha in getattr(self, '_head_alerts', [])
                        if _ha.get('tag') != 'bigmummy']
                    # Delay the slide-tutorial popup so the player can savor
                    # the kill before another tip pops up (~3s).
                    self._slide_hint_pending = 180
                    # Silence music until the player passes through the door
                    try:
                        pygame.mixer.music.fadeout(800)
                    except Exception:
                        pass
                    self._current_music = None
                    self._post_mummy_silence = True

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
                            and hurtTimer > 75):
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
                    if not getattr(self, '_boss_kill_no_hit_locked', False):
                        self._boss_kill_no_hit_snapshot = not getattr(self, '_boss_hit_taken', False)
                        self._boss_kill_no_hit_locked = True
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
                        if (getattr(self, '_boss_kill_no_hit_snapshot', False)
                                and not getattr(self, '_untouchable_unlocked', False)):
                            self._untouchable_unlocked = True
                            bear.setMaxHp(bear.getMaxHp() + 30)
                            bear.setHp(bear.getMaxHp())
                            bear.setDamageAttack(bear.getDamageAttack() + 5)
                            self._push_toast('\U0001F396 UNTOUCHABLE! No-hit boss kill! \U0001F396', duration=360, color=(180, 240, 255))
                            self._push_toast('+30 Max HP, +5 attack damage permanently!', duration=300, color=(255, 230, 140))
                            if getattr(self, 'level_up_sound', None):
                                try: self.level_up_sound.play()
                                except Exception: pass
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
                if getattr(coin, 'landed', False):
                    _ccx = coin.getXPosition() + 15
                    _ccy = coin.getYPosition() + 15
                    _bcx = bear.getXPosition() + 50
                    _bcy = bear.getYPosition() + 50
                    _cdx = _bcx - _ccx
                    _cdy = _bcy - _ccy
                    _cdist = (_cdx * _cdx + _cdy * _cdy) ** 0.5
                    if _cdist < 140 and _cdist > 1:
                        _cpull = 0.5 + (140 - _cdist) * 0.06
                        coin.setXPosition(coin.getXPosition() + (_cdx / _cdist) * _cpull)
                coin.draw()
                if coin.is_grabbed(bear.getXPosition(), bear.getYPosition()):
                    coins_to_remove.append(coin)
                    bear.setCoins(bear.getCoins() + 1)
                    if getattr(self, 'coin_sound', None):
                        self.coin_sound.play()
                    _alt = getattr(self, 'mmx_coin_sound_alt', None)
                    if _alt and random.random() < 0.30:
                        _alt.play()
                    elif getattr(self, 'mmx_coin_sound', None):
                        self.mmx_coin_sound.play()
                    if bear.getCoins() >= 100 and not self._lucky_100_unlocked:
                        self._lucky_100_unlocked = True
                        bear.setCoins(bear.getCoins() + 50)
                        bear.setHp(min(bear.getMaxHp(), bear.getHp() + 30))
                        self._push_toast('\U0001F4B0 LUCKY 100! Bonus +50 coins & +30 HP! \U0001F4B0', duration=300, color=(255, 215, 0))
                        self._push_toast('Treasure hunter achievement unlocked.', duration=240, color=(220, 255, 220))
                        if getattr(self, 'level_up_sound', None):
                            try: self.level_up_sound.play()
                            except Exception: pass
                    if not self._first_coin_popup_shown:
                        self._first_coin_popup_shown = True
                        bear.setArrayText(['You got a coin!',
                                           'Press ENTER any time to',
                                           'open the BEAR SHOP and',
                                           'spend coins on upgrades!',
                                           'Press "s" to continue'])
                        bear.setEndText(False)
                    if (not self._shop_afford_hinted) and bear.getCoins() >= 30:
                        self._shop_afford_hinted = True
                        self._push_toast('You can afford an upgrade! Press ENTER for the Shop',
                                         duration=300, color=(180, 255, 180))
                        if getattr(self, 'shop_open_sound', None):
                            try: self.shop_open_sound.play()
                            except Exception: pass
            for coin in coins_to_remove:
                if coin in self.coins:
                    self.coins.remove(coin)

            # ---- Witch fireballs (safe iteration) -----------------------
            fires_to_remove = []
            for fire in self.fires:
                fire.drawFireBall()
                if getattr(fire, '_falling_only', False):
                    if getattr(fire, '_dead', False) or fire.getYPosition() > 700:
                        fires_to_remove.append(fire)
                    continue
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
                        _fb_dmg = self._roll_attack_bonus(bear.fireballDamage)
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
                    if lion_rect.colliderect(bear_rect_l) and hurtTimer > 75:
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
                        _fs = _fin_font.render('-4', True, (80, 230, 80))
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
                    if hurtTimer > 75:
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
                    if hurtTimer > 75:
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
                        if _pdist < 40 and hurtTimer > 75 and not _wb.get('hit', False):
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
                else:
                    _bcx = bear.getXPosition() + 50
                    _bcy = bear.getYPosition() + 50
                    _dx = _bcx - _hd['x']
                    _dy = _bcy - _hd['y']
                    _dist = (_dx * _dx + _dy * _dy) ** 0.5
                    if _dist < 160 and _dist > 1:
                        _pull = 0.6 + (160 - _dist) * 0.05
                        _hd['x'] += (_dx / _dist) * _pull
                        _hd['y'] += (_dy / _dist) * _pull
                _hd['life'] -= 1
                _hx, _hy = int(_hd['x']), int(_hd['y'])
                _hd_pulse = abs(math.sin(pygame.time.get_ticks() * 0.006)) * 4
                _hr = int(22 + _hd_pulse)
                _heart_s = pygame.Surface((_hr*2+6, _hr*2+6), pygame.SRCALPHA)
                _hcx, _hcy = _hr+3, _hr+3
                pygame.draw.circle(_heart_s, (255, 50, 80, 220), (_hcx - _hr//3, _hcy - _hr//4), _hr//2 + 2)
                pygame.draw.circle(_heart_s, (255, 50, 80, 220), (_hcx + _hr//3, _hcy - _hr//4), _hr//2 + 2)
                pygame.draw.polygon(_heart_s, (255, 50, 80, 220), [
                    (_hcx - _hr, _hcy - 1), (_hcx, _hcy + _hr), (_hcx + _hr, _hcy - 1)])
                _plus_font = pygame.font.SysFont(None, 28, bold=True)
                _heal_disp = _hd.get('heal', 25)
                _plus_txt = _plus_font.render('+' + str(_heal_disp), True, (255, 255, 255))
                _heart_s.blit(_plus_txt, (_hcx - _plus_txt.get_width()//2, _hcy - _plus_txt.get_height()//2 - 2))
                self.screen.blit(_heart_s, (_hx - _hcx, _hy - _hcy))
                if _hd['life'] <= 0:
                    _hd_remove.append(_hd)
                elif _hd['landed']:
                    _hd_rect = pygame.Rect(_hx - 15, _hy - 15, 30, 30)
                    if _hd_rect.colliderect(pygame.Rect(bear.getXPosition(), bear.getYPosition(), 100, 100)):
                        bear.setHp(min(bear.getMaxHp(), bear.getHp() + _hd.get('heal', 25)))
                        bear.setCoins(bear.getCoins() + 1)
                        if getattr(self, 'coin_sound', None):
                            self.coin_sound.play()
                        _alt = getattr(self, 'mmx_coin_sound_alt', None)
                        if _alt and random.random() < 0.30:
                            _alt.play()
                        elif getattr(self, 'mmx_coin_sound', None):
                            self.mmx_coin_sound.play()
                        _hd_remove.append(_hd)
            for _hd in _hd_remove:
                if _hd in self.heart_drops:
                    self.heart_drops.remove(_hd)

            if self._zone_min_distance > 0 and self._zone_wall_world_x > -9000:
                _wall_world_x = self._zone_wall_world_x
                _wall_screen_x = bear.getXPosition() - (totalDistance - _wall_world_x)
                if -60 < _wall_screen_x < 960:
                    _wall_pulse = abs(math.sin(pygame.time.get_ticks() * 0.003))
                    _wall_w = 28
                    _wall_top = 60
                    _wall_bot = 720
                    _wall_h = _wall_bot - _wall_top
                    _wx = int(_wall_screen_x)
                    pygame.draw.rect(self.screen, (90, 70, 60),
                                     (_wx, _wall_top, _wall_w, _wall_h))
                    for _by in range(_wall_top, _wall_bot, 32):
                        pygame.draw.rect(self.screen, (60, 45, 38),
                                         (_wx + 2, _by, _wall_w - 4, 28), 1)
                        pygame.draw.line(self.screen, (50, 38, 30),
                                         (_wx, _by), (_wx + _wall_w, _by), 1)
                    _glow_a = int(80 + _wall_pulse * 80)
                    _glow_s = pygame.Surface((44, _wall_h), pygame.SRCALPHA)
                    pygame.draw.rect(_glow_s, (180, 100, 200, _glow_a),
                                     (28, 0, 10, _wall_h))
                    self.screen.blit(_glow_s, (_wx, _wall_top))

            # ── BOMB GAUNTLET ZONE (7 000 – 9 500) ───────────────────────
            # Short, monster-free corridor: 1 bomb per second, dropping both
            # ahead AND behind the player, with platforms to dodge between.
            # Some bombs are RED INSTANT bombs that detonate the moment they land.
            if (not getattr(self, '_bomb_gauntlet_started', False)
                    and backgroundScrollX >= 7000):
                self._bomb_gauntlet_started = True
                self._bomb_gauntlet_active = True
                self._bomb_gauntlet_timer = 0
                self._bomb_gauntlet_alt = 0
                # NOTE: do NOT touch monster lists or activeMonsters here —
                # that interfered with normal zone/loading flow. Bombs only.
                # Add 4 dodge platforms in front of the player at varied heights
                _gp_specs = [
                    (300, 420, 110, 18),
                    (560, 340, 110, 18),
                    (820, 400, 110, 18),
                    (1080, 310, 110, 18),
                ]
                self._gauntlet_blocks = []
                for _gx, _gy, _gw, _gh in _gp_specs:
                    _gb = Block(_gx, _gy, _gw, _gh, "greyRock", self.screen)
                    self.blocks.append(_gb)
                    self._gauntlet_blocks.append(_gb)
                self._push_toast('\u2620 BOMB GAUNTLET! Dodge and slide! \u2620',
                                 duration=360, color=(255, 100, 60))
                self._push_toast('RED bombs explode INSTANTLY on landing!',
                                 duration=360, color=(255, 200, 80))
                if getattr(self, 'wave_warning_sound', None):
                    try: self.wave_warning_sound.play()
                    except Exception: pass

            if (getattr(self, '_bomb_gauntlet_active', False)
                    and backgroundScrollX >= 9500):
                self._bomb_gauntlet_active = False
                self._push_toast('Bomb gauntlet cleared!',
                                 duration=180, color=(120, 255, 160))

            if getattr(self, '_bomb_gauntlet_active', False) and not _popup_active:
                self._bomb_gauntlet_timer += 1
                # Faster cadence: 1 bomb every 0.4s (was 1.0s) — much harder to miss
                if self._bomb_gauntlet_timer >= 24:
                    self._bomb_gauntlet_timer = 0
                    import random as _bg_rand
                    _bear_gx = bear.getXPosition() + 50
                    # Alternate ahead / behind so bombs come from both sides
                    self._bomb_gauntlet_alt = 1 - self._bomb_gauntlet_alt
                    _side = 1 if self._bomb_gauntlet_alt == 0 else -1
                    # Tighter targeting: drop CLOSE to the player (within 30-130px)
                    _g_off = _bg_rand.randint(30, 130)
                    _gbx = max(40, min(860, _bear_gx + _side * _g_off))
                    _g_big = _bg_rand.random() < 0.25
                    # ~45% of gauntlet bombs detonate INSTANTLY on landing
                    _g_instant = _bg_rand.random() < 0.45
                    _g_secs = 0 if _g_instant else _bg_rand.choice([1, 1, 2])
                    self.bombs.append({
                        'x': float(_gbx), 'y': -40.0, 'vy': 4.5,
                        'landed': False, 'timer': _g_secs * 60,
                        'exploding': False, 'explode_anim': 0,
                        'big': _g_big, 'instant': _g_instant,
                    })

            # Removed legacy 30%/60% bomb wave bursts — they fired in zones
            # that aren't bomb zones, breaking the every-other-zone policy.

            # Every-other-zone bomb policy: each zone's [start, end) range
            # below is a "bomb zone". Scroll outside these ranges = no bombs.
            _BOMB_RANGES = (
                ( 5000,  8000),  # zone 1
                (11000, 14500),  # zone 3
                (18500, 22000),  # zone 5
                (22600, 24500),  # zone 6.5 (calm)
                (25500, 29000),  # zone 7
                (36500, 39500),  # zone 11
                (42000, 43500),  # quiet zone 2 (calm)
                (45000, 50500),  # zone 13
                (53500, 56500),  # zone 15
            )
            _is_bomb_zone = any(_lo <= totalDistance < _hi for _lo, _hi in _BOMB_RANGES)
            if not _popup_active and _is_bomb_zone:
                self._bomb_spawn_timer += 1
                # Calm zone gets more bombs, faster.
                _in_calm = ((getattr(self, '_calm_zone_active', False) and not getattr(self, '_calm_zone_exited', False)) or
                            (getattr(self, '_calm2_zone_active', False) and not getattr(self, '_calm2_zone_exited', False)))
                _bomb_interval = 220 if _in_calm else 420
                if self._bomb_spawn_timer >= _bomb_interval:
                    self._bomb_spawn_timer = 0
                    import random as _br
                    _bear_bx = bear.getXPosition() + 50
                    # Drop a small cluster, not just one
                    _cluster = _br.randint(2, 4) if _in_calm else _br.randint(1, 3)
                    for _ci in range(_cluster):
                        _bx = max(30, min(870, _bear_bx + _br.randint(-250, 500)))
                        _is_big = _br.random() < 0.25
                        _is_instant = _br.random() < 0.40
                        # Fewer "long fuse" bombs — most go off in 1s
                        _timer_secs = 0 if _is_instant else _br.choice([1, 1, 1, 2])
                        # Angled toss: random horizontal velocity ±
                        _vx = _br.uniform(-2.8, 2.8)
                        # Faster vertical drop
                        _vy = _br.uniform(5.5, 7.5)
                        self.bombs.append({
                            'x': float(_bx), 'y': -40.0 - _ci * 30,
                            'vx': _vx, 'vy': _vy,
                            'landed': False, 'timer': _timer_secs * 60,
                            'exploding': False, 'explode_anim': 0,
                            'big': _is_big, 'instant': _is_instant,
                        })

            # ── Falling fireballs — exclusive to Quiet Zone 2 ─────────────
            if (getattr(self, '_calm2_zone_active', False)
                    and not getattr(self, '_calm2_zone_exited', False)
                    and not _popup_active):
                self._calm2_fb_timer = getattr(self, '_calm2_fb_timer', 0) + 1
                if self._calm2_fb_timer >= 55:
                    self._calm2_fb_timer = 0
                    import random as _fr
                    _bear_fbx = bear.getXPosition() + 50
                    for _fi in range(_fr.randint(2, 3)):
                        _fbx = max(40, min(860, _bear_fbx + _fr.randint(-300, 400)))
                        _fb = FireBall(_fbx, -60, 0, _fr.uniform(7.0, 9.5),
                                       self.fireBall, self.screen, size=(60, 60))
                        try: _fb._falling_only = True
                        except Exception: pass
                        self.fires.append(_fb)

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
                        if _dist_b < _b_explode_radius and hurtTimer > 75:
                            _bomb_pct = 0.40 if _b_big else 0.30
                            _bomb_dmg = max(8, int(bear.getMaxHp() * _bomb_pct))
                            bear.applyDamage(_bomb_dmg)
                            bear.displayDamageOnBear(_bomb_dmg, "bomb")
                            hurtTimer = 0
                            if getattr(self, 'bear_hurt_sound', None):
                                self.bear_hurt_sound.play()
                else:
                    _bomb['y'] += _bomb['vy']
                    _bomb['vy'] += 0.28
                    _bomb['x'] += _bomb.get('vx', 0.0)
                    # Bounce off the screen edges so angled bombs stay in play
                    if _bomb['x'] < 20:
                        _bomb['x'] = 20.0
                        _bomb['vx'] = abs(_bomb.get('vx', 0.0)) * 0.7
                    elif _bomb['x'] > 880:
                        _bomb['x'] = 880.0
                        _bomb['vx'] = -abs(_bomb.get('vx', 0.0)) * 0.7
                    if _bomb['y'] >= 385:
                        _bomb['y'] = 385.0
                        _bomb['landed'] = True
                        _bomb['vy'] = 0.0
                        _bomb['vx'] = 0.0
                    _bx_i = int(_bomb['x'])
                    _by_i = int(_bomb['y'])
                    # ─── QoL: landing-shadow telegraph on the ground ───
                    # Pulsing red ring shows exactly where this bomb will land.
                    # Tighter/brighter as the bomb gets closer.
                    _gnd_y = 385
                    _falling_dist = max(1, _gnd_y - _by_i)
                    _proximity = 1.0 - min(1.0, _falling_dist / 400.0)  # 0 far, 1 near
                    _is_instant_b = _bomb.get('instant', False)
                    _shadow_r = int((26 if _b_big else 18) + 10 * (1 - _proximity))
                    _shadow_pulse = abs(math.sin(pygame.time.get_ticks() * 0.018))
                    _base_a = int(80 + 140 * _proximity)
                    _shadow_a = max(40, min(230, int(_base_a + _shadow_pulse * 50)))
                    _shadow_col = (255, 50, 50) if _is_instant_b else (255, 140, 40)
                    _shadow_surf = pygame.Surface((_shadow_r * 2 + 4, _shadow_r + 12),
                                                  pygame.SRCALPHA)
                    pygame.draw.ellipse(_shadow_surf,
                                        (*_shadow_col, _shadow_a),
                                        (0, 0, _shadow_r * 2, _shadow_r))
                    pygame.draw.ellipse(_shadow_surf,
                                        (*_shadow_col, min(255, _shadow_a + 60)),
                                        (4, 4, _shadow_r * 2 - 8, _shadow_r - 8), 2)
                    self.screen.blit(_shadow_surf,
                                     (_bx_i - _shadow_r, _gnd_y + 6))
                    _fall_r = 24 if _b_big else 16
                    _fall_inner = 18 if _b_big else 12
                    _fall_fuse = 6 if _b_big else 4
                    if _bomb.get('instant', False):
                        _flash_on = (pygame.time.get_ticks() // 60) % 2 == 0
                        _fall_col = (255, 40, 40) if _flash_on else (180, 0, 0)
                        _fall_inner_col = (255, 200, 60) if _flash_on else (255, 140, 30)
                    else:
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

            if (totalDistance > 29050 and not getattr(self, '_checkpoint_saved', False)
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

            if self.frankenbear:
                _prev_boss_hp = getattr(self, '_prev_bear_hp_boss', bear.getHp())
                if bear.getHp() < _prev_boss_hp:
                    self._boss_hit_taken = True
                self._prev_bear_hp_boss = bear.getHp()
            else:
                self._prev_bear_hp_boss = bear.getHp()
            _regen_threshold = 540 if self._hardMode else 360
            _regen_rate = 150 if self._hardMode else 75
            if hurtTimer > _regen_threshold and bear.getHp() < bear.getMaxHp() and bear.getHp() > 0:
                self._regen_tick = getattr(self, '_regen_tick', 0) + 1
                if self._regen_tick >= _regen_rate:
                    self._regen_tick = 0
                    bear.setHp(min(bear.getMaxHp(), bear.getHp() + 1))
            else:
                self._regen_tick = 0

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
                self._intro_banner = {'text': 'FRANKENBEAR', 'sub': 'final challenge', 'frames': 240, 'max': 240, 'color': (255, 130, 200)}
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
                if self.bossTimerAnimation == 31:
                    if getattr(self, 'mmx_boss_door_sound', None):
                        try: self.mmx_boss_door_sound.play()
                        except Exception: pass

                if self.bossTimerAnimation > 170:
                    if self.showBoss:
                        frankenbear = FrankenBear(1400, 20, self.screen)
                        self.frankenbear.append(frankenbear)
                        self._boss_hit_taken = False
                        self._boss_kill_no_hit_locked = False
                        self._boss_kill_no_hit_snapshot = False
                        self._prev_bear_hp_boss = bear.getHp()
                        self.showBoss = False
                        if self.boss_entrance_sound: self.boss_entrance_sound.play()
                    for frankenbear in self.frankenbear:
                        frankenbear._popup_frozen = _popup_active
                        frankenbear.drawMonster()
                        if not _popup_active and (frankenbear.getThrowFireBallLeft() or frankenbear.getThrowFireBallRight()):
                            frankenbear.setThrowFireBallLeft(False)
                            frankenbear.setThrowFireBallRight(False)
                            volley = 2 if getattr(self, '_hardMode', False) else 1
                            import math as _m
                            _fx = frankenbear.getXPosition() + 200
                            _fy = frankenbear.getYPosition() + 100
                            _bx = bear.getXPosition() + 50
                            _by = bear.getYPosition() + 50
                            _dx = _bx - _fx
                            _dy = _by - _fy
                            _dist = max(1, _m.sqrt(_dx*_dx + _dy*_dy))
                            for _ in range(volley):
                                _speed = random.uniform(2.5, 3.8)
                                _spread = random.uniform(-0.12, 0.12)
                                _vx = _speed * (_dx / _dist) + _spread * _speed
                                _vy_raw = _speed * (_dy / _dist)
                                _vy_raw = max(1, abs(_vy_raw)) * (1 if _dy > 0 else -1)
                                _bfb = FireBall(_fx, _fy,
                                             _vx,
                                             _vy_raw,
                                             self.fireBossBall, self.screen)
                                _bfb.damageAttack = max(3, int(bear.getMaxHp() * 0.04))
                                if getattr(self, '_hardMode', False):
                                    _bfb.damageAttack = int(_bfb.damageAttack * 1.5)
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

            # Critical: only fall if NO block currently supports the bear.
            # When walking across adjacent (e.g. stretched) platforms, the
            # block we just left briefly has dropStatus=True even while the
            # next block already has onPlatform=True. Falling in that frame
            # caused the bear to drop straight through stretched platforms.
            _any_support = any(b.getOnPlatform() for b in self.blocks)
            for block in self.blocks:
                # Skip drop gravity while jump physics are already controlling
                # vertical movement – double-falling causes the bear to blow
                # through landing windows and fall through platforms.
                if (block.getDropStatus() and not bear.getComingUp()
                        and not bear.getJumpStatus()
                        and not bear.getLeftJumpStatus()
                        and not _any_support):
                    if bear.getYPosition() + 100 < floorHeight:
                        bear.setYPosition(bear.getYPosition() + JUMP_STEP)
                    elif bear.getYPosition() + 100 >= floorHeight:
                        bear.setYPosition(floorHeight - 100)
                        block.setDropStatus(False)
                        block.setOnPlatform(False)
                        bear.setJumpStatus(False)
                        bear.setLeftJumpStatus(False)
                elif (block.getDropStatus() and _any_support
                        and not bear.getJumpStatus()
                        and not bear.getLeftJumpStatus()):
                    block.setDropStatus(False)

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

            # ── Big Mummy boss bar — top-of-screen forefront UI ──────────────
            _bm_ref = None
            for _mu in self.mummys:
                try:
                    if _mu.getName() == "bigMummy" and _mu.getHp() > 0:
                        _bm_ref = _mu; break
                except Exception:
                    pass
            if _bm_ref is not None:
                _bw = 720; _bh = 26
                _bx = (900 - _bw) // 2
                _by = 40
                _maxhp = max(1, getattr(_bm_ref, 'max_health', getattr(_bm_ref, 'health', 1)))
                _hp = max(0, getattr(_bm_ref, 'health', _maxhp))
                # NG+ buffs raise current health above the originally-stored
                # max_health — keep the bar in sync rather than overflowing.
                if _hp > _maxhp:
                    _maxhp = _hp
                    try: _bm_ref.max_health = _hp
                    except Exception: pass
                _frac = max(0.0, min(1.0, _hp / _maxhp))
                # Outer frame + dark fill
                pygame.draw.rect(self.screen, (0, 0, 0), (_bx - 4, _by - 4, _bw + 8, _bh + 8), border_radius=6)
                pygame.draw.rect(self.screen, (40, 0, 0), (_bx, _by, _bw, _bh), border_radius=4)
                # HP fill — pulsing crimson with hot orange tip
                _pulse = 0.85 + 0.15 * math.sin(pygame.time.get_ticks() * 0.006)
                _r = int(220 * _pulse); _g = int(40 + 60 * (1 - _frac))
                pygame.draw.rect(self.screen, (_r, _g, 30), (_bx, _by, int(_bw * _frac), _bh), border_radius=4)
                pygame.draw.rect(self.screen, (255, 220, 80),
                                 (_bx + max(0, int(_bw * _frac) - 6), _by, 6, _bh), border_radius=2)
                pygame.draw.rect(self.screen, (255, 255, 255), (_bx, _by, _bw, _bh), 2, border_radius=4)
                # Title
                _bf = pygame.font.SysFont(None, 28, bold=True)
                _bt = _bf.render('BIG MUMMY — Tomb Guardian', True, (255, 230, 140))
                _bts = _bf.render('BIG MUMMY — Tomb Guardian', True, (0, 0, 0))
                _btx = (900 - _bt.get_width()) // 2
                self.screen.blit(_bts, (_btx + 2, _by - 26 + 2))
                self.screen.blit(_bt, (_btx, _by - 26))
                _hf = pygame.font.SysFont(None, 20, bold=True)
                _hpt = _hf.render(f'{_hp} / {_maxhp}', True, (255, 255, 255))
                self.screen.blit(_hpt, (_bx + _bw - _hpt.get_width() - 6, _by + 4))
            _hp_ratio_v = bear.getHp() / max(1, bear.getMaxHp())
            if _hp_ratio_v < 0.25 and bear.getHp() > 0:
                if not hasattr(self, '_vig_base'):
                    self._vig_base = pygame.Surface((900, 700), pygame.SRCALPHA)
                    _band = 110
                    for _i in range(_band):
                        _a = int(255 * (1.0 - _i / _band))
                        pygame.draw.rect(self._vig_base, (200, 30, 40, _a),
                                         (_i, _i, 900 - 2 * _i, 700 - 2 * _i), 1)
                _vig_pulse = abs(math.sin(pygame.time.get_ticks() * 0.008))
                _vig_alpha = int(70 + 90 * _vig_pulse * (1.0 - _hp_ratio_v / 0.25))
                self._vig_base.set_alpha(max(0, min(255, _vig_alpha)))
                self.screen.blit(self._vig_base, (0, 0))
            if self._combo_timer > 0:
                self._combo_timer -= 1
                if self._combo_timer == 0:
                    self._combo = 0
            if self._combo >= 2 and self._combo_timer > 0:
                _ct_frac = self._combo_timer / 150.0
                _ct_alpha = int(255 * min(1.0, _ct_frac * 2.5))
                _ct_size = 36 + min(20, self._combo * 2)
                _ct_pulse = 1.0 + 0.08 * abs(math.sin(pygame.time.get_ticks() * 0.012))
                _ct_size = int(_ct_size * _ct_pulse)
                _ct_font = pygame.font.SysFont(None, _ct_size, bold=True)
                _ct_palette = [(255, 200, 100), (255, 150, 80), (255, 100, 100), (255, 80, 200), (180, 80, 255)]
                _ct_color = _ct_palette[min(len(_ct_palette) - 1, (self._combo - 2) // 3)]
                _ct_text = 'x' + str(self._combo) + ' COMBO!'
                _ct_surf = _ct_font.render(_ct_text, True, _ct_color)
                _ct_shadow = _ct_font.render(_ct_text, True, (0, 0, 0))
                _ct_x = 880 - _ct_surf.get_width()
                _ct_y = 90
                _ct_shadow.set_alpha(_ct_alpha)
                _ct_surf.set_alpha(_ct_alpha)
                self.screen.blit(_ct_shadow, (_ct_x + 3, _ct_y + 3))
                self.screen.blit(_ct_surf, (_ct_x, _ct_y))
                _bar_w = 160
                _bar_h = 6
                _bar_x = 880 - _bar_w
                _bar_y = _ct_y + _ct_surf.get_height() + 4
                _bar_bg = pygame.Surface((_bar_w, _bar_h), pygame.SRCALPHA)
                _bar_bg.fill((0, 0, 0, int(_ct_alpha * 0.6)))
                self.screen.blit(_bar_bg, (_bar_x, _bar_y))
                _bar_fill = pygame.Surface((int(_bar_w * _ct_frac), _bar_h), pygame.SRCALPHA)
                _bar_fill.fill((*_ct_color, _ct_alpha))
                self.screen.blit(_bar_fill, (_bar_x, _bar_y))
            # ---- Combo bonus XP indicator (under the combo bar) ----
            if self._combo_bonus_display is not None:
                _cb = self._combo_bonus_display
                _cb['frames'] -= 1
                if _cb['frames'] <= 0:
                    self._combo_bonus_display = None
                else:
                    _cb_alpha = int(255 * min(1.0, _cb['frames'] / 30.0))
                    _cb_font = pygame.font.SysFont(None, 26, bold=True)
                    _cb_text = 'COMBO x%d  bonus +%d xp' % (_cb['combo'], _cb['bonus'])
                    _cb_surf = _cb_font.render(_cb_text, True, (255, 230, 120))
                    _cb_shadow = _cb_font.render(_cb_text, True, (0, 0, 0))
                    _cb_surf.set_alpha(_cb_alpha)
                    _cb_shadow.set_alpha(_cb_alpha)
                    _cb_x = 880 - _cb_surf.get_width()
                    _cb_y = 90 + 60
                    self.screen.blit(_cb_shadow, (_cb_x + 2, _cb_y + 2))
                    self.screen.blit(_cb_surf, (_cb_x, _cb_y))
            if self._intro_banner is not None:
                _ib = self._intro_banner
                _ib['frames'] -= 1
                _age = _ib['max'] - _ib['frames']
                if _ib['frames'] <= 0:
                    self._intro_banner = None
                else:
                    if _age < 18:
                        _slide = -900 + int((_age / 18.0) * 900)
                    elif _ib['frames'] < 18:
                        _slide = int(((18 - _ib['frames']) / 18.0) * 900)
                    else:
                        _slide = 0
                    _bn_y = 240
                    _bn_h = 110
                    _bn_bg = pygame.Surface((900, _bn_h), pygame.SRCALPHA)
                    pygame.draw.rect(_bn_bg, (10, 5, 25, 200), (0, 0, 900, _bn_h))
                    pygame.draw.line(_bn_bg, (*_ib['color'], 240), (0, 0), (900, 0), 3)
                    pygame.draw.line(_bn_bg, (*_ib['color'], 240), (0, _bn_h - 1), (900, _bn_h - 1), 3)
                    self.screen.blit(_bn_bg, (_slide, _bn_y))
                    _bn_font = pygame.font.SysFont(None, 64, bold=True)
                    _bn_sub_font = pygame.font.SysFont(None, 26, bold=True)
                    _bn_t = _bn_font.render(_ib['text'], True, _ib['color'])
                    _bn_s = _bn_sub_font.render(_ib.get('sub', ''), True, (220, 220, 240))
                    _bn_t_shadow = _bn_font.render(_ib['text'], True, (0, 0, 0))
                    self.screen.blit(_bn_t_shadow, (450 - _bn_t.get_width() // 2 + 3 + _slide, _bn_y + 18 + 3))
                    self.screen.blit(_bn_t, (450 - _bn_t.get_width() // 2 + _slide, _bn_y + 18))
                    self.screen.blit(_bn_s, (450 - _bn_s.get_width() // 2 + _slide, _bn_y + 78))
            for _em in self.mummys:
                try:
                    if getattr(_em, '_elite', False) and _em.getHp() > 0:
                        _ex = _em.getXPosition() + 50
                        _ey = _em.getYPosition() + 60
                        if -50 < _ex < 950:
                            _epulse = 4 + int(math.sin(pygame.time.get_ticks() * 0.01) * 4)
                            pygame.draw.circle(self.screen, (255, 215, 0), (_ex, _ey), 70 + _epulse, 3)
                            pygame.draw.circle(self.screen, (255, 240, 150), (_ex, _ey), 60 + _epulse, 1)
                except Exception:
                    pass
            if getattr(self, '_mummy_hint_active', False):
                _big_mummy_alive = False
                for _mu in self.mummys:
                    try:
                        if _mu.getName() == "bigMummy" and _mu.getHp() > 0:
                            _big_mummy_alive = True
                            break
                    except Exception:
                        pass
                if not _big_mummy_alive:
                    self._mummy_hint_active = False
                    self._mummy_arrow_frames = 0
                else:
                    pass  # bottom hint text removed — arrow + head_alert is enough
            if self._mummy_arrow_frames > 0:
                self._mummy_arrow_frames -= 1
                _big_mummy = None
                for _mu in self.mummys:
                    try:
                        if _mu.getName() == "bigMummy" and _mu.getHp() > 0:
                            _big_mummy = _mu
                            break
                    except Exception:
                        pass
                if _big_mummy is not None:
                    _amx = _big_mummy.getXPosition() + 130
                    _amy = _big_mummy.getYPosition()
                    if 0 < _amx < 900:
                        _bob = int(math.sin(pygame.time.get_ticks() * 0.008) * 8)
                        # Anchor the arrow TIP directly on the forehead
                        # (forehead rect starts at _amy and is 108 tall).
                        # Place tip ~20px down into the forehead, keep label
                        # safely below the upper HUD via a top clamp.
                        _tip_y = max(80, _amy + 20 + _bob)
                        _ay = _tip_y - 30
                        _arrow_color = (255, 80, 80)
                        pygame.draw.polygon(self.screen, _arrow_color, [
                            (_amx, _ay + 30), (_amx - 18, _ay), (_amx - 8, _ay),
                            (_amx - 8, _ay - 22), (_amx + 8, _ay - 22),
                            (_amx + 8, _ay), (_amx + 18, _ay)])
                        pygame.draw.polygon(self.screen, (255, 255, 255), [
                            (_amx, _ay + 30), (_amx - 18, _ay), (_amx - 8, _ay),
                            (_amx - 8, _ay - 22), (_amx + 8, _ay - 22),
                            (_amx + 8, _ay), (_amx + 18, _ay)], 2)
                        _af = pygame.font.SysFont(None, 22, bold=True)
                        _at = _af.render('FOREHEAD!', True, (255, 240, 240))
                        _at_shadow = _af.render('FOREHEAD!', True, (0, 0, 0))
                        self.screen.blit(_at_shadow, (_amx - _at.get_width() // 2 + 1, _ay - 48 + 1))
                        self.screen.blit(_at, (_amx - _at.get_width() // 2, _ay - 48))
                else:
                    self._mummy_arrow_frames = 0
            # ---- Danger alarm: loop two-tone beep when HP is critical ----
            try:
                _hp_pct = bear.getHp() / max(1, bear.getMaxHp())
                _danger_now = (_hp_pct <= 0.25 and bear.getHp() > 0)
                _ch = getattr(self, 'danger_alarm_channel', None)
                _snd = getattr(self, 'danger_alarm_sound', None)
                if _danger_now and _snd and _ch and not getattr(self, '_danger_alarm_playing', False):
                    _ch.play(_snd, loops=-1)
                    self._danger_alarm_playing = True
                elif (not _danger_now) and getattr(self, '_danger_alarm_playing', False):
                    if _ch: _ch.stop()
                    self._danger_alarm_playing = False
            except Exception:
                pass
            self._render_toasts()
            if getattr(self, '_head_alerts', None):
                _ha_keep = []
                _ha_font = pygame.font.SysFont(None, 30, bold=True)
                _ha_pulse = 0.5 + 0.5 * abs(math.sin(pygame.time.get_ticks() * 0.012))
                for _ha in self._head_alerts:
                    _ha['life'] -= 1
                    if _ha['life'] <= 0:
                        continue
                    _ha_keep.append(_ha)
                    _frac = _ha['life'] / max(1, _ha['max_life'])
                    if _frac < 0.20:
                        _alpha = int(255 * (_frac / 0.20))
                    else:
                        _alpha = 255
                    _alpha = max(0, min(255, _alpha))
                    _bx = bear.getXPosition() + 50
                    _by = bear.getYPosition() - 70 - int(_ha_pulse * 6)
                    _txt = _ha_font.render(_ha['text'], True, _ha['color'])
                    _shd = _ha_font.render(_ha['text'], True, (0, 0, 0))
                    _bw = _txt.get_width() + 24
                    _bh = _txt.get_height() + 10
                    _bg = pygame.Surface((_bw, _bh), pygame.SRCALPHA)
                    pygame.draw.rect(_bg, (0, 0, 0, int(_alpha * 0.78)),
                                     _bg.get_rect(), border_radius=10)
                    pygame.draw.rect(_bg, (_ha['color'][0], _ha['color'][1],
                                           _ha['color'][2], int(_alpha * (0.6 + 0.3 * _ha_pulse))),
                                     _bg.get_rect(), width=3, border_radius=10)
                    _bgx = max(10, min(890 - _bw, _bx - _bw // 2))
                    _bgy = max(20, _by - _bh // 2)
                    self.screen.blit(_bg, (_bgx, _bgy))
                    _shd.set_alpha(_alpha)
                    _txt.set_alpha(_alpha)
                    self.screen.blit(_shd, (_bgx + 13, _bgy + 6))
                    self.screen.blit(_txt, (_bgx + 12, _bgy + 5))
                    pygame.draw.polygon(
                        self.screen,
                        (_ha['color'][0], _ha['color'][1], _ha['color'][2]),
                        [(_bgx + _bw // 2 - 8, _bgy + _bh),
                         (_bgx + _bw // 2 + 8, _bgy + _bh),
                         (_bgx + _bw // 2, _bgy + _bh + 10)])
                self._head_alerts = _ha_keep
            # ── Mega-Man-X-style level-up text: slide-in from left, big chunky
            # white-cyan glyphs with thick black outline, screen flash, chromatic
            # split, and "VICTORY" banner bars sweeping across.
            _luf = getattr(bear, '_level_up_float', 0)
            if _luf > 0:
                bear._level_up_float -= 1
                _luf_max = getattr(bear, '_level_up_float_max', 150)
                _luf_age = _luf_max - _luf
                _luf_text = getattr(bear, '_level_up_text', 'LEVEL UP!')
                # Position upper area, modest size — non-intrusive
                _luf_cy = 150
                _base_size = 52
                _font = pygame.font.SysFont(None, _base_size, bold=True)
                # Slide-in: text flies in from left during first 14 frames,
                # then "punches" by overshooting and settling
                if _luf_age < 14:
                    _slide_t = _luf_age / 14.0
                    _slide_off = int(-700 * (1 - _slide_t) ** 2)
                    _scale = 1.0
                elif _luf_age < 22:
                    _slide_off = 0
                    _punch_t = (_luf_age - 14) / 8.0
                    _scale = 1.25 - 0.25 * _punch_t  # punch from 1.25 → 1.0
                else:
                    _slide_off = 0
                    _scale = 1.0 + 0.04 * math.sin(_luf_age * 0.18)
                # Fade out at end
                if _luf < 25:
                    _luf_alpha = int(255 * (_luf / 25.0))
                else:
                    _luf_alpha = 255

                # ── Render the actual text: white core with thick black
                # outline + cyan/magenta chromatic split ──
                _scaled_size = max(20, int(_base_size * _scale))
                _font_s = pygame.font.SysFont(None, _scaled_size, bold=True)
                _white_surf = _font_s.render(_luf_text, True, (255, 255, 255))
                _outline_surf = _font_s.render(_luf_text, True, (0, 0, 0))
                _cyan_surf = _font_s.render(_luf_text, True, (60, 220, 255))
                _mag_surf = _font_s.render(_luf_text, True, (255, 60, 200))
                _tw, _th = _white_surf.get_size()
                _tx = 450 - _tw // 2 + _slide_off
                _ty = _luf_cy - _th // 2

                _white_surf.set_alpha(_luf_alpha)
                _outline_surf.set_alpha(_luf_alpha)
                _cyan_surf.set_alpha(min(200, _luf_alpha))
                _mag_surf.set_alpha(min(200, _luf_alpha))

                # Thick black outline (8 directions, 3px)
                for _ox in (-3, 0, 3):
                    for _oy in (-3, 0, 3):
                        if _ox == 0 and _oy == 0:
                            continue
                        self.screen.blit(_outline_surf, (_tx + _ox, _ty + _oy))
                # Chromatic split offsets for that arcade CRT vibe
                self.screen.blit(_cyan_surf, (_tx - 3, _ty))
                self.screen.blit(_mag_surf, (_tx + 3, _ty))
                # White core on top
                self.screen.blit(_white_surf, (_tx, _ty))

            if (bear.getHp() > 0 and bear.getEndText()
                    and bear.getHp() < bear.getMaxHp() * 0.30
                    and bear.getCoins() >= 30
                    and not self._shop_low_hp_hinted):
                self._shop_low_hp_hinted = True
                self._push_toast('LOW HP! Press ENTER to heal in the Shop',
                                 duration=300, color=(255, 180, 180))
                if getattr(self, 'shop_open_sound', None):
                    try: self.shop_open_sound.play()
                    except Exception: pass
            if bear.getHp() > bear.getMaxHp() * 0.60:
                self._shop_low_hp_hinted = False
            if (not self._critical_hp_popup_shown
                    and bear.getHp() < bear.getMaxHp() * 0.50
                    and bear.getHp() > 0 and bear.getEndText()):
                self._critical_hp_popup_shown = True
                bear.setArrayText([
                    'WARNING: HP GETTING LOW!', '',
                    'Between 30-50% HP, enemies',
                    'have a 30% chance to drop hearts.',
                    'Below 30% the chance is even higher!',
                    'Each heart restores 25 HP.',
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

            # ---- Big-mummy on-screen alert (shows as soon as it's visible,
            #      clears the moment the player lands the first hit) --------
            if not getattr(self, '_bigMummy_first_hit', False):
                _bm_visible = False
                for _mu in self.mummys:
                    try:
                        if (_mu.getName() == "bigMummy" and _mu.getHp() > 0
                                and -100 < _mu.getXPosition() < 950):
                            _bm_visible = True
                            break
                    except Exception:
                        pass
                if _bm_visible and not getattr(self, '_bigMummy_alert_shown', False):
                    self._bigMummy_alert_shown = True
                    self.triggerText1 = True
                    self._mummy_hint_active = True
                    self._mummy_arrow_frames = 99999
                    self._head_alerts.append({
                        'text': 'ATTACK FOREHEAD!',
                        'life': 99999, 'max_life': 99999,
                        'color': (255, 90, 90),
                        'tag': 'bigmummy'})

            for spike in self.spikes:
                spike.draw()

            for door in self.door:
                door.drawRectangle()
                door_x = door.getXPosition()

                if not self.isDoor1Open:
                    if door_x - 90 <= bear.getXPosition():
                        bear.setXPosition(door_x - 91)
                        totalDistance -= STEP
                        if not self.triggerText3:
                            self.triggerText3 = True
                            bear._level_up_float = 180
                            bear._level_up_float_max = 180
                            bear._level_up_text = 'DOOR LOCKED!'
                else:
                    if self.isDoor1Open and bear.getXPosition() > door_x + 50:
                        if not getattr(self, '_boss_door_passed', False):
                            # Resume music now that the player has passed
                            if getattr(self, '_post_mummy_silence', False):
                                self._start_ambient_loop()
                                self._switch_music("normal")
                                self._post_mummy_silence = False
                        self._boss_door_passed = True
                    if (not self.triggerText2
                            and door_x - 150 <= bear.getXPosition()):
                        self.triggerText2 = True
                        bear._level_up_float = 180
                        bear._level_up_float_max = 180
                        bear._level_up_text = 'DOOR OPENED!'

            if not bear.getEndText():
                bear.displayTextBox()

            # ─── Death animation ─────────────────────────────────────
            # When HP first hits 0, play a 120-frame fall/spin/shockwave
            # sequence before the game-over screen takes over.
            _DEATH_ANIM_LEN = 120
            if bear.getHealth() <= 0 and self._death_anim_frame < 0 and not self.triggerText4:
                self._death_anim_frame = 0
                self._death_anim_x = bear.getXPosition()
                self._death_anim_y = bear.getYPosition()
                self._death_anim_dir = -1 if bear.getLeftDirection() else 1
                # Stop the danger alarm so it doesn't blare during the death scene
                try:
                    if getattr(self, '_danger_alarm_playing', False) and getattr(self, 'danger_alarm_channel', None):
                        self.danger_alarm_channel.stop()
                        self._danger_alarm_playing = False
                except Exception:
                    pass
                try:
                    if getattr(self, 'bear_hurt_sound', None):
                        self.bear_hurt_sound.play()
                except Exception:
                    pass
                try:
                    if getattr(self, 'boss_explosion_sound', None):
                        self.boss_explosion_sound.play()
                except Exception:
                    pass

            if self._death_anim_frame >= 0 and self._death_anim_frame < _DEATH_ANIM_LEN:
                _df = self._death_anim_frame
                _dprog = _df / _DEATH_ANIM_LEN
                _dx0 = self._death_anim_x
                _dy0 = self._death_anim_y
                # Brief upward pop, then fall off screen
                if _df < 25:
                    _vert = -2.6 * _df  # rise ~65px
                else:
                    _t2 = _df - 25
                    _vert = -65 + 0.55 * _t2 * _t2 * 0.18 * _t2  # accelerating fall
                # Spin
                _rot = (_df * 9 * self._death_anim_dir) % 360
                # Pick a sprite to spin
                _spr_src = (self.bearWalkingLeft1 if self._death_anim_dir < 0
                            else self.bearWalking1)
                # Red-tint the sprite
                try:
                    _tinted = _spr_src.copy()
                    _tint_a = int(160 * _dprog)
                    _tint_overlay = pygame.Surface(_tinted.get_size(), pygame.SRCALPHA)
                    _tint_overlay.fill((255, 40, 40, _tint_a))
                    _tinted.blit(_tint_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                except Exception:
                    _tinted = _spr_src
                _rotated = pygame.transform.rotate(_tinted, _rot)
                _rect = _rotated.get_rect(center=(_dx0 + 60, _dy0 + 55 + int(_vert)))
                # Expanding white→orange shockwave from death point
                _sw_r = int(20 + _df * 4)
                _sw_a = max(0, 220 - int(_df * 1.8))
                if _sw_a > 0:
                    _sw_surf = pygame.Surface((_sw_r * 2 + 4, _sw_r * 2 + 4),
                                              pygame.SRCALPHA)
                    pygame.draw.circle(_sw_surf, (255, 255, 220, _sw_a),
                                       (_sw_r + 2, _sw_r + 2), _sw_r, 4)
                    pygame.draw.circle(_sw_surf, (255, 140, 60, _sw_a // 2),
                                       (_sw_r + 2, _sw_r + 2), max(1, _sw_r - 8), 3)
                    self.screen.blit(_sw_surf,
                                     (_dx0 + 60 - _sw_r - 2, _dy0 + 55 - _sw_r - 2))
                # "Star burst" particles radiating out
                _num_stars = 8
                for _si in range(_num_stars):
                    _angle = (_si / _num_stars) * 2 * math.pi
                    _sd = 20 + _df * 3
                    _sx = _dx0 + 60 + int(math.cos(_angle) * _sd)
                    _sy = _dy0 + 55 + int(math.sin(_angle) * _sd)
                    _scol_a = max(0, 230 - int(_df * 2))
                    if _scol_a > 0:
                        _star_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
                        pygame.draw.circle(_star_surf, (255, 230, 100, _scol_a),
                                           (5, 5), max(2, 5 - _df // 25))
                        self.screen.blit(_star_surf, (_sx - 5, _sy - 5))
                # The spinning bear
                self.screen.blit(_rotated, _rect.topleft)
                # Screen-wide red vignette flash that fades in
                _flash_a = int(min(140, _df * 2.5))
                if _flash_a > 0:
                    _flash_surf = pygame.Surface(self.screen.get_size(),
                                                 pygame.SRCALPHA)
                    _flash_surf.fill((180, 0, 0, _flash_a))
                    self.screen.blit(_flash_surf, (0, 0))
                # Big "K.O.!" text appears halfway through
                if _df > 60:
                    _ko_font = pygame.font.SysFont(None, 120, bold=True)
                    _ko_a = min(255, (_df - 60) * 8)
                    _ko_surf = _ko_font.render('You died', True, (255, 230, 60))
                    _ko_outline = _ko_font.render('You died', True, (60, 0, 0))
                    _kw, _kh = _ko_surf.get_size()
                    _kx = self.screen.get_width() // 2 - _kw // 2
                    _ky = self.screen.get_height() // 2 - _kh // 2 - 30
                    _ko_surf.set_alpha(_ko_a)
                    _ko_outline.set_alpha(_ko_a)
                    for _ox, _oy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
                        self.screen.blit(_ko_outline, (_kx + _ox, _ky + _oy))
                    self.screen.blit(_ko_surf, (_kx, _ky))
                self._death_anim_frame += 1
                # Hold on the last frame; only proceed when finished
                pygame.display.flip()
                self.clock.tick(60)
                continue

            if bear.getHealth() <= 0 and not self.triggerText4:
                if getattr(self, '_checkpoint_saved', False) and self._checkpoint_data:
                    totalDistance, backgroundScrollX = self._restore_checkpoint(
                        bear, background, totalDistance)
                    bear.setArrayText(['Checkpoint restored!', '',
                                       'Return to your last save.',
                                       'Press "s" to continue'])
                    bear.setEndText(False)
                    self._death_anim_frame = -1  # ready for next death
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
                self.bombs = []; self._bomb_spawn_timer = 0
                self._bomb_wave_30 = False; self._bomb_wave_60 = False
                self._bomb_gauntlet_started = False
                self._bomb_gauntlet_active = False
                self._bomb_gauntlet_timer = 0
                self.heart_drops = []; self.shaman_orbs = []; self._shaman_orb_timer = 0
                self.witch_beams = []

                self.showBoss = True
                self.triggerText1 = False; self.triggerText2 = False
                self.triggerText3 = False; self.triggerText4 = False
                self.triggerText5 = False; self.createdBoss = False
                self._bigMummy_alert_shown = False
                self._bigMummy_first_hit = False
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
                self._zone_count = 0
                self._prev_active_zones = 0
                self._z12_pending_witches = None
                self._calm_zone_active = False
                self._calm_zone_exited = False
                self._calm2_zone_active = False
                self._calm2_zone_exited = False
                self._calm2_fb_timer = 0

                bear = Bear(150, 300, self.screen, self.thud_sound)
                self._bear_ref = bear
                bear.grunt_sound = self.grunt_sound
                bear.jump_scream_sound = getattr(self, 'jump_scream_sound', None)
                bear._mmx_jump_sound = getattr(self, 'mmx_jump_sound', None)
                bear._mmx_jump_sound_alt = getattr(self, 'mmx_jump_sound_alt', None)
                bear._mmx_land_sound = getattr(self, 'mmx_land_sound', None)
                bear._mmx_dash_sound = getattr(self, 'mmx_dash_sound', None)
                bear._mmx_powerup_sound = getattr(self, 'mmx_powerup_sound', None)
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
                self._checkpoint_saved = False
                self._checkpoint_used = False
                self._checkpoint_data = None
                self._critical_hp_popup_shown = False

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
                    _ng_hp_early = _ng_hp_mult * 0.8
                    _ng_dmg_mult = 1.0 + 3.0 * self.newGamePlusLevel
                    _ng_exp_mult = 1.0 + 1.0 * self.newGamePlusLevel
                    _ng_spd_mult = 1.0 + 0.2 * self.newGamePlusLevel
                    self._z1_mummy = Mummy(1000, 20, 260, 360, self.mummy1, self.mummy2, self.screen)
                    self._z1_mummy.health = int(self._z1_mummy.health * _ng_hp_early)
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
                        _m.health = int(_m.health * _ng_hp_early)
                        _m.damageAttack = int(_m.damageAttack * _ng_dmg_mult)
                        _m.exp = int(_m.exp * _ng_exp_mult)
                        _m.rand = max(1, round(_m.rand * _ng_spd_mult))
                        _m._ng_boosted = True
                        if random.random() < min(0.50, 0.15 * self.newGamePlusLevel):
                            _m._elite = True
                            _m.health = int(_m.health * 1.5)
                            _m.exp = int(_m.exp * 2)
                        self.mummys.append(_m)
                    self._switch_music("normal")
                    _ng_coin_bonus = 25 * self.newGamePlusLevel
                    bear.setCoins(bear.getCoins() + _ng_coin_bonus)
                    self._ng_beam_mult = min(2.0, 1.0 + 0.15 * self.newGamePlusLevel)
                    self._ng_lucky_drop_chance = min(0.40, 0.05 * self.newGamePlusLevel)
                    self._push_toast('\u2728 NEW GAME+ %d \u2728' % self.newGamePlusLevel, duration=300, color=(255, 215, 0))
                    self._push_toast('+%d starting coins, +%d%% beam recharge' % (_ng_coin_bonus, int((self._ng_beam_mult - 1.0) * 100)), duration=300, color=(180, 255, 220))
                    self._push_toast('Look for golden ELITE enemies — double XP!', duration=300, color=(255, 200, 100))
                    import random as _ng_rnd
                    _ng_flavor = _ng_rnd.choice([
                        'The pyramid remembers you, bear...',
                        'The mummies whisper your name in fear.',
                        'Even the witches step aside.',
                        'Your aura now leaves a rainbow trail!',
                        'Try typing BEAR, DASH or JUMP for secrets...',
                        'The ShadowShamans bow before your might.',
                    ])
                    self._push_toast(_ng_flavor, duration=300, color=(220, 200, 255))
                    if self.newGamePlusLevel >= 1:
                        self._push_toast('Rainbow trail unlocked!', duration=240, color=(255, 180, 220))
                    if self.newGamePlusLevel >= 3:
                        self._push_toast('NG+3: Confetti rain on every kill!', duration=240, color=(180, 255, 200))
                    if self.newGamePlusLevel >= 5:
                        self._push_toast('NG+5: The FrankenBear wears a crown.', duration=300, color=(255, 215, 80))
                bear.setXPosition(150)
                bear.setYPosition(300)
                backgroundScrollX = 60
                totalDistance = 60
                background.setXPosition(backgroundScrollX)
                self._switch_music("normal")
                self._zone_min_distance = 0
                self._last_zone_idx = 0
                self._zone_lock_toasted = False
                self._zone_wall_world_x = -10000
                self._boots_spawned = False
                try:
                    self.boot_pickups = []
                except Exception:
                    pass

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

            if self.newGamePlusLevel >= 2:
                try:
                    import random as _spk_rnd
                    _bcx = bear.getXPosition() + 50
                    _bcy = bear.getYPosition() + 50
                    if not hasattr(self, '_sparkles'):
                        self._sparkles = []
                    if _spk_rnd.random() < 0.55:
                        _ang = _spk_rnd.uniform(0, 6.283)
                        _rad = _spk_rnd.uniform(40, 75)
                        self._sparkles.append([
                            _bcx + math.cos(_ang) * _rad,
                            _bcy + math.sin(_ang) * _rad,
                            _spk_rnd.uniform(-0.4, 0.4),
                            _spk_rnd.uniform(-1.2, -0.3),
                            _spk_rnd.randint(22, 38),
                            _spk_rnd.choice([(255,255,180),(180,220,255),(255,180,220),(200,255,200)]),
                        ])
                    _sk_keep = []
                    for _sp in self._sparkles:
                        _sp[0] += _sp[2]; _sp[1] += _sp[3]; _sp[4] -= 1
                        if _sp[4] > 0:
                            _alpha = max(0, min(255, int(255 * (_sp[4] / 35.0))))
                            _sz = 2 + int(_sp[4] / 8)
                            _ssurf = pygame.Surface((_sz*4, _sz*4), pygame.SRCALPHA)
                            _col = (_sp[5][0], _sp[5][1], _sp[5][2], _alpha)
                            pygame.draw.line(_ssurf, _col, (0, _sz*2), (_sz*4, _sz*2), 2)
                            pygame.draw.line(_ssurf, _col, (_sz*2, 0), (_sz*2, _sz*4), 2)
                            self.screen.blit(_ssurf, (int(_sp[0])-_sz*2, int(_sp[1])-_sz*2))
                            _sk_keep.append(_sp)
                    self._sparkles = _sk_keep
                except Exception:
                    pass

            if self.newGamePlusLevel >= 4:
                try:
                    _aura_t = pygame.time.get_ticks() * 0.005
                    _aura_pulse = 0.5 + 0.5 * math.sin(_aura_t)
                    _aura_r = int(70 + 20 * _aura_pulse)
                    _aura_alpha = int(40 + 50 * _aura_pulse)
                    _acx = bear.getXPosition() + 50
                    _acy = bear.getYPosition() + 50
                    _asurf = pygame.Surface((_aura_r*2, _aura_r*2), pygame.SRCALPHA)
                    _hue = (self._rainbow_tick * 2) % 360
                    _h6 = _hue / 60.0
                    _xx = 1.0 - abs(_h6 % 2 - 1)
                    if _h6 < 1: _r,_g,_b = 1.0, _xx, 0
                    elif _h6 < 2: _r,_g,_b = _xx, 1.0, 0
                    elif _h6 < 3: _r,_g,_b = 0, 1.0, _xx
                    elif _h6 < 4: _r,_g,_b = 0, _xx, 1.0
                    elif _h6 < 5: _r,_g,_b = _xx, 0, 1.0
                    else: _r,_g,_b = 1.0, 0, _xx
                    pygame.draw.circle(_asurf,
                        (int(_r*255), int(_g*255), int(_b*255), _aura_alpha),
                        (_aura_r, _aura_r), _aura_r)
                    self.screen.blit(_asurf, (_acx - _aura_r, _acy - _aura_r))
                except Exception:
                    pass

            if self.newGamePlusLevel >= 5:
                try:
                    if not hasattr(self, '_starfall'):
                        self._starfall = []
                    import random as _sf_rnd
                    if _sf_rnd.random() < 0.18:
                        self._starfall.append([
                            _sf_rnd.randint(0, 900),
                            -10.0,
                            _sf_rnd.uniform(2.5, 5.5),
                            _sf_rnd.choice([(255,255,200),(255,200,255),(180,220,255)]),
                            _sf_rnd.randint(2, 4),
                        ])
                    _sf_keep = []
                    for _st in self._starfall:
                        _st[1] += _st[2]
                        if _st[1] < 720:
                            _stsurf = pygame.Surface((_st[4]*2, _st[4]*2), pygame.SRCALPHA)
                            pygame.draw.circle(_stsurf,
                                (_st[3][0], _st[3][1], _st[3][2], 200),
                                (_st[4], _st[4]), _st[4])
                            self.screen.blit(_stsurf, (int(_st[0])-_st[4], int(_st[1])-_st[4]))
                            _sf_keep.append(_st)
                    self._starfall = _sf_keep
                except Exception:
                    pass

            # ── Rainbow trail: ALWAYS visible while sliding, plus persistent
            # while walking once unlocked (level 8+ or NG+). Now bigger, brighter,
            # and longer-lasting for much better visibility.
            _is_sliding = getattr(bear, 'slide_frames', 0) > 0
            _trail_unlocked = (self.newGamePlusLevel >= 1 or bear.getLevel() >= 8)
            _is_moving = False
            try:
                _kp_rt = pygame.key.get_pressed()
                _is_moving = _kp_rt[pygame.K_LEFT] or _kp_rt[pygame.K_RIGHT]
            except Exception:
                pass
            # Spawn new trail points only while sliding or (unlocked and active)
            _spawn_trail = _is_sliding or _trail_unlocked
            if _spawn_trail or self._rainbow_trail:
                self._rainbow_tick = (self._rainbow_tick + 3) % 360  # faster cycle
                if _spawn_trail:
                    try:
                        _bx = bear.getXPosition() + 50
                        _by = bear.getYPosition() + 60
                        # Drop trail points more often (every 3px instead of 6px)
                        if not self._rainbow_trail or \
                                abs(self._rainbow_trail[-1][0] - _bx) > 3 or \
                                abs(self._rainbow_trail[-1][1] - _by) > 3:
                            # Slide trails live longer (55f) and are tagged 'slide'
                            _life = 55 if _is_sliding else 38
                            self._rainbow_trail.append([_bx, _by, _life,
                                                        1 if _is_sliding else 0])
                        if len(self._rainbow_trail) > 60:
                            self._rainbow_trail = self._rainbow_trail[-60:]
                    except Exception:
                        pass
                _rt_keep = []
                for _i, _pt in enumerate(self._rainbow_trail):
                    _pt[2] -= 1
                    if _pt[2] > 0:
                        _is_slide_pt = (len(_pt) > 3 and _pt[3] == 1)
                        _life_max = 55 if _is_slide_pt else 38
                        _t_age = _pt[2] / _life_max
                        _hue = (self._rainbow_tick + _i * 14) % 360
                        _h6 = _hue / 60.0
                        _c = 1.0
                        _x_ = _c * (1 - abs(_h6 % 2 - 1))
                        if _h6 < 1: _r, _g, _b = _c, _x_, 0
                        elif _h6 < 2: _r, _g, _b = _x_, _c, 0
                        elif _h6 < 3: _r, _g, _b = 0, _c, _x_
                        elif _h6 < 4: _r, _g, _b = 0, _x_, _c
                        elif _h6 < 5: _r, _g, _b = _x_, 0, _c
                        else: _r, _g, _b = _c, 0, _x_
                        # Beefier: 220 alpha, radius up to 22 for slides / 16 walk
                        _max_a = 230 if _is_slide_pt else 200
                        _alpha = int(_max_a * _t_age)
                        _max_r = 22 if _is_slide_pt else 16
                        _radius = max(4, int(_max_r * _t_age))
                        # Outer halo (soft, big, low alpha)
                        _halo = pygame.Surface((_radius * 3, _radius * 3),
                                               pygame.SRCALPHA)
                        pygame.draw.circle(_halo,
                            (int(_r * 255), int(_g * 255), int(_b * 255), _alpha // 3),
                            (_radius * 3 // 2, _radius * 3 // 2), _radius * 3 // 2)
                        self.screen.blit(_halo,
                            (_pt[0] - _radius * 3 // 2, _pt[1] - _radius * 3 // 2))
                        # Core (vivid, full alpha)
                        _surf = pygame.Surface((_radius * 2, _radius * 2),
                                               pygame.SRCALPHA)
                        pygame.draw.circle(_surf,
                            (int(_r * 255), int(_g * 255), int(_b * 255), _alpha),
                            (_radius, _radius), _radius)
                        # Bright white-hot center
                        pygame.draw.circle(_surf,
                            (255, 255, 255, min(255, _alpha + 30)),
                            (_radius, _radius), max(1, _radius // 3))
                        self.screen.blit(_surf,
                            (_pt[0] - _radius, _pt[1] - _radius))
                        _rt_keep.append(_pt)
                self._rainbow_trail = _rt_keep

            if self._confetti_particles:
                _cp_keep = []
                for _p in self._confetti_particles:
                    _p[0] += _p[2]
                    _p[1] += _p[3]
                    _p[3] += 0.25
                    _p[4] -= 1
                    if _p[4] > 0:
                        _alpha = max(0, min(255, int(255 * (_p[4] / 40.0))))
                        _col = (_p[5][0], _p[5][1], _p[5][2], _alpha)
                        _csurf = pygame.Surface((6, 6), pygame.SRCALPHA)
                        pygame.draw.rect(_csurf, _col, (0, 0, 6, 6))
                        self.screen.blit(_csurf, (int(_p[0]), int(_p[1])))
                        _cp_keep.append(_p)
                self._confetti_particles = _cp_keep

            if self._xp_popups:
                try:
                    _xp_font = pygame.font.SysFont(None, 26, bold=True)
                except Exception:
                    _xp_font = pygame.font.Font(None, 26)
                _xp_keep = []
                for _xp in self._xp_popups:
                    _xp[1] -= 1.1
                    _xp[4] -= 1
                    if _xp[4] > 0:
                        _alpha = max(0, min(255, int(255 * (_xp[4] / 70.0))))
                        _txt_surf = _xp_font.render(_xp[2], True, _xp[3])
                        _shadow = _xp_font.render(_xp[2], True, (0, 0, 0))
                        _wrap = pygame.Surface(_txt_surf.get_size(), pygame.SRCALPHA)
                        _wrap.blit(_txt_surf, (0, 0))
                        _wrap.set_alpha(_alpha)
                        _shadow_wrap = pygame.Surface(_shadow.get_size(), pygame.SRCALPHA)
                        _shadow_wrap.blit(_shadow, (0, 0))
                        _shadow_wrap.set_alpha(_alpha)
                        _bx = int(_xp[0] - _txt_surf.get_width() // 2)
                        _by = int(_xp[1])
                        self.screen.blit(_shadow_wrap, (_bx + 2, _by + 2))
                        self.screen.blit(_wrap, (_bx, _by))
                        _xp_keep.append(_xp)
                self._xp_popups = _xp_keep

            try:
                _hp_now = bear.getHp()
                _max_hp = max(1, bear.getMaxHp())
                _ratio = _hp_now / _max_hp
                if _ratio < 0.25 and _hp_now > 0:
                    if not getattr(self, '_low_hp_warned', False):
                        if getattr(self, 'mmx_low_health_sound', None):
                            try: self.mmx_low_health_sound.play()
                            except Exception: pass
                        self._low_hp_warned = True
                        self._low_hp_pulse_timer = 0
                    else:
                        self._low_hp_pulse_timer = getattr(self, '_low_hp_pulse_timer', 0) + 1
                        if self._low_hp_pulse_timer >= 90:
                            self._low_hp_pulse_timer = 0
                            if getattr(self, 'mmx_low_health_sound', None):
                                try: self.mmx_low_health_sound.play()
                                except Exception: pass
                elif _ratio >= 0.40:
                    self._low_hp_warned = False
                    self._low_hp_pulse_timer = 0
            except Exception:
                pass

            pygame.display.flip()
            self.clock.tick(60)

    # -----------------------------------------------------------------------
    def _spawn_confetti(self, x, y, count=12):
        if self.newGamePlusLevel < 3:
            return
        import random as _crnd
        _palette = [(255, 80, 80), (255, 200, 60), (80, 255, 120),
                    (80, 200, 255), (220, 120, 255), (255, 255, 255)]
        for _ in range(count):
            self._confetti_particles.append([
                float(x), float(y),
                _crnd.uniform(-3.5, 3.5),
                _crnd.uniform(-5.0, -1.5),
                _crnd.randint(28, 44),
                _crnd.choice(_palette),
            ])

    # -----------------------------------------------------------------------
    def deleteAndCreateObjects(self, backgroundScrollX):
        # Zones are ordered in ascending scroll distance with ~4 000+ unit gaps
        # so they never overlap or interfere with one another.

        # ── Fireball tutorial — silent: controls are listed in READY text. ────
        if backgroundScrollX > 400 and not self._fireball_tutorial_shown:
            self._fireball_tutorial_shown = True

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
            hurtTimer = -30
            if getattr(self, 'enemy_spawn_sound', None): self.enemy_spawn_sound.play()
            self._switch_music("boss_mummy")
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []; self.miniFrankenBears = []; self.lasers = []

            self.blocks.extend([self._z1_block_left, self._z1_block_right])
            self._intro_banner = {'text': 'BIG MUMMY', 'sub': 'guardian of the tomb', 'frames': 200, 'max': 200, 'color': (255, 220, 140)}
            self._z1_mummy.setXPosition(750)  # Start just off right edge; walks toward player
            _bear_ref_zm = getattr(self, '_bear_ref', None)
            if _bear_ref_zm is not None and _bear_ref_zm.getLevel() <= 1 and not getattr(self._z1_mummy, '_lvl1_reduced', False):
                self._z1_mummy._lvl1_reduced = True
                self._z1_mummy.health = int(self._z1_mummy.health * 0.7)
            if not getattr(self._z1_mummy, '_exp_boosted', False):
                self._z1_mummy._exp_boosted = True
                self._z1_mummy.exp = int(self._z1_mummy.exp * 1.5)
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
            hurtTimer = -30
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

            # Witch-heavy zone — no mummies. Spawn one witch up front so the
            # player isn't swarmed; the other two arrive later in the zone.
            witch1 = Witch(1500, 200, self.witch, self.witch2, self.screen, self.fireball_sound)
            self.witches.append(witch1)
            self._z12_pending_witches = [
                (1850, 280),
                (2200, 150),
            ]
            self.snakes.append(Snake(1500, 220, self.screen))

        # ── Zone 1.2 reinforcements @ 9 500 – the other two witches arrive ────
        # Spawn just off-screen to the right (screen ≈ 900 wide) so they
        # walk into view rather than appearing on top of the player.
        if (getattr(self, '_z12_pending_witches', None)
                and backgroundScrollX > 9500):
            for _wx, _wy in [(1100, 200), (1400, 280)]:
                self.witches.append(
                    Witch(_wx, _wy, self.witch, self.witch2,
                          self.screen, self.fireball_sound))
            self._z12_pending_witches = None

        # ── Zone 1.5 @ 11 000 – "Crumbling Ruins" gauntlet ───────────────────
        elif not self._monkey_level_active and backgroundScrollX > 11000 and not self.activeMonsters[10]:
            self.activeMonsters[10] = True
            hurtTimer = -30
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

            self.miniFrankenBears.append(MiniFrankenBear(2050, 180, self.screen))

            # ── Two witches: one low-and-close, one high-and-far ─────────────
            witch1 = Witch(1800,  80, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch2 = Witch(2200, 140, self.witch, self.witch2, self.screen, self.fireball_sound)
            self.witches.extend([witch1, witch2])
            self.triggerFire = True

        # ── Zone 2 @ 14 500 – green blobs on a rock platform ──────────────────
        elif not self._monkey_level_active and backgroundScrollX > 14500 and not self.activeMonsters[3]:
            self.activeMonsters[3] = True
            hurtTimer = -30
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

            self.miniFrankenBears.append(MiniFrankenBear(2400, 160, self.screen))
            self.miniFrankenBears.append(MiniFrankenBear(2800, 200, self.screen))

            x = 1950
            for _ in range(6):
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
                x += 450

        # ── Zone 3 @ 18 500 – first witch encounter (3 witches) ──────────────
        elif not self._monkey_level_active and backgroundScrollX > 18500 and not self.activeMonsters[2]:
            self.activeMonsters[2] = True
            hurtTimer = -30
            if getattr(self, 'enemy_spawn_sound', None): self.enemy_spawn_sound.play()
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []; self.shadowShamans = []

            block1 = Block(1100, 340, 100, 60,  "greyRock", self.screen)
            block2 = Block(1420, 100, 150, 300, "monster",  self.screen)
            block3 = Block(1260, 160, 130, 60,  "greyRock", self.screen)
            block4 = Block(950,  340, 600, 60,  "greyRock", self.screen)
            self.blocks.extend([block1, block2, block3, block4])

            witch1 = Witch(1800, 150, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch2 = Witch(2600, 180, self.witch, self.witch2, self.screen, self.fireball_sound)
            self.witches.extend([witch1, witch2])

            for x in [1100, 2100]:
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
            self.triggerFire = True

        # ── Zone 3.5 @ 22 000 – waterfall passage ─────────────────────────────
        elif not self._monkey_level_active and backgroundScrollX > 22000 and not self.activeMonsters[13]:
            self.activeMonsters[13] = True
            hurtTimer = -30
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
            hurtTimer = -30
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

        # ── Calm Zone @ 22 600 – silent breather, only bombs + hearts ─────────
        # Sits ~40 % through the run, between zone 13 (@22 000) and zone 4
        # (@25 500). Clears any leftover monsters so the player gets a quiet
        # stretch with hearts to grab.
        elif (not self._monkey_level_active
              and backgroundScrollX > 22600
              and not getattr(self, '_calm_zone_active', False)):
            self._calm_zone_active = True
            self._calm_zone_exited = False
            self._pre_calm_music = getattr(self, '_current_music', None)
            self.mummys = []; self.witches = []; self.greenBlobs = []
            self.fires = []; self.miniFrankenBears = []; self.shadowShamans = []
            self.snakes = []; self.lasers = []; self.blocks = []
            # Silence the music — bombs falling on a quiet stage
            self._switch_music(None)
            # A few hearts laid out at platform / floor heights
            for _hx, _hy in [(500, 360), (900, 360), (1300, 360),
                             (1700, 360), (2100, 360)]:
                self.heart_drops.append({
                    'x': float(_hx), 'y': float(_hy),
                    'vy': 0.0, 'landed': True, 'life': 99999
                })

        # ── Calm Zone exit @ 24 500 – resume the previous track ───────────────
        if (getattr(self, '_calm_zone_active', False)
                and not getattr(self, '_calm_zone_exited', False)
                and backgroundScrollX > 24500):
            self._calm_zone_exited = True
            _resume = getattr(self, '_pre_calm_music', None) or "deep_crypt"
            self._switch_music(_resume)

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

            # Reduced density + spread out — less overwhelming
            greenBlob  = GreenBlob(1030, 300, 100, 100, self.screen, self.blob_jump_sound)
            greenBlob2 = GreenBlob(2400, 300, 100, 100, self.screen, self.blob_jump_sound)
            self.greenBlobs.extend([greenBlob, greenBlob2])

            x = 1500
            for _ in range(3):
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
                x += 700

            mini1 = MiniFrankenBear(2000, 160, self.screen)
            self.miniFrankenBears.append(mini1)

        # ── Quiet Zone 2 @ 42 000 – longer silent stretch with creative ──────
        # blocks, only bombs + falling fireballs (no music, no enemies).
        elif (not self._monkey_level_active
              and backgroundScrollX > 42000
              and not getattr(self, '_calm2_zone_active', False)):
            self._calm2_zone_active = True
            self._calm2_zone_exited = False
            self._pre_calm2_music = getattr(self, '_current_music', None)
            self.mummys = []; self.witches = []; self.greenBlobs = []
            self.fires = []; self.miniFrankenBears = []; self.shadowShamans = []
            self.snakes = []; self.lasers = []; self.blocks = []
            self._switch_music(None)
            # Creative staircase + floating-island layout — invites jumping
            # while bombs and fireballs rain down.
            stair = [
                (1100, 360, 220, 40, "greyRock"),
                (1400, 320, 220, 40, "checkered"),
                (1700, 280, 220, 40, "striped"),
                (2050, 240, 260, 40, "stripedFlip"),
                (2400, 200, 260, 40, "checkered"),
                (2800, 250, 220, 40, "greyRock"),
                (3150, 300, 260, 40, "striped"),
                (3500, 260, 260, 40, "checkered"),
                (3900, 220, 240, 40, "greyRock"),
                (4250, 290, 320, 40, "striped"),
                (4700, 340, 260, 40, "checkered"),
            ]
            for _bx, _by, _bw, _bh, _bt in stair:
                self.blocks.append(Block(_bx, _by, _bw, _bh, _bt, self.screen))
            # Hearts placed along the path for survivability
            for _hx, _hy in [(1500, 290), (2200, 210), (2900, 220),
                             (3600, 230), (4350, 260), (4800, 310)]:
                self.heart_drops.append({
                    'x': float(_hx), 'y': float(_hy),
                    'vy': 0.0, 'landed': True, 'life': 99999
                })
            self._calm2_fb_timer = 0

        # ── Quiet Zone 2 exit @ 43 500 – resume previous track ───────────────
        if (getattr(self, '_calm2_zone_active', False)
                and not getattr(self, '_calm2_zone_exited', False)
                and backgroundScrollX > 43500):
            self._calm2_zone_exited = True
            _resume2 = getattr(self, '_pre_calm2_music', None) or "deep_crypt"
            self._switch_music(_resume2)

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

            # Reduced + spread — was 4 witches + 3 mummies
            witch1 = Witch(1500, 200, self.witch, self.witch2, self.screen, self.fireball_sound)
            witch2 = Witch(2400, 150, self.witch, self.witch2, self.screen, self.fireball_sound)
            self.witches.extend([witch1, witch2])
            for x in [1050, 1900, 2700]:
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

            # Reduced + spread — was 3 mummies + 2 witches + 2 blobs + 2 minis
            for x in [1000, 1900, 2800]:
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
            witch1 = Witch(2300, 150, self.witch, self.witch2, self.screen, self.fireball_sound)
            self.witches.extend([witch1])
            self.greenBlobs.append(GreenBlob(1500, 300, 100, 100, self.screen, self.blob_jump_sound))

            mini1 = MiniFrankenBear(2500, 120, self.screen)
            self.miniFrankenBears.extend([mini1])
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

            # Reduced + spread — was 2 shamans + 2 minis + 2 mummies + 2 blobs
            self.shadowShamans.extend([
                ShadowShaman(1100, 180, self.witch, self.witch2, self.screen),
                ShadowShaman(2400, 140, self.witch, self.witch2, self.screen),
            ])
            mini1 = MiniFrankenBear(1900, 120, self.screen)
            self.miniFrankenBears.extend([mini1])

            self.mummys.extend([
                Mummy(1500, 300, 100, 100, self.mummy1, self.mummy2, self.screen),
                Mummy(2800, 300, 100, 100, self.mummy1, self.mummy2, self.screen),
            ])
            self.greenBlobs.extend([
                GreenBlob(2200, 300, 100, 100, self.screen, self.blob_jump_sound),
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
            _ng_early = backgroundScrollX < 18000
            for _m in (self.mummys + self.witches + self.greenBlobs +
                       self.shadowShamans + self.miniFrankenBears + self.lions):
                if not getattr(_m, '_ng_boosted', False):
                    _m._ng_boosted = True
                    _hp_mult = _ng_hp_m * 0.8 if _ng_early else _ng_hp_m
                    _m.health = int(_m.health * _hp_mult)
                    _m.damageAttack = int(_m.damageAttack * _ng_dmg_m)
                    _m.exp = int(_m.exp * _ng_exp_m)
                    if hasattr(_m, 'walk_speed'):
                        _m.walk_speed = max(1, round(_m.walk_speed * _ng_spd_m))
                    if hasattr(_m, 'rand'):
                        _m.rand = max(1, round(_m.rand * _ng_spd_m))

        bear = getattr(self, '_bear_ref', None)
        if bear is None:
            return
        _low_hp_slow = bear.getHp() > 0 and bear.getHp() < bear.getMaxHp() * 0.30
        for _m in (self.mummys + self.witches + self.greenBlobs +
                   self.shadowShamans + self.miniFrankenBears + self.lions +
                   self.monkey_mummies + self.snakes):
            _was_active = getattr(_m, '_lowhp_active', False)
            if hasattr(_m, 'rand'):
                if not hasattr(_m, '_lowhp_orig_rand'):
                    _m._lowhp_orig_rand = _m.rand
                if _low_hp_slow:
                    _m.rand = max(1, int(round(_m._lowhp_orig_rand * 0.8)))
                else:
                    _m.rand = _m._lowhp_orig_rand
            if hasattr(_m, 'walk_speed'):
                if not hasattr(_m, '_lowhp_orig_walk'):
                    _m._lowhp_orig_walk = _m.walk_speed
                if _low_hp_slow:
                    _m.walk_speed = max(1, int(round(_m._lowhp_orig_walk * 0.8)))
                else:
                    _m.walk_speed = _m._lowhp_orig_walk
            _m._lowhp_active = _low_hp_slow

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

    def _update_bonus_instrument_layer(self, track):
        """Slow drum boom layer that plays throughout the entire game (skipped only during boss tracks)."""
        if not getattr(self, '_tension_layers_ready', False):
            return
        if not hasattr(self, '_bonus_inst_channel'):
            try:
                self._bonus_inst_channel = pygame.mixer.Channel(20)
            except Exception:
                self._bonus_inst_channel = None
        ch = getattr(self, '_bonus_inst_channel', None)
        if ch is None:
            return
        # Skip during boss music — boss tracks should stay focused
        if track in ("boss_mummy", "boss_final"):
            try: ch.fadeout(800)
            except Exception: pass
            return
        _candidates = [getattr(self, '_layer_drum_pulse', None),
                       getattr(self, '_layer_drum_heart', None),
                       getattr(self, '_layer_drum_swell', None)]
        _candidates = [s for s in _candidates if s is not None]
        if not _candidates:
            try: ch.fadeout(800)
            except Exception: pass
            return
        import random as _brnd
        snd = _brnd.choice(_candidates)
        # Keep drums sitting in the background under the melody.
        # Per-sound volumes (set at load) handle the relative mix between
        # pulse (30%) and heart/swell (50%); channel acts as a master cap.
        _vol = 0.55 if track in ("normal", "post_boss_normal") else 0.65
        try:
            ch.stop()
            ch.play(snd, loops=-1, fade_ms=800)
            ch.set_volume(_vol)
        except Exception:
            pass

    def _roll_attack_bonus(self, dmg):
        """Apply per-attack damage rolls: 5%->+10%, 20%->+5%, 50%->+3, 25%->+4."""
        import random as _r
        if _r.random() < 0.05: dmg = int(dmg * 1.10 + 0.5)
        if _r.random() < 0.20: dmg = int(dmg * 1.05 + 0.5)
        if _r.random() < 0.50: dmg += 3
        if _r.random() < 0.25: dmg += 4
        return max(1, dmg)

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

    def _push_toast(self, text, duration=240, color=(255, 255, 255)):
        """Show a non-blocking message at the bottom of the screen.

        Multiple toasts stack and slide up. Duration is in frames (60fps).
        """
        if not hasattr(self, '_toasts') or self._toasts is None:
            self._toasts = []
        self._toasts.append({'text': text, 'life': duration, 'max_life': duration, 'color': color})

    def _render_toasts(self):
        if not getattr(self, '_toasts', None):
            return
        _toast_font = pygame.font.SysFont(None, 34, bold=True)
        _y_base = 660
        _alive = []
        for i, _t in enumerate(self._toasts):
            _t['life'] -= 1
            if _t['life'] <= 0:
                continue
            _alive.append(_t)
        self._toasts = _alive[-3:]
        _pulse = 0.5 + 0.5 * abs(math.sin(pygame.time.get_ticks() * 0.006))
        for i, _t in enumerate(reversed(self._toasts)):
            _frac = _t['life'] / max(1, _t['max_life'])
            if _frac > 0.90:
                _alpha = int(255 * (1.0 - _frac) / 0.10)
            elif _frac < 0.15:
                _alpha = int(255 * (_frac / 0.15))
            else:
                _alpha = 255
            _alpha = max(0, min(255, _alpha))
            _y = _y_base - i * 44
            _txt = _toast_font.render(_t['text'], True, _t['color'])
            _shadow = _toast_font.render(_t['text'], True, (0, 0, 0))
            _bg_w = _txt.get_width() + 40
            _bg_h = _txt.get_height() + 16
            _bg = pygame.Surface((_bg_w, _bg_h), pygame.SRCALPHA)
            pygame.draw.rect(_bg, (0, 0, 0, int(_alpha * 0.82)),
                             _bg.get_rect(), border_radius=14)
            _border_a = int(_alpha * (0.55 + 0.35 * _pulse))
            pygame.draw.rect(_bg, (_t['color'][0], _t['color'][1], _t['color'][2], _border_a),
                             _bg.get_rect(), width=3, border_radius=14)
            _bg_x = 450 - _bg_w // 2
            _bg_y = _y - _bg_h // 2
            self.screen.blit(_bg, (_bg_x, _bg_y))
            _shadow.set_alpha(_alpha)
            _txt.set_alpha(_alpha)
            self.screen.blit(_shadow, (_bg_x + 22, _bg_y + 10))
            self.screen.blit(_txt, (_bg_x + 20, _bg_y + 8))

    def _stop_ambient_loop(self):
        if self._ambient_channel and self._ambient_playing:
            self._ambient_channel.fadeout(1000)
            self._ambient_playing = False

    def _switch_music(self, track):
        if getattr(self, '_current_music', None) == track:
            return
        self._current_music = track
        try:
            self._update_bonus_instrument_layer(track)
        except Exception:
            pass
        if track is None:
            try:
                pygame.mixer.music.fadeout(600)
            except Exception:
                pass
            try:
                self._stop_tension_layers()
            except Exception:
                pass
            if self._ambient_playing and self._ambient_channel:
                self._ambient_channel.set_volume(0.0)
            return
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
        self._sway_period = 24

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
        # Per-tile variant: 0 = regular sway pair, 1 = alt (coffin) tile.
        # Slots start opposite so the alt is visible right away, then they
        # flip every time a tile wraps off-screen — alternating forever.
        self._bg1_variant = 0
        self._bg2_variant = 1
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
                # Pick image per tile based on its current variant so the
                # regular and alt (coffin) backgrounds alternate as the
                # world scrolls — not just once at the start.
                _reg = self.bg_pairs[bg_idx][self._sway_frame]
                _alt = self.bg_alt_pairs[bg_idx]
                self.bgimage     = _alt if self._bg1_variant == 1 else _reg
                self.bgimage_alt = _alt if self._bg2_variant == 1 else self.bg_pairs[bg_idx][1 - self._sway_frame]

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
                self._bg1_variant = 1 - self._bg1_variant
            if self.bgX2 <= -self.rectBGimg.width:
                self.bgX2 = self.rectBGimg.width
                self._bg2_variant = 1 - self._bg2_variant
        elif characterPosition <= 180:
            self.totalX -= STEP
            self.bgX1 += self.moving_speed
            self.bgX2 += self.moving_speed
            if self.bgX1 >= self.rectBGimg.width:
                self.bgX1 = -self.rectBGimg.width
                self._bg1_variant = 1 - self._bg1_variant
            if self.bgX2 >= self.rectBGimg.width:
                self.bgX2 = -self.rectBGimg.width
                self._bg2_variant = 1 - self._bg2_variant


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
        self.health = int(random.randint(7, 16) * 1.20 * 1.05)
        self._defense = random.randint(1, 10) / 100.0
        self._bear_x = 400
        self._bear_y = 300
        self._chase_range = random.randint(250, 450)
        self._aggro = False
        self._aggro_delay = random.randint(0, 90)
        self._aggro_timer = 0
        # ── Chase fatigue: mummies tire after ~5s of chasing and disengage ──
        self._chase_duration = 0
        self._chase_max = random.randint(150, 240)  # 2.5-4s
        self._chase_cooldown = 0  # frames during which they refuse to chase
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
        self.max_hp = self.hp
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
            self.health = int(24 * 1.20 * 1.05)
            self.max_health = self.health
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
        if getattr(self, 'destructionAnimation', 0) > 0 or getattr(self, 'startDestructionAnimation', False):
            alpha = 255
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
            # Tick down the post-fatigue cooldown
            if self._chase_cooldown > 0:
                self._chase_cooldown -= 1
            # Engage only when in range AND not on fatigue cooldown
            if (_dist < self._chase_range
                    and self._aggro_timer >= self._aggro_delay
                    and self._chase_cooldown == 0):
                if not self._aggro:
                    self._chase_duration = 0
                self._aggro = True
            elif _dist > self._chase_range:
                # Player escaped chase range → instantly disengage and rest
                if self._aggro:
                    self._chase_cooldown = random.randint(360, 600)  # 6-10s
                self._aggro = False
                self._aggro_timer = 0
                self._chase_duration = 0
            # Disengage after chasing for too long — they "give up" and rest
            if self._aggro:
                self._chase_duration += 1
                if self._chase_duration >= self._chase_max:
                    self._aggro = False
                    self._chase_duration = 0
                    self._chase_cooldown = random.randint(480, 720)  # 8-12s rest

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
        self.health = int(random.randint(24, 42) * 1.20 * 1.05)
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
        # Chase fatigue
        self._chase_duration = 0
        self._chase_max = random.randint(180, 300)  # 3-5s
        self._chase_cooldown = 0
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
        if getattr(self, 'destructionAnimation', 0) > 0 or getattr(self, 'startDestructionAnimation', False):
            alpha = 255
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

            if self._chase_cooldown > 0:
                self._chase_cooldown -= 1
            if _dist > self._aggro_range:
                if self._state != 'idle':
                    self._chase_cooldown = random.randint(360, 600)
                self._state = 'idle'
                self._chase_duration = 0
            elif (self._state == 'idle' and _dist < self._aggro_range * 0.7
                    and self._chase_cooldown == 0):
                self._state = 'approach'
                self._state_timer = 0
                self._chase_duration = 0
            # Fatigue: after sustained pursuit, retreat to idle and rest
            if self._state != 'idle':
                self._chase_duration += 1
                if self._chase_duration >= self._chase_max:
                    self._state = 'idle'
                    self._chase_duration = 0
                    self._chase_cooldown = random.randint(480, 720)

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
        if getattr(self, '_falling_only', False):
            # Pure straight downward fall — no bounce. Marked dead off-screen.
            self.y += abs(self.vel_y)
            self.x += self.vel_x
            if self.y > 460:
                self._dead = True
        elif self.y < 370:
            self.y -= self.vel_y
            self.x += self.vel_x
        else:
            self.vel_y *= -1
            self.y -= self.vel_y
            _bs = getattr(self, '_bounce_sound', None)
            if _bs: _bs.play()
        # ----- Optional fiery trail (player fireballs only) -----
        if getattr(self, '_trail_enabled', False):
            if not hasattr(self, '_trail_pts'):
                self._trail_pts = []
            self._trail_pts.append((self.x, self.y))
            _max_len = max(3, getattr(self, '_trail_max_len', 8))
            if len(self._trail_pts) > _max_len:
                self._trail_pts = self._trail_pts[-_max_len:]
            _fw = self.fire.get_width(); _fh = self.fire.get_height()
            for _i, (_tx, _ty) in enumerate(self._trail_pts[:-1]):
                _frac = (_i + 1) / len(self._trail_pts)
                _radius = max(3, int(_fw * 0.35 * _frac))
                _alpha = int(180 * _frac * _frac)
                # Outer glow (orange)
                _gs = pygame.Surface((_radius*2, _radius*2), pygame.SRCALPHA)
                pygame.draw.circle(_gs, (255, 140, 30, _alpha),
                                   (_radius, _radius), _radius)
                pygame.draw.circle(_gs, (255, 220, 120, min(255, _alpha+40)),
                                   (_radius, _radius), max(1, _radius // 2))
                self.screen.blit(_gs, (_tx + _fw//2 - _radius,
                                       _ty + _fh//2 - _radius))
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
        self.health = int(26 * 1.20 * 1.05)
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
        # Chase fatigue
        self._chase_duration = 0
        self._chase_max = random.randint(180, 300)  # 3-5s
        self._chase_cooldown = 0
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
            self.health = int(60 * 1.20 * 1.05)
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
        if getattr(self, 'destructionAnimation', 0) > 0 or getattr(self, 'startDestructionAnimation', False):
            alpha = 255
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
            if self._chase_cooldown > 0:
                self._chase_cooldown -= 1
            # Hysteresis: must come closer than 70% of range to start chasing
            _was_chasing = self._chase_duration > 0
            _engage_dist = self._chase_range if _was_chasing else self._chase_range * 0.7
            _can_chase = (_dist < _engage_dist and self._chase_cooldown == 0)
            if _can_chase:
                self._chase_duration += 1
                if self._chase_duration >= self._chase_max:
                    self._chase_duration = 0
                    self._chase_cooldown = random.randint(480, 720)
                    _can_chase = False
            else:
                if _was_chasing and self._chase_cooldown == 0:
                    self._chase_cooldown = random.randint(360, 600)
                self._chase_duration = 0
            if _can_chase:
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
        # ---- Slide / Mega-Man-X dash attributes ----
        self.slide_frames = 0          # frames of active slide remaining
        self.slide_dir = 1             # +1 right, -1 left
        self.slide_cooldown = 0        # frames until next slide allowed
        self.slide_jump_carry = 0      # frames of horizontal momentum after a slide jump
        self.slide_jump_dir = 0        # direction of carry
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
        self.endText = True
        self.maxHp = 100
        self.attack = 10
        self.hp = 100
        self.maxExp = 12
        self.exp = 0
        self.text1 = ""
        self.text2 = ""
        self.text3 = ""
        self.textArray = []
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
        self._coyote_max = 10
        self._jump_buffer = 0
        self._jump_buffer_max = 12
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
            # Apply 4 damage every 2 seconds (120 frames) — extra +2 bite
            if self.poison_damage_tick >= 120:
                self.hp = max(0, self.hp - 4)
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
        try:
            _alt = getattr(self, '_mmx_jump_sound_alt', None)
            _mmx = getattr(self, '_mmx_jump_sound', None)
            if _alt and random.random() < 0.30:
                _alt.play()
            elif _mmx:
                _mmx.play()
        except Exception:
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
            try:
                _mmx_l = getattr(self, '_mmx_land_sound', None)
                if _mmx_l:
                    _mmx_l.play()
            except Exception:
                pass
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
        if getattr(self, 'is_crouching', False):
            if objectName not in _MONSTER_SIZES:
                return False
            _ow, _oh = _MONSTER_SIZES[objectName]
            _crouch_top_offset = 45
            _crouch_h = BEAR_H - _crouch_top_offset - 5
            bear_rect = pygame.Rect(bearXPosition + 5,
                                    bearYPosition + _crouch_top_offset,
                                    BEAR_W - 10, _crouch_h)
            obj_rect = pygame.Rect(objectXPosition, objectYPosition, _ow, _oh)
            return bear_rect.colliderect(obj_rect)
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
        _can_afford = self.coins >= 30
        if _can_afford:
            _pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
            _glow_r = int(14 + _pulse * 4)
            _glow_a = int(60 + _pulse * 80)
            _glow = pygame.Surface((_glow_r * 2, _glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(_glow, (255, 240, 120, _glow_a), (_glow_r, _glow_r), _glow_r)
            self.screen.blit(_glow, (CX + 24 - _glow_r, CY + 28 - _glow_r))
        pygame.draw.circle(self.screen, (255, 215, 0), (CX + 24, CY + 28), 12)
        pygame.draw.circle(self.screen, (255, 245, 130), (CX + 24, CY + 28), 6)
        render_hud_text_outlined(self.screen, _FONT_HUD, str(self.coins),
                           CX + 50, CY + 8, (255, 255, 160))
        if _can_afford:
            _hint_pulse = abs(math.sin(pygame.time.get_ticks() * 0.004))
            _hint_col = (180 + int(_hint_pulse * 75), 255, 180 + int(_hint_pulse * 50))
            render_hud_text_outlined(self.screen, _FONT_HUD_VAL,
                                     '[ENTER] SHOP', CX + 140, CY + 6, _hint_col)
        else:
            render_hud_text_outlined(self.screen, _FONT_HUD_VAL,
                                     '[ENTER] Shop', CX + 140, CY + 6, (170, 160, 130))
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
        if getattr(self, '_god_mode', False):
            return 0
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
            if hasattr(self, '_mmx_powerup_sound') and self._mmx_powerup_sound:
                try: self._mmx_powerup_sound.play()
                except Exception: pass
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
            self._level_up_float = 150
            self._level_up_float_max = 150
            self._level_up_text = 'LEVEL UP! Lv.' + str(self.level)
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
        self.key = self._build_silver_key()
        self.isOpen = False
        self.initialHeight = yPosition

    @staticmethod
    def _build_silver_key():
        """Procedural cartoon silver key — round bow, slim shaft, two teeth."""
        w, h = 64, 64
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        # soft shadow
        pygame.draw.circle(s, (0, 0, 0, 70), (20, 34), 14)
        pygame.draw.rect(s, (0, 0, 0, 60), (28, 28, 30, 10), border_radius=3)
        # bow (round head) — silver gradient via concentric circles
        for i, col in enumerate([(110, 115, 125), (160, 165, 175),
                                 (200, 205, 215), (235, 240, 250)]):
            pygame.draw.circle(s, col, (20, 32), 13 - i * 2)
        pygame.draw.circle(s, (60, 65, 75), (20, 32), 13, 2)
        # inner hole
        pygame.draw.circle(s, (40, 45, 55), (20, 32), 5)
        pygame.draw.circle(s, (20, 25, 35), (20, 32), 3)
        # shaft
        pygame.draw.rect(s, (180, 185, 195), (32, 29, 26, 7))
        pygame.draw.rect(s, (220, 225, 235), (32, 29, 26, 2))
        pygame.draw.rect(s, (60, 65, 75), (32, 29, 26, 7), 1)
        # teeth
        pygame.draw.rect(s, (180, 185, 195), (50, 36, 4, 7))
        pygame.draw.rect(s, (60, 65, 75), (50, 36, 4, 7), 1)
        pygame.draw.rect(s, (180, 185, 195), (44, 36, 4, 5))
        pygame.draw.rect(s, (60, 65, 75), (44, 36, 4, 5), 1)
        # specular highlight
        pygame.draw.circle(s, (255, 255, 255, 200), (16, 28), 3)
        return pygame.transform.scale(s, (50, 50))

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
    _bear_ref = None  # set once at game start so spikes can scale damage to bear's max HP

    @staticmethod
    def _build_sprite(w=100, h=60):
        """Cartoon Banjo-Kazooie style spike trap: wooden plank base with iron spikes."""
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # Wooden plank base (warm brown with grain)
        plank_y = h - 18
        pygame.draw.rect(surf, (110, 70, 40), (0, plank_y, w, 18), border_radius=3)
        pygame.draw.rect(surf, (140, 95, 55), (0, plank_y, w, 4), border_radius=2)
        pygame.draw.rect(surf, (70, 42, 22), (0, h - 4, w, 4), border_radius=2)
        # Wood grain lines
        for gx in range(8, w, 18):
            pygame.draw.line(surf, (80, 50, 28), (gx, plank_y + 5), (gx + 6, h - 5), 1)
        # Iron rivets at corners
        for rx in (5, w - 6):
            for ry in (plank_y + 4, h - 6):
                pygame.draw.circle(surf, (60, 60, 70), (rx, ry), 2)
                pygame.draw.circle(surf, (180, 180, 190), (rx - 1, ry - 1), 1)
        # Spikes - 5 cartoon iron triangles with highlights
        spike_w = w // 5
        for i in range(5):
            cx = i * spike_w + spike_w // 2
            tip_y = 4
            base_y = plank_y + 2
            # Black outline
            outline = [(cx - spike_w // 2 - 1, base_y + 1),
                       (cx, tip_y - 2),
                       (cx + spike_w // 2 + 1, base_y + 1)]
            pygame.draw.polygon(surf, (15, 15, 20), outline)
            # Spike body — gradient look via two polygons
            left_face = [(cx - spike_w // 2, base_y),
                         (cx, tip_y),
                         (cx, base_y)]
            right_face = [(cx, base_y),
                          (cx, tip_y),
                          (cx + spike_w // 2, base_y)]
            pygame.draw.polygon(surf, (180, 185, 200), left_face)   # bright left face
            pygame.draw.polygon(surf, (110, 115, 130), right_face)  # darker right face
            # Highlight streak
            pygame.draw.line(surf, (235, 240, 250),
                             (cx - 2, tip_y + 4), (cx - 4, base_y - 6), 2)
            # Tip glint
            pygame.draw.circle(surf, (255, 255, 255), (cx, tip_y + 2), 1)
        return surf

    def __init__(self, x, y, screen):
        self.x = x
        self.y = y
        self.screen = screen
        self.stunned = False
        self.health = 1
        self.damageAttack = random.randint(13, 26)
        if not hasattr(SpikeBlock, '_cached_sprite'):
            SpikeBlock._cached_sprite = SpikeBlock._build_sprite(100, 60)
        self.spike = SpikeBlock._cached_sprite
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
        # Spikes hurt for 5% of player's max HP (rounded, min 1).
        _bear = SpikeBlock._bear_ref
        if _bear is not None:
            try:
                return max(1, int(round(_bear.getMaxHp() * 0.05)))
            except Exception:
                pass
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
        self.health = int(random.randint(40, 60) * 1.20 * 1.05)
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
        # Chase fatigue (ShadowShaman): periodically pauses repositioning
        self._chase_duration = 0
        self._chase_max = random.randint(180, 300)
        self._chase_cooldown = 0
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
        if getattr(self, 'destructionAnimation', 0) > 0 or getattr(self, 'startDestructionAnimation', False):
            alpha = 255
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
            if self._chase_cooldown > 0:
                self._chase_cooldown -= 1
            _resting = self._chase_cooldown > 0
            if not _resting:
                self._chase_duration += 1
                if self._chase_duration >= self._chase_max:
                    self._chase_duration = 0
                    self._chase_cooldown = random.randint(180, 300)
                    _resting = True
            if _resting:
                _mx = 0
                _my = 0
            elif _dist < self._preferred_dist - 30:
                _mx = -1 if _dx > 0 else 1
            elif _dist > self._preferred_dist + 30:
                _mx = 1 if _dx > 0 else -1
            else:
                _mx = 1 if self._strafe_timer % 100 < 50 else -1
            if _resting:
                pass
            else:
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
        self.health = int(45 * 1.20 * 1.05)
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
        # Chase fatigue
        self._chase_duration = 0
        self._chase_max = random.randint(180, 300)
        self._chase_cooldown = 0
        
    def walk(self):
        _dx = self._bear_x - self.x
        _dist = abs(_dx)
        if self._chase_cooldown > 0:
            self._chase_cooldown -= 1
        _was_chasing = self._chase_duration > 0
        _engage_dist = self._chase_range if _was_chasing else self._chase_range * 0.7
        _engaged = (_dist < _engage_dist and _dist > 20
                    and self._chase_cooldown == 0)
        if _engaged:
            self._chase_duration += 1
            if self._chase_duration >= self._chase_max:
                self._chase_duration = 0
                self._chase_cooldown = random.randint(480, 720)
                _engaged = False
        else:
            if _was_chasing and self._chase_cooldown == 0:
                self._chase_cooldown = random.randint(360, 600)
            self._chase_duration = 0
        if _engaged:
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
        if getattr(self, 'destructionAnimation', 0) > 0 or getattr(self, 'startDestructionAnimation', False):
            alpha = 255
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
        self.health = int(1000 * 1.44 * 1.05)  # base 1000 * 1.20 (orig) * 1.20 (boost) * 1.05 (enemy hp +5%)
        self.max_health = self.health
        self._defense = random.randint(1, 10) / 100.0
        self.startDestructionAnimation = False
        self.boss1 = pygame.image.load("Game/Images/boss1.png")
        self.boss1 = pygame.transform.scale(self.boss1, (240, 240))
        self.boss2 = pygame.image.load("Game/Images/boss2.png")
        self.boss2 = pygame.transform.scale(self.boss2, (240, 240))
        self.boss3 = pygame.image.load("Game/Images/boss3.png")
        self.boss3 = pygame.transform.scale(self.boss3, (240, 240))
        self.exp = 0
        self.boss3Flipped = pygame.transform.flip(self.boss3, True, False)
        self.flipped = random.randint(1, 2)
        self.isHurtAnimationStarted = False
        self.isHurtTimer = 0
        self.blinkTimer = 0
        self.attackTimer = 0
        self.randomBlink = random.randint(50, 150)
        self.randomAttack = random.randint(95, 145)
        self.bossDisplay = self.boss3
        self.blinked = False
        self.attacked = False
        self.throwFireBallLeft = False
        self.throwFireBallRight = False
        self.damageAttack = 12
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
        # Pinned near the floor so the number is always readable on top of
        # the busy boss sprite/background. (boss position is unaffected.)
        render_damage_text(self.screen, _FONT_BOSS_DAMAGE, damage,
                            int(self.x) + 120, 380,
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
                    self.randomAttack = random.randint(95, 145)
                else:
                    self.randomAttack = random.randint(95, 145)
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
            _fw = self.fire.get_width(); _fh = self.fire.get_height()
            _sw, _sh = self.screen.get_size()
            for _ in range(_num_fires):
                _fx = self.x + random.randint(-180, 80)
                _fy = self.y + random.randint(-180, 80)
                _fx = max(0, min(_sw - _fw, _fx))
                _fy = max(0, min(_sh - _fh, _fy))
                self.screen.blit(self.fire, (_fx, _fy))

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
        self.health = int(15 * 1.80 * 2 * 1.05)
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
        if getattr(self, 'destructionAnimation', 0) > 0 or getattr(self, 'startDestructionAnimation', False):
            alpha = 255
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
        self.health = int(20 * 1.15 * 1.05)
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
        if getattr(self, 'destructionAnimation', 0) > 0 or getattr(self, 'startDestructionAnimation', False):
            alpha = 255
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
        self.health = int(25 * 1.20 * 1.05)
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
        if getattr(self, 'destructionAnimation', 0) > 0 or getattr(self, 'startDestructionAnimation', False):
            alpha = 255
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
