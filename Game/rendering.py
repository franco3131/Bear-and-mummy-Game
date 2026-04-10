# -*- coding: utf-8 -*-
"""Rendering utilities for HUD, damage display, and world elements."""
import pygame


def render_damage_text(screen, font, damage, x, y, alpha=255):
    """Render damage text with outlined style and optional alpha fade.
    
    Uses italic fonts for cursive look. alpha: 0-255 for transparency.
    """
    txt = str(damage)
    col_black = (0, 0, 0)
    col_white = (255, 255, 255)
    w, h = font.size(txt)
    pad = 6
    surf = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    
    # Draw outline with black text at offsets
    outline_surf = font.render(txt, True, col_black)
    ox = pad
    oy = pad
    for dx, dy in ((-2, -2), (2, -2), (2, 2), (-2, 2)):
        surf.blit(outline_surf, (ox + dx, oy + dy))
    
    # Draw main white text
    main_surf = font.render(txt, True, col_white)
    surf.blit(main_surf, (ox, oy))
    
    # Apply alpha transparency
    if alpha < 255:
        surf.set_alpha(alpha)
    
    screen.blit(surf, (x - pad, y - pad))


def render_enemy_health_bar(screen, x, y, health, max_health, w=120, h=12):
    """Draw a temporary health bar beside a damage popup.
    
    Color changes based on health ratio: green (>60%), yellow (30-60%), red (<30%).
    """
    try:
        if max_health is None or max_health <= 0:
            return
        ratio = max(0.0, min(1.0, float(health) / float(max_health)))
    except Exception:
        return
    
    bar_x = x + 10
    bar_y = y + 36  # Positioned below damage text
    
    # Draw background track
    track = pygame.Rect(bar_x, bar_y, w, h)
    pygame.draw.rect(screen, (40, 30, 40), track, border_radius=3)
    
    # Draw health fill based on ratio
    fill_w = max(0, int(w * ratio))
    if fill_w > 0:
        if ratio > 0.6:
            fill_color = (60, 200, 60)  # Green
        elif ratio > 0.3:
            fill_color = (220, 200, 60)  # Yellow
        else:
            fill_color = (220, 60, 60)  # Red
        fill = pygame.Rect(bar_x, bar_y, fill_w, h)
        pygame.draw.rect(screen, fill_color, fill, border_radius=3)
    
    # Draw border
    pygame.draw.rect(screen, (200, 200, 200), track, 1, border_radius=3)


def render_hud_panel(screen, x, y, w, h, border_color, border=3):
    """Draw a HUD panel with border."""
    inner = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, (18, 14, 26), inner, border_radius=6)
    pygame.draw.rect(screen, border_color, inner, border, border_radius=6)


def render_hud_bar(screen, x, y, w, h, ratio, fill_color):
    """Draw a HUD progress bar."""
    track = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, (40, 30, 40), track, border_radius=4)
    
    fill_w = max(0, int(w * ratio))
    if fill_w > 0:
        fill = pygame.Rect(x, y, fill_w, h)
        pygame.draw.rect(screen, fill_color, fill, border_radius=4)
    
    pygame.draw.rect(screen, (200, 200, 200), track, 1, border_radius=4)


def render_hud_text_outlined(screen, font, text, x, y, color, outline=(0, 0, 0)):
    """Draw HUD text with black outline."""
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        screen.blit(font.render(text, True, outline), (x + dx, y + dy))
    screen.blit(font.render(text, True, color), (x, y))


def render_water(screen, offset):
    """Draw an animated scrolling waterstream."""
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
