# -*- coding: utf-8 -*-
"""Utility functions for collision detection and rendering."""
import pygame
from Game.constants import _MONSTER_SIZES, BEAR_W, BEAR_H


def scale_to_box(img, target_w, target_h):
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


def make_outline_surf(sprite, color=(255, 255, 255, 220)):
    """Return a surface with a white outline matching the sprite's silhouette."""
    mask = pygame.mask.from_surface(sprite)
    w, h = sprite.get_size()
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    white_fill = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2),
                   (-2, -2), (2, -2), (-2, 2), (2, 2)):
        out.blit(white_fill, (dx, dy))
    return out


def positionRelativeToMonster(bearXPosition, bearYPosition, mummyXPosition,
                              mummyYPosition):
    if ((bearXPosition > mummyXPosition
         and bearXPosition < mummyXPosition + 100)
            and bearYPosition < mummyYPosition):
        return "TOP"
    elif (bearXPosition < mummyXPosition and bearYPosition <= mummyYPosition):
        return "LEFT"
    elif (bearXPosition > mummyXPosition and bearYPosition <= mummyYPosition):
        return "RIGHT"


def isBearHurt(positionRelative, bearXPosition, bearYPosition,
               objectXPosition, objectYPosition, objectName):
    """Return True if the bear's hitbox overlaps with the named object."""
    if objectName not in _MONSTER_SIZES:
        return False
    width, height = _MONSTER_SIZES[objectName]
    bear_rect = pygame.Rect(bearXPosition + 5, bearYPosition + 5,
                            BEAR_W - 10, BEAR_H - 10)
    obj_rect = pygame.Rect(objectXPosition, objectYPosition, width, height)
    return bear_rect.colliderect(obj_rect)


def isMonsterHurt(bearXPosition, bearYPosition, mummyXPosition, mummyYPosition,
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


def isMonsterForeheadHit(bearXPosition, bearYPosition, mummyXPosition,
                         mummyYPosition, facingLeft):
    """Return True only if the attack hits the big mummy's forehead (top 30%)."""
    # Forehead zone: center 120px wide, top 90px of the 200x300 sprite
    forehead_rect = pygame.Rect(mummyXPosition + 40, mummyYPosition, 120, 90)
    if not facingLeft:
        attack_rect = pygame.Rect(bearXPosition, bearYPosition + 10, 190, 80)
    else:
        attack_rect = pygame.Rect(bearXPosition - 180, bearYPosition + 10,
                                  180, 80)
    return attack_rect.colliderect(forehead_rect)


def render_damage_text(screen, font, damage, x, y, alpha=255):
    """Render damage text with an outlined style and optional alpha fade.
    Uses italic fonts for cursive look. alpha: 0-255 for transparency.
    """
    txt = str(damage)
    col_black = (0, 0, 0)
    col_white = (255, 255, 255)
    w, h = font.size(txt)
    pad = 6
    surf = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    outline_surf = font.render(txt, True, col_black)
    ox = pad
    oy = pad
    for dx, dy in ((-2, -2), (2, -2), (2, 2), (-2, 2)):
        surf.blit(outline_surf, (ox + dx, oy + dy))
    main_surf = font.render(txt, True, col_white)
    surf.blit(main_surf, (ox, oy))
    if alpha < 255:
        surf.set_alpha(alpha)
    screen.blit(surf, (x - pad, y - pad))


def render_enemy_health_bar(screen, x, y, health, max_health, w=120, h=12):
    """Draw a small temporary health bar beside a damage popup."""
    try:
        if max_health is None or max_health <= 0:
            return
        ratio = max(0.0, min(1.0, float(health) / float(max_health)))
    except Exception:
        return
    bar_x = x + 10
    bar_y = y + 36
    track = pygame.Rect(bar_x, bar_y, w, h)
    pygame.draw.rect(screen, (40, 30, 40), track, border_radius=3)
    fill_w = max(0, int(w * ratio))
    if fill_w > 0:
        if ratio > 0.6:
            fill_color = (60, 200, 60)
        elif ratio > 0.3:
            fill_color = (220, 200, 60)
        else:
            fill_color = (220, 60, 60)
        fill = pygame.Rect(bar_x, bar_y, fill_w, h)
        pygame.draw.rect(screen, fill_color, fill, border_radius=3)
    pygame.draw.rect(screen, (200, 200, 200), track, 1, border_radius=3)


def hud_panel(screen, x, y, w, h, border_color, border=3):
    """Draw a HUD panel."""
    inner = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, (18, 14, 26), inner, border_radius=6)
    pygame.draw.rect(screen, border_color, inner, border, border_radius=6)


def hud_bar(screen, x, y, w, h, ratio, fill_color):
    """Draw a HUD progress bar."""
    track = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, (40, 30, 40), track, border_radius=4)
    fill_w = max(0, int(w * ratio))
    if fill_w > 0:
        fill = pygame.Rect(x, y, fill_w, h)
        pygame.draw.rect(screen, fill_color, fill, border_radius=4)
    pygame.draw.rect(screen, (200, 200, 200), track, 1, border_radius=4)


def hud_text_outlined(screen, font, text, x, y, color, outline=(0, 0, 0)):
    """Draw HUD text with outline."""
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        screen.blit(font.render(text, True, outline), (x + dx, y + dy))
    screen.blit(font.render(text, True, color), (x, y))


def draw_water(screen, offset):
    """Draw animated scrolling waterstream."""
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
