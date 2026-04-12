# -*- coding: utf-8 -*-
"""Game constants and font initialization."""
import pygame

# Movement step – pixels per frame for walking/world-scroll
STEP = 8
JUMP_STEP = 7

# Monitor sizes for monsters
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
    "snake":          (180, 80),
    "monkeyMummy":    (140, 140),
    "lion":           (200, 140),
}

BEAR_W = 80
BEAR_H = 100

# Module-level font cache – created once after pygame.init(), reused every frame
_FONT_DAMAGE = None
_FONT_HUD = None
_FONT_BOSS_DAMAGE = None
_FONT_POPUP = None
_FONT_HUD_LABEL = None
_FONT_HUD_VAL = None
_FONT_HUD_LVL = None


def init_fonts():
    """Initialize all game fonts (call once after pygame.init())."""
    global _FONT_DAMAGE, _FONT_HUD, _FONT_BOSS_DAMAGE, _FONT_POPUP
    global _FONT_HUD_LABEL, _FONT_HUD_VAL, _FONT_HUD_LVL
    _FONT_DAMAGE = pygame.font.SysFont("Italic", 40)
    _FONT_HUD = pygame.font.SysFont("Italic", 40)
    _FONT_BOSS_DAMAGE = pygame.font.SysFont("Italic", 60)
    _FONT_POPUP = pygame.font.SysFont("Italic", 26)
    _FONT_HUD_LABEL = pygame.font.SysFont(None, 26, bold=True)
    _FONT_HUD_VAL = pygame.font.SysFont(None, 20, bold=True)
    _FONT_HUD_LVL = pygame.font.SysFont(None, 38, bold=True)


def get_font(name):
    """Retrieve a cached font by name."""
    fonts = {
        'damage': _FONT_DAMAGE,
        'hud': _FONT_HUD,
        'boss_damage': _FONT_BOSS_DAMAGE,
        'popup': _FONT_POPUP,
        'hud_label': _FONT_HUD_LABEL,
        'hud_val': _FONT_HUD_VAL,
        'hud_lvl': _FONT_HUD_LVL,
    }
    return fonts.get(name)
