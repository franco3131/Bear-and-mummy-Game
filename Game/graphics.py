# -*- coding: utf-8 -*-
"""Graphics utilities for sprite scaling and effects."""
import pygame


def scale_image_to_box(img, target_w, target_h):
    """Scale image to fit target box preserving aspect ratio.
    
    Scales by height first, then centers or pads width as needed.
    Returns a surface of exactly (target_w, target_h).
    """
    iw, ih = img.get_size()
    scale = target_h / ih
    nw = max(1, int(iw * scale))
    scaled = pygame.transform.scale(img, (nw, target_h))
    
    surf = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
    if nw >= target_w:
        # Crop from center if too wide
        ox = (nw - target_w) // 2
        surf.blit(scaled, (0, 0), (ox, 0, target_w, target_h))
    else:
        # Pad from center if too narrow
        ox = (target_w - nw) // 2
        surf.blit(scaled, (ox, 0))
    return surf


def create_outline_surface(sprite, color=(255, 255, 255, 220)):
    """Create an outline surface matching sprite's silhouette.
    
    Returns a new surface with a colored outline matching the sprite's shape.
    """
    mask = pygame.mask.from_surface(sprite)
    w, h = sprite.get_size()
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    white_fill = mask.to_surface(setcolor=color, unsetcolor=(0, 0, 0, 0))
    
    # Draw outline with multiple offsets for thickness
    for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2),
                   (-2, -2), (2, -2), (-2, 2), (2, 2)):
        out.blit(white_fill, (dx, dy))
    return out
