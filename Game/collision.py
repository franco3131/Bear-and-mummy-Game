# -*- coding: utf-8 -*-
"""Collision detection utilities."""
import pygame
from Game.constants import _MONSTER_SIZES, BEAR_W, BEAR_H


def get_position_relative_to_monster(bear_x, bear_y, monster_x, monster_y):
    """Return position of bear relative to monster: 'TOP', 'LEFT', 'RIGHT', or None."""
    if ((bear_x > monster_x and bear_x < monster_x + 100) and bear_y < monster_y):
        return "TOP"
    elif (bear_x < monster_x and bear_y <= monster_y):
        return "LEFT"
    elif (bear_x > monster_x and bear_y <= monster_y):
        return "RIGHT"
    return None


def is_bear_hurt(position_relative, bear_x, bear_y, object_x, object_y, object_name):
    """Return True if the bear's hitbox overlaps with the named object."""
    if object_name not in _MONSTER_SIZES:
        return False
    width, height = _MONSTER_SIZES[object_name]
    bear_rect = pygame.Rect(bear_x + 5, bear_y + 5, BEAR_W - 10, BEAR_H - 10)
    obj_rect = pygame.Rect(object_x, object_y, width, height)
    return bear_rect.colliderect(obj_rect)


def is_monster_hurt(bear_x, bear_y, monster_x, monster_y, facing_left, monster_type):
    """Return True if the bear's attack hitbox overlaps with the monster."""
    if monster_type == "frankenbears":
        m_w, m_h = 300, 300
    elif monster_type == "bigMummy":
        m_w, m_h = 200, 300
    elif monster_type == "miniFrankenBear":
        m_w, m_h = 80, 80
    elif monster_type == "shadowShaman":
        m_w, m_h = 120, 120
    else:
        m_w, m_h = 100, 100

    monster_rect = pygame.Rect(monster_x, monster_y, m_w, m_h)

    # Attack reach mirrors the attack-sprite widths (190 right / 180 left)
    if not facing_left:
        attack_rect = pygame.Rect(bear_x, bear_y + 10, 190, 80)
    else:
        attack_rect = pygame.Rect(bear_x - 180, bear_y + 10, 180, 80)
    return attack_rect.colliderect(monster_rect)


def is_monster_forehead_hit(bear_x, bear_y, monster_x, monster_y, facing_left):
    """Return True only if the attack hits the big mummy's forehead (top 30%)."""
    # Forehead zone: center 120px wide, top 90px of the 200x300 sprite
    forehead_rect = pygame.Rect(monster_x + 40, monster_y, 120, 90)
    if not facing_left:
        attack_rect = pygame.Rect(bear_x, bear_y + 10, 190, 80)
    else:
        attack_rect = pygame.Rect(bear_x - 180, bear_y + 10, 180, 80)
    return attack_rect.colliderect(forehead_rect)
