"""Generate new mummy2.png – opposite-stride walk frame from mummy1.png."""
import os, shutil
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
import pygame
pygame.init()
pygame.display.set_mode((1, 1))

img = pygame.image.load('Game/Images/Mummy/mummy1.png').convert_alpha()
w, h = img.get_size()
print(f'Source mummy1.png: {w}x{h}')

# Composite: keep head+torso from mummy1, flip legs horizontally
# so the stepping foot clearly alternates (opposite stride to frame 1).
split_y = int(h * 0.62)

new2 = pygame.Surface((w, h), pygame.SRCALPHA)
new2.fill((0, 0, 0, 0))

# --- Top: head + torso (identical to mummy1 so bandage wraps match) ---
new2.blit(img, (0, 0), pygame.Rect(0, 0, w, split_y))

# --- Bottom: legs cropped from mummy1 then flipped left<->right ---
bot = pygame.Surface((w, h - split_y), pygame.SRCALPHA)
bot.fill((0, 0, 0, 0))
bot.blit(img, (0, 0), pygame.Rect(0, split_y, w, h - split_y))
bot_flip = pygame.transform.flip(bot, True, False)
new2.blit(bot_flip, (0, split_y))

out = 'Game/Images/Mummy/mummy2.png'
shutil.copy(out, out + '.bak')
pygame.image.save(new2, out)
print(f'Saved {out}')
pygame.quit()
