import pygame
import random

# ---------------------------------------------------------------------------
# Movement step – pixels per frame for walking/world-scroll
# Smaller value = smoother, slower feel. Jump step is kept separate.
# ---------------------------------------------------------------------------
STEP = 8
JUMP_STEP = 7

# ---------------------------------------------------------------------------
# Module-level font cache – created once after pygame.init(), reused every frame
# ---------------------------------------------------------------------------
_FONT_DAMAGE = None
_FONT_HUD = None
_FONT_BOSS_DAMAGE = None
_FONT_POPUP = None


def _init_fonts():
    global _FONT_DAMAGE, _FONT_HUD, _FONT_BOSS_DAMAGE, _FONT_POPUP
    _FONT_DAMAGE = pygame.font.SysFont("Italic", 40)
    _FONT_HUD = pygame.font.SysFont("Italic", 40)
    _FONT_BOSS_DAMAGE = pygame.font.SysFont("Italic", 60)
    _FONT_POPUP = pygame.font.SysFont("Italic", 26)


# ---------------------------------------------------------------------------
# Collision helpers (using pygame.Rect for clean, accurate AABB detection)
# ---------------------------------------------------------------------------
_MONSTER_SIZES = {
    "mummy":        (100, 100),
    "bigMummy":     (200, 300),
    "fireBall":     (60,  60),
    "witch":        (100, 100),
    "greenBlob":    (100, 100),
    "bigGreenBlob": (300, 400),
    "spikes":       (600, 60),
    "frankenbears": (300, 300),
}

BEAR_W = 80
BEAR_H = 100


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


# ---------------------------------------------------------------------------
# Damage text helper – drawn once instead of duplicated across every class
# ---------------------------------------------------------------------------
def _render_damage_text(screen, font, damage, x, y):
    black = pygame.Color(0, 0, 0)
    white = pygame.Color(255, 255, 255)
    outline = font.render(str(damage), True, black)
    for dx, dy in ((-2, -2), (2, -2), (2, 2), (-2, 2)):
        screen.blit(outline, (x + dx, y + dy))
    screen.blit(font.render(str(damage), True, white), (x, y))


# ---------------------------------------------------------------------------
# Main game class
# ---------------------------------------------------------------------------

class mainGame:
    def __init__(self):
        pygame.init()
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.thud_sound = pygame.mixer.Sound("Game/Sounds/thud.wav")
            self.thud_sound.set_volume(0.75)
            pygame.mixer.music.load("Game/Sounds/music.wav")
            pygame.mixer.music.set_volume(0.45)
            pygame.mixer.music.play(-1)   # loop forever
        except Exception:
            self.thud_sound = None   # no audio device – run silently
        _init_fonts()

        self.screen = pygame.display.set_mode((900, 700), pygame.DOUBLEBUF)
        self.clock = pygame.time.Clock()

        self.standingBear = pygame.image.load("Game/Images/Bear/standBear2.png")
        self.standingBear = pygame.transform.scale(self.standingBear, (105, 100))
        self.standingBearLeft = pygame.transform.flip(self.standingBear, True, False)

        self.bearWalking1 = pygame.image.load("Game/Images/Bear/bearWalking1.png")
        self.bearWalking1 = pygame.transform.scale(self.bearWalking1, (120, 115))
        self.bearWalking2 = pygame.image.load("Game/Images/Bear/bearWalking2.png")
        self.bearWalking2 = pygame.transform.scale(self.bearWalking2, (120, 115))
        self.bearWalking3 = pygame.image.load("Game/Images/Bear/bearWalking3.png")
        self.bearWalking3 = pygame.transform.scale(self.bearWalking3, (120, 115))

        self.screen.fill((255, 255, 255))
        pygame.display.update()

        self.bearWalkingLeft1 = pygame.transform.flip(self.bearWalking1, True, False)
        self.bearWalkingLeft2 = pygame.transform.flip(self.bearWalking2, True, False)
        self.bearWalkingLeft3 = pygame.transform.flip(self.bearWalking3, True, False)

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
        self.greenBlobs = []
        self.witches = []
        self.blocks = []
        self.frankenbear = []

        self.fireBall = pygame.image.load("Game/Images/fire3.png")
        self.fireBossBall = pygame.image.load("Game/Images/fire4.png")

        self.screen.fill((255, 255, 255))
        pygame.display.update()

        self.showBoss = True
        self.triggerText1 = False
        self.triggerText2 = False
        self.triggerText3 = False
        self.triggerText4 = False
        self.triggerText5 = False
        self.createdBoss = False
        self.leftBoundary = 180
        self.rightBoundary = 300
        self.isFinalBossDestroyed = False

    # -----------------------------------------------------------------------
    # Helper: draw the bear idle sprite (used to fill animation gaps)
    # -----------------------------------------------------------------------
    def _draw_idle_bear(self, bear):
        if not bear.getLeftDirection():
            self.screen.blit(self.standingBear,
                             (bear.getXPosition(), bear.getYPosition()))
        else:
            self.screen.blit(self.standingBearLeft,
                             (bear.getXPosition(), bear.getYPosition()))

    def runGame(self):
        self.triggerFire = False
        floorHeight = 400
        continueLoop = True
        bear = Bear(60, 300, self.screen)
        bear.setJumpStatus(False)
        bear.setLeftJumpStatus(False)

        attackingAnimationCounter = 0
        attackingLeftAnimtationCounter = 0
        hurtTimer = 0
        background = Background(self.screen)
        for x in [500, 750]:
            mummy = Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen)
            self.mummys.append(mummy)

        self.activeMonsters = [False] * 14

        # Initial obstacle platforms – each clearly separated with ~80 px gaps
        block1 = Block(280,  340, 100, 60,  "red",     self.screen)
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
        deflectTimer = 0
        deflectPos = (0, 0)

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

            background.render(totalDistance)

            if bear.getEndText():

                keys = pygame.key.get_pressed()

                # ---- Z + RIGHT: jump-right --------------------------------
                if keys[pygame.K_z] and keys[pygame.K_RIGHT]:
                    airborne = bear.getJumpStatus() or bear.getLeftJumpStatus()
                    if airborne:
                        # ---- Already in the air: move right every frame ----
                        totalDistance += STEP
                        if bear.getXPosition() < self.rightBoundary:
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                            bear.setXPosition(bear.getXPosition() + STEP)
                            backgroundScrollX = bear.getXPosition() - STEP
                            background.setXPosition(backgroundScrollX)
                        else:
                            moveObjects = (self.mummys + self.fires + self.witches +
                                           self.greenBlobs + self.door + self.keys + self.spikes)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() - STEP)
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                if not block.getIsLeftBoundary():
                                    block.setblockXPosition(block.getBlockXPosition() - STEP)
                                    backgroundScrollX = bear.getXPosition() + STEP
                                    background.setXPosition(backgroundScrollX)

                    elif jumpTimer > 12:
                        # ---- On the ground: start a new jump (cooldown gated) ----
                        totalDistance += STEP
                        if bear.getXPosition() < self.rightBoundary:
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                if block.getIsLeftBoundary():
                                    bear.setXPosition(bear.getXPosition() - STEP)
                                    totalDistance -= STEP
                            backgroundScrollX = bear.getXPosition() - STEP
                            background.setXPosition(backgroundScrollX)
                            bear.setXPosition(bear.getXPosition() + STEP)
                        else:
                            moveObjects = (self.mummys + self.fires + self.witches +
                                           self.greenBlobs + self.door + self.keys + self.spikes)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() - STEP)
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                if not block.getIsLeftBoundary():
                                    block.setblockXPosition(block.getBlockXPosition() - STEP)
                                    backgroundScrollX = bear.getXPosition() + STEP
                                    background.setXPosition(backgroundScrollX)
                        backgroundScrollX -= STEP
                        background.setXPosition(backgroundScrollX)
                        bear.setJumpStatus(True)
                        bear.startJump()
                        jumpTimer = 0
                        background.update(bear.getXPosition(), bear.getYPosition())

                    # Only enforce side-wall collision on the ground, not mid-arc
                    if not bear.getJumpStatus() and not bear.getLeftJumpStatus():
                        for block in self.blocks:
                            if block.getIsLeftBoundary():
                                bear.setXPosition(bear.getXPosition() - STEP)
                                totalDistance += STEP

                    dangerousObjects = (self.mummys + self.fires + self.witches +
                                        self.greenBlobs + self.spikes + self.bossFires +
                                        self.frankenbear)
                    for monster in dangerousObjects:
                        if (bear.isBearHurt("RIGHT", bear.getXPosition(), bear.getYPosition(),
                                            monster.getXPosition(), monster.getYPosition(),
                                            monster.getName()) and hurtTimer > 25):
                            hurtTimer = 0
                            bear.displayDamageOnBear(monster.getDamageAttack())
                            bear.setHp(bear.getHp() - monster.getDamageAttack())
                            self.screen.blit(self.hurtBear,
                                             (bear.getXPosition(), bear.getYPosition()))
                            if bear.getXPosition() <= 400:
                                bear.setXPosition(bear.getXPosition() + STEP)
                                totalDistance += STEP
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                                bear.displayDamageOnBear(monster.getDamageAttack())
                            monster.setHurtTimer(monster.getHurtTimer() + 1)
                        elif 0 < monster.getHurtTimer() < 15:
                            monster.setHurtTimer(monster.getHurtTimer() + 1)
                            bear.displayDamageOnBear(monster.getDamageAttack())
                            self.screen.blit(self.hurtBear,
                                             (bear.getXPosition(), bear.getYPosition()))
                        else:
                            monster.setHurtTimer(0)
                        bear.setLeftDirection(False)

                    background.update(bear.getXPosition(), bear.getYPosition())

                # ---- Z + LEFT: jump-left ---------------------------------
                elif keys[pygame.K_z] and keys[pygame.K_LEFT]:
                    airborne = bear.getJumpStatus() or bear.getLeftJumpStatus()
                    if airborne:
                        # ---- Already in the air: move left every frame ----
                        totalDistance -= STEP
                        if bear.getXPosition() > self.leftBoundary:
                            bear.setXPosition(bear.getXPosition() - STEP)
                            backgroundScrollX = bear.getXPosition() + STEP
                            background.setXPosition(backgroundScrollX)
                        else:
                            moveObjects = (self.mummys + self.fires + self.witches +
                                           self.greenBlobs + self.door + self.keys + self.spikes)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() + STEP)
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                if not block.getIsRightBoundary():
                                    block.setblockXPosition(block.getBlockXPosition() + STEP)
                                    backgroundScrollX = bear.getXPosition() - STEP
                                    background.setXPosition(backgroundScrollX)
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)

                    elif jumpTimer > 12:
                        # ---- On the ground: start a new jump (cooldown gated) ----
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
                                           self.greenBlobs + self.spikes)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() + STEP)
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
                        bear.startJump()

                    # Only enforce side-wall collision on the ground, not mid-arc
                    if not bear.getJumpStatus() and not bear.getLeftJumpStatus():
                        for block in self.blocks:
                            if block.getIsRightBoundary():
                                bear.setXPosition(bear.getXPosition() + STEP)
                                totalDistance += STEP

                        dangerousObjects = (self.mummys + self.fires + self.witches +
                                            self.greenBlobs + self.spikes + self.bossFires +
                                            self.frankenbear)
                        for monster in dangerousObjects:
                            if (bear.isBearHurt("RIGHT", bear.getXPosition(), bear.getYPosition(),
                                                monster.getXPosition(), monster.getYPosition(),
                                                monster.getName()) and hurtTimer > 25):
                                hurtTimer = 0
                                bear.displayDamageOnBear(monster.getDamageAttack())
                                bear.setHp(bear.getHp() - monster.getDamageAttack())
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
                                bear.displayDamageOnBear(monster.getDamageAttack())
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                            else:
                                monster.setHurtTimer(0)
                            bear.setLeftDirection(True)
                            bear.setLeftJumpStatus(True)
                            bear.startJump()

                    background.update(backgroundScrollX, bear.getYPosition())

                # ---- Z only: vertical jump --------------------------------
                elif (keys[pygame.K_z]
                      and not bear.getJumpStatus()
                      and not bear.getLeftJumpStatus()
                      and jumpTimer > 12):
                    jumpTimer = 0
                    bear.setJumpStatus(True)
                    bear.setLeftJumpStatus(True)
                    bear.startJump()
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
                    monsters = self.mummys + self.witches + self.greenBlobs + self.frankenbear
                    for monster in monsters:
                        if isMonsterHurt(bear.getXPosition(), bear.getYPosition(),
                                         monster.getXPosition(), monster.getYPosition(),
                                         bear.getLeftDirection(), monster.getName()):
                            if monster.getName() == "bigMummy":
                                if isMonsterForeheadHit(bear.getXPosition(), bear.getYPosition(),
                                                        monster.getXPosition(), monster.getYPosition(),
                                                        bear.getLeftDirection()):
                                    monster.setDamageReceived(bear.getDamageAttack())
                                    monster.setStunned(1)
                                    monster.setHealth(monster.getHealth() - bear.getDamageAttack())
                                    hurtTimer = 0
                                else:
                                    deflectTimer = 40
                                    deflectPos = (monster.getXPosition() + 70, monster.getYPosition() + 120)
                            else:
                                if not self.frankenbear:
                                    monster.setXPosition(monster.getXPosition() + STEP)
                                monster.setDamageReceived(bear.getDamageAttack())
                                monster.setStunned(1)
                                monster.setHealth(monster.getHealth() - bear.getDamageAttack())
                                hurtTimer = 0
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
                    monsters = self.mummys + self.witches + self.greenBlobs + self.frankenbear
                    for monster in monsters:
                        if isMonsterHurt(bear.getXPosition(), bear.getYPosition(),
                                         monster.getXPosition(), monster.getYPosition(),
                                         bear.getLeftDirection(), monster.getName()):
                            if monster.getName() == "bigMummy":
                                if isMonsterForeheadHit(bear.getXPosition(), bear.getYPosition(),
                                                        monster.getXPosition(), monster.getYPosition(),
                                                        bear.getLeftDirection()):
                                    monster.setDamageReceived(bear.getDamageAttack())
                                    monster.setStunned(1)
                                    monster.setHealth(monster.getHealth() - bear.getDamageAttack())
                                    hurtTimer = 0
                                else:
                                    deflectTimer = 40
                                    deflectPos = (monster.getXPosition() + 70, monster.getYPosition() + 120)
                            else:
                                if not self.frankenbear:
                                    monster.setXPosition(monster.getXPosition() + STEP)
                                monster.setDamageReceived(bear.getDamageAttack())
                                monster.setStunned(1)
                                monster.setHealth(monster.getHealth() - bear.getDamageAttack())
                                hurtTimer = 0
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
                                           self.greenBlobs + self.door + self.keys + self.spikes)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() - STEP)
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
                            for b in self.blocks:
                                b.setblockXPosition(b.getBlockXPosition() + STEP)
                            totalDistance += STEP
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)

                        _walkFrame = (bearAnimation // 11) % 3
                        _walkImgs = [self.bearWalking1, self.bearWalking2, self.bearWalking3]
                        self.screen.blit(_walkImgs[_walkFrame],
                                         (bear.getXPosition(), bear.getYPosition() - 10))

                        dangerousObjects = (self.mummys + self.fires + self.witches +
                                            self.greenBlobs + self.spikes + self.bossFires +
                                            self.frankenbear)
                        for monster in dangerousObjects:
                            if (bear.isBearHurt("RIGHT", bear.getXPosition(), bear.getYPosition(),
                                                monster.getXPosition(), monster.getYPosition(),
                                                monster.getName()) and hurtTimer > 25):
                                hurtTimer = 0
                                bear.displayDamageOnBear(monster.getDamageAttack())
                                bear.setHp(bear.getHp() - monster.getDamageAttack())
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                                bear.setXPosition(bear.getXPosition() - STEP)
                                totalDistance -= STEP
                                monster.setHurtTimer(monster.getHurtTimer() + 1)
                            elif 0 < monster.getHurtTimer() < 15:
                                monster.setHurtTimer(monster.getHurtTimer() + 1)
                                bear.displayDamageOnBear(monster.getDamageAttack())
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                            else:
                                monster.setHurtTimer(0)

                    elif bear.getJumpStatus() or bear.getLeftJumpStatus():
                        if bear.getXPosition() < self.rightBoundary:
                            jumpTimer = 0
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                if block.getIsLeftBoundary():
                                    bear.setXPosition(bear.getXPosition() - STEP)
                                    totalDistance -= STEP
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)
                            bear.setXPosition(bear.getXPosition() + STEP)
                        else:
                            jumpTimer = 0
                            moveObjects = (self.mummys + self.fires + self.witches +
                                           self.greenBlobs + self.door + self.keys + self.spikes)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() - STEP)
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                if not block.getIsLeftBoundary():
                                    block.setblockXPosition(block.getBlockXPosition() - STEP)
                                    backgroundScrollX = bear.getXPosition()
                                    background.setXPosition(backgroundScrollX)
                                elif block.getIsLeftBoundary():
                                    block.setblockXPosition(block.getBlockXPosition() - STEP)
                                    backgroundScrollX = bear.getXPosition()
                                    background.setXPosition(backgroundScrollX)

                        for block in self.blocks:
                            block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                            if block.getIsLeftBoundary():
                                bear.setXPosition(bear.getXPosition() - STEP)
                                totalDistance -= STEP

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
                                           self.greenBlobs + self.door + self.keys + self.spikes)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() + STEP)
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
                            for b in self.blocks:
                                b.setblockXPosition(b.getBlockXPosition() - STEP)
                            totalDistance -= STEP
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)

                        _walkFrame = (bearAnimation // 11) % 3
                        _walkLeftImgs = [self.bearWalkingLeft1, self.bearWalkingLeft2, self.bearWalkingLeft3]
                        self.screen.blit(_walkLeftImgs[_walkFrame],
                                         (bear.getXPosition(), bear.getYPosition() - 10))

                        dangerousObjects = (self.mummys + self.fires + self.witches +
                                            self.greenBlobs + self.spikes + self.bossFires +
                                            self.frankenbear)
                        for monster in dangerousObjects:
                            if (bear.isBearHurt("RIGHT", bear.getXPosition(), bear.getYPosition(),
                                                monster.getXPosition(), monster.getYPosition(),
                                                monster.getName()) and hurtTimer > 25):
                                bear.displayDamageOnBear(monster.getDamageAttack())
                                bear.setHp(bear.getHp() - monster.getDamageAttack())
                                hurtTimer = 0
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                                bear.setXPosition(bear.getXPosition() + STEP)
                                totalDistance += STEP
                                monster.setHurtTimer(monster.getHurtTimer() + 1)
                            elif 0 < monster.getHurtTimer() < 15:
                                monster.setHurtTimer(monster.getHurtTimer() + 1)
                                bear.displayDamageOnBear(monster.getDamageAttack())
                                self.screen.blit(self.hurtBear,
                                                 (bear.getXPosition(), bear.getYPosition()))
                            else:
                                monster.setHurtTimer(0)

                    elif bear.getJumpStatus() or bear.getLeftJumpStatus():
                        jumpTimer = 0
                        if bear.getXPosition() > self.leftBoundary:
                            backgroundScrollX = bear.getXPosition() + STEP
                            background.setXPosition(backgroundScrollX)
                            bear.setXPosition(bear.getXPosition() - STEP)
                        else:
                            moveObjects = (self.mummys + self.fires + self.greenBlobs +
                                           self.witches + self.door + self.keys + self.spikes)
                            for obj in moveObjects:
                                obj.setXPosition(obj.getXPosition() + STEP)
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                if not block.getIsRightBoundary():
                                    block.setblockXPosition(block.getBlockXPosition() + STEP)
                                    backgroundScrollX = bear.getXPosition()
                                    background.setXPosition(backgroundScrollX)
                                elif block.getIsRightBoundary():
                                    block.setblockXPosition(block.getBlockXPosition() + STEP)
                                    totalDistance += STEP
                                    backgroundScrollX = bear.getXPosition()
                                    background.setXPosition(backgroundScrollX)
                        for block in self.blocks:
                            block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                            if block.getIsRightBoundary():
                                bear.setXPosition(bear.getXPosition() + STEP)
                                totalDistance += STEP

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
                    monsters = self.mummys + self.witches + self.greenBlobs + self.frankenbear
                    for monster in monsters:
                        if isMonsterHurt(bear.getXPosition(), bear.getYPosition(),
                                         monster.getXPosition(), monster.getYPosition(),
                                         bear.getLeftDirection(), monster.getName()):
                            if monster.getName() == "bigMummy":
                                if isMonsterForeheadHit(bear.getXPosition(), bear.getYPosition(),
                                                        monster.getXPosition(), monster.getYPosition(),
                                                        bear.getLeftDirection()):
                                    monster.setDamageReceived(bear.getDamageAttack())
                                    monster.setStunned(1)
                                    monster.setHealth(monster.getHealth() - bear.getDamageAttack())
                                    hurtTimer = 0
                                else:
                                    deflectTimer = 40
                                    deflectPos = (monster.getXPosition() + 70, monster.getYPosition() + 120)
                            else:
                                if not self.frankenbear:
                                    monster.setXPosition(monster.getXPosition() + STEP)
                                monster.setDamageReceived(bear.getDamageAttack())
                                monster.setStunned(1)
                                monster.setHealth(monster.getHealth() - bear.getDamageAttack())
                                hurtTimer = 0

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
                                        self.frankenbear)
                    for monster in dangerousObjects:
                        if (bear.isBearHurt("LEFT", bear.getXPosition(), bear.getYPosition(),
                                            monster.getXPosition(), monster.getYPosition(),
                                            monster.getName()) and hurtTimer > 25):
                            bear.displayDamageOnBear(monster.getDamageAttack())
                            bear.setHp(bear.getHp() - monster.getDamageAttack())
                            hurtTimer = 0
                            self.screen.blit(self.hurtBear,
                                             (bear.getXPosition(), bear.getYPosition()))
                            rel = positionRelativeToMonster(
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
                            bear.displayDamageOnBear(monster.getDamageAttack())
                            self.screen.blit(self.hurtBear,
                                             (bear.getXPosition(), bear.getYPosition()))
                        else:
                            monster.setHurtTimer(0)

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
                # Draw idle sprite on the reset frame so the bear never vanishes
                self._draw_idle_bear(bear)
            elif 1 <= attackingLeftAnimtationCounter < 12:
                attackingLeftAnimtationCounter += 1
                self.screen.blit(self.bearAttackingLeft,
                                 (bear.getXPosition(), bear.getYPosition()))
            elif attackingLeftAnimtationCounter >= 12:
                attackingLeftAnimtationCounter = 0
                # Draw idle sprite on the reset frame so the bear never vanishes
                self._draw_idle_bear(bear)
            elif bear.getJumpStatus():
                bear.jump(self.blocks)
            elif bear.getLeftJumpStatus():
                bear.leftJump(self.blocks)

            # ---- Boundary and timer updates ------------------------------
            bear.boundaryExtraCheck()
            jumpTimer += 1

            # ---- Monster lifecycle ---------------------------------------
            for mummy in self.mummys:
                mummy.setBlocks(self.blocks)

            monsters = self.mummys + self.witches + self.greenBlobs
            to_remove = []
            for monster in monsters:
                if monster.getHealth() > 0:
                    monster.drawMonster()
                elif (monster.getHealth() <= 0
                      and monster.getDestructionAnimationCount() < 20
                      and not monster.getStartDestructionAnimationStatus()):
                    monster.setStartDestructionAnimation(True)
                elif monster.getStartDestructionAnimationStatus():
                    monster.drawDestruction(bear.getDamageAttack())
                    if monster.getDestructionAnimationCount() >= 30:
                        monster.setStartDestructionAnimation(False)
                        bear.setCurrentExp(bear.getCurrentExp() + monster.getExp())
                        to_remove.append(monster)
                else:
                    to_remove.append(monster)

            for monster in to_remove:
                if monster in self.mummys:
                    self.mummys.remove(monster)
                elif monster in self.witches:
                    self.witches.remove(monster)
                elif monster in self.greenBlobs:
                    self.greenBlobs.remove(monster)

                if monster.getName() == "greenBlob" and monster.getHeight() == 100:
                    self.greenBlobs.append(
                        GreenBlob(monster.getXPosition() - 40, 350, 70, 100, self.screen))
                    self.greenBlobs.append(
                        GreenBlob(monster.getXPosition() + 40, 350, 70, 100, self.screen))
                elif monster.getName() == "bigMummy":
                    self.keys.append(
                        KeyItem(self.screen, monster.getXPosition(), monster.getYPosition()))

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
                elif monster.getStartDestructionAnimationStatus():
                    monster.drawDestruction(bear.getDamageAttack())
                    if monster.getDestructionAnimationCount() >= 30:
                        monster.setStartDestructionAnimation(False)
                        bear.setCurrentExp(bear.getCurrentExp() + monster.getExp())
                        boss_to_remove.append(monster)
                        bear.setArrayText(['Thank you for playing!', '',
                                           'Press "s" to continue'])
                        bear.setArrayText(['The screen will close now', '',
                                           'Press "s" to continue'])
                        bear.setEndText(False)
                        self.isFinalBossDestroyed = True
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
                for witch in self.witches:
                    witch.setThrowsFireBalls(True)
                    for _ in range(3):
                        self.fires.append(
                            FireBall(witch.getXPosition(), witch.getYPosition(),
                                     random.randint(-7, 7), random.randint(1, 12),
                                     self.fireBall, self.screen))

            for witch in self.witches:
                witch.drawMonster()

            hurtTimer += 1

            # ---- Boss trigger zone (scaled to STEP-based totalDistance) --
            # Original triggers were designed for 30px steps; scaled to 8px steps
            # by multiplying by (8/30) ≈ 0.267. Zone triggers ÷ ~3.75.
            if 17840 < totalDistance < 17870 and not self.createdBoss:
                self.createdBoss = True

            if totalDistance > 17870 and not self.activeMonsters[9]:
                self.spikes = []
                self.activeMonsters[9] = True
                self.mummys = []
                self.witches = []
                self.blocks = []
                self.greenBlobs = []
                self.fires = []
                self.activeMonsters[1] = True

            if totalDistance > 17870:
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
                        frankenbear = FrankenBear(300, 40, self.screen)
                        self.frankenbear.append(frankenbear)
                        self.showBoss = False
                    for frankenbear in self.frankenbear:
                        frankenbear.drawMonster()
                        if frankenbear.getThrowFireBallLeft() and not self.bossFires:
                            frankenbear.setThrowFireBallLeft(False)
                            volley = 7 if frankenbear.getHealth() <= 3 else 5
                            for _ in range(volley):
                                self.bossFires.append(
                                    FireBall(frankenbear.getXPosition() + 200,
                                             frankenbear.getYPosition() + 100,
                                             random.randint(-24, -4),
                                             random.randint(6, 14),
                                             self.fireBossBall, self.screen))
                        elif frankenbear.getThrowFireBallRight() and not self.bossFires:
                            frankenbear.setThrowFireBallLeft(False)
                            volley = 7 if frankenbear.getHealth() <= 3 else 5
                            for _ in range(volley):
                                self.bossFires.append(
                                    FireBall(frankenbear.getXPosition() + 200,
                                             frankenbear.getYPosition() + 100,
                                             random.randint(4, 24),
                                             random.randint(6, 14),
                                             self.fireBossBall, self.screen))

                    boss_fires_to_remove = []
                    for fire in self.bossFires:
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

            # ---- Platforms and gravity ----------------------------------
            for block in self.blocks:
                block.drawRectangle()
                # Only run boundary logic on the ground.  While airborne,
                # _jumpPhysics() is the sole authority on vertical state;
                # calling isBoundaryPresent() mid-air can corrupt dropStatus
                # the instant _jumpPhysics() sets jumpStatus=False, causing the
                # bear to fall straight through a platform it just landed on.
                if not bear.getJumpStatus() and not bear.getLeftJumpStatus():
                    block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
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

            bear.displayBearHp()
            bear.displayBearExp()

            # ---- Story / trigger text (triggers scaled to 8px steps) ----
            if totalDistance > 2300 and not self.triggerText1:
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
                for mummy in self.mummys:
                    if (door.getXPosition() - 90 <= bear.getXPosition()
                            and not self.isDoor1Open
                            and not self.triggerText3):
                        totalDistance -= STEP
                        if not self.triggerText3 and not self.isDoor1Open:
                            bear.setArrayText(['Attack the mummy\'s forehead!', '',
                                               'Press "s" to continue'])
                            bear.setArrayText(['Hit it to grab the key',
                                               'for the locked door.',
                                               'Press "s" to continue'])
                            self.triggerText3 = True
                            bear.setEndText(False)

                if self.isDoor1Open and not self.triggerText2:
                    bear.setArrayText(['Grabbed the key!', '',
                                       'Press "s" to continue'])
                    bear.setArrayText(['You can open the door now.', '',
                                       'Press "s" to continue'])
                    self.triggerText2 = True
                    bear.setEndText(False)
                elif (self.isDoor1Open
                      and door.getXPosition() - 90 <= bear.getXPosition()
                      and not self.triggerText5):
                    bear.setXPosition(bear.getXPosition() - STEP)
                    totalDistance -= STEP
                    self.triggerText5 = True
                    bear.setArrayText(['You used the key!', '',
                                       'Press "s" to continue'])
                    bear.setArrayText(['The door is unlocked.', '',
                                       'Press "s" to continue'])
                    bear.setEndText(False)

            if not bear.getEndText():
                bear.displayTextBox()

            if bear.getHealth() <= 0 and not self.triggerText4:
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

            pygame.display.flip()
            self.clock.tick(60)

    # -----------------------------------------------------------------------
    def deleteAndCreateObjects(self, backgroundScrollX):
        # Zones are ordered in ascending scroll distance with ~4 000+ unit gaps
        # so they never overlap or interfere with one another.

        # ── Zone 1 @ 3 800 – big mummy flanked by monster blocks ─────────────
        if backgroundScrollX > 3800 and not self.activeMonsters[1]:
            self.activeMonsters[1] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []

            block_left  = Block(650,  250, 130, 150, "monster", self.screen)
            block_right = Block(1420, 250, 130, 150, "monster", self.screen)
            self.blocks.extend([block_left, block_right])

            mummy = Mummy(1000, 100, 200, 300, self.mummy1, self.mummy2, self.screen)
            self.mummys.append(mummy)

            self.door1 = Door(self.screen, 1650)
            self.door.append(self.door1)

        # ── Zone 2 @ 7 000 – green blobs on a rock platform ──────────────────
        elif backgroundScrollX > 7000 and not self.activeMonsters[3]:
            self.activeMonsters[3] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []

            block1 = Block(400,  340, 900,  60, "greyRock", self.screen)
            block2 = Block(1300, 220, 2000, 60, "greyRock", self.screen)
            self.blocks.extend([block1, block2])

            greenBlob  = GreenBlob(450,  300, 100, 100, self.screen)
            greenBlob2 = GreenBlob(650,  300, 100, 100, self.screen)
            greenBlob3 = GreenBlob(850,  300, 100, 100, self.screen)
            greenBlob4 = GreenBlob(1100, 300, 100, 100, self.screen)
            greenBlob5 = GreenBlob(1400, 300, 100, 100, self.screen)
            self.greenBlobs.extend([greenBlob, greenBlob2, greenBlob3,
                                    greenBlob4, greenBlob5])

            x = 500
            for _ in range(8):
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
                x += 350

        # ── Zone 3 @ 11 500 – first witch encounter (3 witches) ──────────────
        elif backgroundScrollX > 11500 and not self.activeMonsters[2]:
            self.activeMonsters[2] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []

            block1 = Block(500,  340, 100, 60,  "greyRock", self.screen)
            block2 = Block(820,  100, 150, 300, "monster",  self.screen)
            block3 = Block(660,  160, 130, 60,  "greyRock", self.screen)
            block4 = Block(350,  340, 600, 60,  "greyRock", self.screen)
            self.blocks.extend([block1, block2, block3, block4])

            witch1 = Witch(600,  100, self.witch, self.witch2, self.screen)
            witch2 = Witch(900,  200, self.witch, self.witch2, self.screen)
            witch3 = Witch(1100, 150, self.witch, self.witch2, self.screen)
            self.witches.extend([witch1, witch2, witch3])
            self.triggerFire = True

        # ── Zone 4 @ 16 000 – mummy rush on tiered platforms ─────────────────
        elif backgroundScrollX > 16000 and not self.activeMonsters[4]:
            self.activeMonsters[4] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []

            block1 = Block(500, 280, 2000, 60, "greyRock", self.screen)
            block2 = Block(700, 340, 1000, 60, "greyRock", self.screen)
            self.blocks.extend([block1, block2])

            x = 450
            for _ in range(8):
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
                x += 200

        # ── Zone 5 @ 20 500 – striped platforms, mummies + 2 witches ─────────
        elif backgroundScrollX > 20500 and not self.activeMonsters[5]:
            self.activeMonsters[5] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []

            block1 = Block(450, 220, 3000, 60, "striped",     self.screen)
            block2 = Block(600, 280, 2000, 60, "stripedFlip", self.screen)
            block3 = Block(800, 340, 1000, 60, "striped",     self.screen)
            self.blocks.extend([block1, block2, block3])

            x = 450
            for _ in range(6):
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
                x += 250

            witch1 = Witch(900,  100, self.witch, self.witch2, self.screen)
            witch2 = Witch(1150, 100, self.witch, self.witch2, self.screen)
            self.witches.extend([witch1, witch2])

        # ── Zone 6 @ 25 000 – checkered gauntlet, blobs + mummies ───────────
        elif backgroundScrollX > 25000 and not self.activeMonsters[6]:
            self.activeMonsters[6] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []

            block1 = Block(500, 220, 3500, 60, "checkered", self.screen)
            block2 = Block(420, 280, 3500, 60, "checkered", self.screen)
            block3 = Block(350, 340, 3000, 60, "checkered", self.screen)
            block4 = Block(500, 100, 1000, 60, "greyRock",  self.screen)
            self.blocks.extend([block1, block2, block3, block4])

            greenBlob  = GreenBlob(430, 300, 100, 100, self.screen)
            greenBlob2 = GreenBlob(620, 300, 100, 100, self.screen)
            greenBlob3 = GreenBlob(800, 300, 100, 100, self.screen)
            greenBlob4 = GreenBlob(1000,300, 100, 100, self.screen)
            self.greenBlobs.extend([greenBlob, greenBlob2, greenBlob3, greenBlob4])

            x = 900
            for _ in range(3):
                self.mummys.append(
                    Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen))
                x += 450

        # ── Zone 7 @ 29 500 – 3 witches, small platforms (no ceiling) ────────
        elif backgroundScrollX > 29500 and not self.activeMonsters[7]:
            self.activeMonsters[7] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []

            block1 = Block(420, 340, 100, 60, "checkered", self.screen)
            block2 = Block(700, 340, 100, 60, "checkered", self.screen)
            block3 = Block(980, 280, 100, 60, "checkered", self.screen)
            self.blocks.extend([block1, block2, block3])

            witch1 = Witch(1000, 200, self.witch, self.witch2, self.screen)
            witch2 = Witch(700,  250, self.witch, self.witch2, self.screen)
            witch3 = Witch(1200, 150, self.witch, self.witch2, self.screen)
            self.witches.extend([witch1, witch2, witch3])

        # ── Zone 8 @ 34 000 – spike gauntlet ─────────────────────────────────
        elif backgroundScrollX > 34000 and not self.activeMonsters[8]:
            self.activeMonsters[8] = True
            self.mummys = []; self.witches = []; self.blocks = []
            self.greenBlobs = []; self.fires = []

            block1 = Block(450, 220, 100, 60, "checkered", self.screen)
            block2 = Block(700, 220, 100, 60, "checkered", self.screen)
            block3 = Block(950, 280, 100, 60, "checkered", self.screen)
            block4 = Block(350, 340, 100, 60, "checkered", self.screen)
            block5 = Block(1200,280, 100, 60, "checkered", self.screen)
            self.blocks.extend([block1, block2, block3, block4, block5])

            self.spikes.append(SpikeBlock(500,  340, self.screen))
            self.spikes.append(SpikeBlock(750,  340, self.screen))
            self.spikes.append(SpikeBlock(1000, 340, self.screen))
            self.spikes.append(SpikeBlock(1300, 340, self.screen))


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
        # Load 3 background colour themes × 2 sway variants (A and B)
        # bg_pairs[i] = (frame_A, frame_B) for theme i
        self.bg_pairs = []
        for i in range(1, 4):
            a = pygame.image.load(f'Game/Images/background{i}.png')
            a = pygame.transform.scale(a, (900, 700))
            b = pygame.image.load(f'Game/Images/background{i}_b.png')
            b = pygame.transform.scale(b, (900, 700))
            self.bg_pairs.append((a, b))
        self.bgimage = self.bg_pairs[0][0]   # start with theme 0, frame A
        self._sway_timer  = 0                # controls A↔B switching
        self._sway_frame  = 0               # 0 = A, 1 = B
        self._sway_period = 10              # frames per half-sway (~6 Hz flicker)

        self.bgBlack  = pygame.image.load('Game/Images/black.png')
        self.bgBlack  = pygame.transform.scale(self.bgBlack, (900, 700))
        self.floor = pygame.image.load('Game/Images/wood.png')
        self.floor = pygame.transform.scale(self.floor, (900, 200))
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

    def getBackgroundX(self):
        return self.totalX

    def setXPosition(self, totalX):
        self.totalX = totalX

    def render(self, total_distance=0):
        # Choose theme and sway frame.
        if self.isBlackBackground:
            self.bgimage = self.bgBlack
            self._black_latched = True
            self.isBlackBackground = False
        elif not getattr(self, '_black_latched', False):
            bg_idx = min(2, max(0, int(total_distance)) // 4500)
            self._sway_timer += 1
            if self._sway_timer >= self._sway_period:
                self._sway_timer = 0
                self._sway_frame = 1 - self._sway_frame   # toggle A↔B
            self.bgimage = self.bg_pairs[bg_idx][self._sway_frame]

        self.surface.fill((0, 0, 0))
        self.surface.blit(self.bgimage, (self.bgX1, self.bgY1))
        self.surface.blit(self.bgimage, (self.bgX2 + 5, self.bgY2))
        self.surface.blit(self.floor, (self.bgX1, self.bgY1 + 400))
        self.surface.blit(self.floor, (self.bgX2 + 5, self.bgY2 + 400))
        self.surface.blit(self.water, (self.bgX1, self.bgY1 + 600))
        self.surface.blit(self.water, (self.bgX2, self.bgY2 + 600))
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
                self.bgX1 = self.rectBGimg.width + 15
            if self.bgX2 <= -self.rectBGimg.width:
                self.bgX2 = self.rectBGimg.width + 15
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
        self.direction = -1 * random.randint(1, 2)
        self.x = x
        self.y = y
        self.destructionAnimation = 0
        self.stunned = 0
        self.screen = screen
        self.rand = 1
        randomMax = random.randint(300, 500)
        self.changeDirection = random.randint(200, randomMax)
        self.storeDirection = 1
        self.health = random.randint(6, 13)
        self.fire = pygame.image.load("Game/Images/fire.png")
        self.fire = pygame.transform.scale(self.fire, (60, 60))
        self.hurtMummy = pygame.image.load("Game/Images/Mummy/hurtMummy.png")
        self.hurtMummy = pygame.transform.scale(self.hurtMummy, (width, height))
        self.hurtLeftMummy = pygame.transform.flip(self.hurtMummy, True, False)
        self.hurtLeftMummy = pygame.transform.scale(self.hurtLeftMummy, (width, height))
        self.damageAttack = 8
        self.hp = 100
        self.height = height
        self.width = width
        self.hurtTimer = 0
        self.isMonsterHurtAnimation = 0
        self.damageReceived = 0
        self.exp = 10
        self.isHurtAnimationStarted = False
        self.isHurtTimer = 0
        self.startDestructionAnimation = False
        self.blocks = []   # set each frame by the game loop for wall collision

        if self.height > 100:
            self.damageAttack = 10
            self.exp = 20
            self.health = 20
            self.mummy1 = pygame.image.load("Game/Images/Mummy/mummy1Big.png")
            self.mummy1 = pygame.transform.scale(self.mummy1, (width, height))
            self.mummy2 = pygame.image.load("Game/Images/Mummy/mummy2Big.png")
            self.mummy2 = pygame.transform.scale(self.mummy2, (width, height))
            self.hurtMummy = pygame.transform.scale(self.hurtMummy, (width, height))
            self.hurtLeftMummy = pygame.transform.scale(self.hurtLeftMummy, (width, height))

        # Outline surfaces built AFTER final hurt sprites are set
        self.hurtOutline     = make_outline_surf(self.hurtMummy)
        self.hurtLeftOutline = make_outline_surf(self.hurtLeftMummy)

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
        _render_damage_text(self.screen, _FONT_DAMAGE, damage,
                            self.getXPosition() + 60, self.getYPosition() - 60)

    def drawDestruction(self, damage):
        self.destructionAnimation += 1
        self.displayDamageOnMonster(damage)
        if self.destructionAnimation < 30 and self.destructionAnimation % 2 == 0:
            self.screen.blit(self.fire,
                             (self.x + random.randint(-100, 0),
                              self.y + random.randint(-100, 0)))

    def _hits_block(self, new_x):
        """Return True if moving to new_x would overlap a block horizontally."""
        _dy = 12
        m_top    = self.y + _dy
        m_bottom = self.y + _dy + self.height
        m_left   = new_x
        m_right  = new_x + self.width
        for b in self.blocks:
            bx = b.getBlockXPosition()
            by = b.getBlockYPosition()
            bx2 = bx + b.getWidth()
            by2 = by + b.getHeight()
            # Vertical overlap?
            if m_bottom <= by or m_top >= by2:
                continue
            # Horizontal overlap?
            if m_right > bx and m_left < bx2:
                return True
        return False

    def drawMonster(self):
        _dy = 12  # push sprite down so feet touch the floor
        if self.x % 90 < 40 and self.stunned == 0:
            self.screen.blit(self.mummy1, (self.x, self.y + _dy))
        elif self.stunned == 0:
            self.screen.blit(self.mummy2, (self.x, self.y + _dy))

        if self.stunned == 0:
            new_x = self.x + self.direction * self.rand
            if self._hits_block(new_x):
                # Reverse direction on block contact
                self.direction *= -1
                self.mummy1 = pygame.transform.flip(self.mummy1, True, False)
                self.mummy2 = pygame.transform.flip(self.mummy2, True, False)
            else:
                self.x = new_x
        elif self.stunned > 0 and self.direction > 0:
            self.stunned += 1
            self.displayDamageOnMonster(self.damageReceived)
            self.screen.blit(self.hurtMummy, (self.x, self.y + _dy))
            if self.stunned <= 8:
                self.screen.blit(self.hurtOutline, (self.x, self.y + _dy))
            if self.stunned == 20:
                self.stunned = 0
        elif self.stunned > 0 and self.direction < 0:
            self.stunned += 1
            self.screen.blit(self.hurtLeftMummy, (self.x, self.y + _dy))
            self.displayDamageOnMonster(self.damageReceived)
            if self.stunned <= 8:
                self.screen.blit(self.hurtLeftOutline, (self.x, self.y + _dy))
            if self.stunned == 20:
                self.stunned = 0

        if self.x % self.changeDirection == 0 and self.stunned == 0:
            self.direction *= -1
            self.mummy1 = pygame.transform.flip(self.mummy1, True, False)
            self.mummy2 = pygame.transform.flip(self.mummy2, True, False)


# ---------------------------------------------------------------------------
class Witch():
    def __init__(self, x, y, witch1Image, witch2Image, screen):
        self.witch = pygame.transform.scale(witch1Image, (100, 100))
        self.witch2 = pygame.transform.scale(witch2Image, (100, 100))
        self.hurtWitch = pygame.image.load("Game/Images/Bear/hurtWitch.png")
        self.hurtWitch = pygame.transform.scale(self.hurtWitch, (100, 100))
        self.directionX = -1 * random.randint(1, 2)
        self.x = x
        self.y = y
        self.destructionAnimation = 0
        self.stunned = 0
        self.screen = screen
        self.rand = 1
        self.health = random.randint(20, 35)
        self.fire = pygame.image.load("Game/Images/fire2.png")
        self.fire = pygame.transform.scale(self.fire, (60, 60))
        self.changeDirectionX = random.randint(100, 300)
        self.changeDirectionY = 80
        self.storeDirection = 1
        self.directionY = 1
        self.setThrowsFireBall = False
        self.fireBallAnimationCounter = 0
        self.damageAttack = 5
        self.hp = 100
        self.isMonsterHurtAnimation = 0
        self.damageReceived = 0
        self.exp = 12
        self.isHurtAnimationStarted = False
        self.isHurtTimer = 0
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
        _render_damage_text(self.screen, _FONT_DAMAGE, damage,
                            self.getXPosition() + 60, self.getYPosition() - 60)

    def drawDestruction(self, damage):
        self.destructionAnimation += 1
        self.displayDamageOnMonster(damage)
        if self.destructionAnimation < 30 and self.destructionAnimation % 2 < 10:
            self.screen.blit(self.fire,
                             (self.x + random.randint(-100, 0),
                              self.y + random.randint(-100, 0)))

    def drawMonster(self):
        if self.stunned == 0:
            if not self.setThrowsFireBall:
                self.screen.blit(self.witch, (self.x, self.y))
            else:
                self.fireBallAnimationCounter += 1
                self.screen.blit(self.witch2, (self.x, self.y))

        if self.fireBallAnimationCounter > 50:
            self.fireBallAnimationCounter = 0
            self.setThrowsFireBalls(False)

        if self.stunned == 0:
            self.x += self.directionX * self.rand
            self.y += self.directionY * self.rand
        elif self.stunned > 0:
            self.stunned += 1
            self.screen.blit(self.hurtWitch, (self.x, self.y))
            self.displayDamageOnMonster(self.damageReceived)
            if self.stunned == 20:
                self.stunned = 0

        if self.x % self.changeDirectionX == 0 and self.stunned == 0:
            self.directionX *= -1
            if not self.setThrowsFireBall:
                self.witch = pygame.transform.flip(self.witch, True, False)
            else:
                self.fireBallAnimationCounter += 1
                self.witch2 = pygame.transform.flip(self.witch2, True, False)

        if self.y % self.changeDirectionY == 0 and self.stunned == 0:
            self.directionY *= -1
            if not self.setThrowsFireBall:
                self.witch = pygame.transform.flip(self.witch, True, False)
            else:
                self.witch2 = pygame.transform.flip(self.witch2, True, False)


# ---------------------------------------------------------------------------
class FireBall():
    def __init__(self, x, y, vel_x, vel_y, fireballImage, screen):
        self.x = x
        self.y = y
        self.vel_x = vel_x
        self.vel_y = -1 * vel_y
        self.screen = screen
        # Pre-scale once; reused every frame
        self.fire = pygame.transform.scale(fireballImage, (60, 60))
        self.stunned = False
        self.health = 1
        self.damageAttack = 5
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
        self.screen.blit(self.fire, (self.x, self.y))


# ---------------------------------------------------------------------------
class GreenBlob():
    def __init__(self, x, y, height, width, screen):
        self.height = height
        self.width = width
        self.greenBlob = pygame.image.load("Game/Images/greenBlob.png")
        self.greenBlob = pygame.transform.scale(self.greenBlob, (self.width, self.height))
        self.comingUp = False
        self.direction = -1 * random.randint(1, 2)
        self.x = x
        self.y = y
        self.health = 22
        self.destructionAnimation = 0
        self.stunned = 0
        self.screen = screen
        self.rand = random.randint(1, 2)
        randomMax = random.randint(30, 80)
        self.changeDirection = random.randint(30, randomMax)
        self.jump = False
        self.comingDown = False
        self.nextJumpTimer = random.randint(20, 90)
        self.timer = 0
        self.hurtGreenBlob = pygame.image.load("Game/Images/greenBlob2.png")
        self.hurtGreenBlob = pygame.transform.scale(self.hurtGreenBlob, (100, 100))
        self.fire = pygame.image.load("Game/Images/fire.png")
        self.fire = pygame.transform.scale(self.fire, (60, 60))
        self.damageAttack = 12
        self.hp = 22
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
            self.health = 50
            self.exp = 40
            self.damageAttack = 25

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
        _render_damage_text(self.screen, _FONT_DAMAGE, damage,
                            self.getXPosition() + 60, self.getYPosition() - 60)

    def drawDestruction(self, damage):
        self.destructionAnimation += 1
        self.displayDamageOnMonster(damage)
        if self.destructionAnimation < 30 and self.destructionAnimation % 2 == 0:
            self.screen.blit(self.fire,
                             (self.x + random.randint(-100, 0),
                              self.y + random.randint(-100, 0)))

    def drawMonster(self):
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

        if self.stunned == 0:
            self.screen.blit(self.greenBlob, (self.x, self.y))
            self.x += self.direction * self.rand
        elif self.stunned > 0:
            self.stunned += 1
            self.displayDamageOnMonster(self.damageReceived)
            self.screen.blit(self.hurtGreenBlob, (self.x, self.y))
            if self.stunned == 20:
                self.stunned = 0

        if self.x % self.changeDirection == 0 and self.stunned == 0:
            self.direction *= -1
            self.greenBlob = pygame.transform.flip(self.greenBlob, True, False)


# ---------------------------------------------------------------------------
class Bear:
    def __init__(self, x, y, screen):
        self.screen = screen
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
        self.hurtTimer = 0
        self.leftDirection = False
        self.comingUp = False

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

    def startJump(self):
        """Kick off a new jump – sets initial upward velocity."""
        self.jumpVelocity = 16.8   # tuned so peak ≈ 217 px – clears y=190 blocks
        self.comingUp = True

    def _jumpPhysics(self, blocks):
        """
        Velocity-based jump physics shared by jump() and leftJump().
        • Parabolic arc via variable gravity (lighter rising, heavier falling).
        • Variable height: releasing Z early caps upward velocity at 3 px/frame.
        • Landing uses a frame-crossing check: did feet move from above to
          at/below a block's top surface this frame? Works at any fall speed.
        """
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
            block.setDropStatus(False)
            self.setJumpStatus(False)
            self.setLeftJumpStatus(False)
            self.initialHeight = self.y
            self.jumpVelocity = 0.0

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

                    if prev_feet <= bty and feet >= bty and bx2 > blx and self.x < brx + 30:
                        _land(block, bty)
                        return

                # Secondary fallback
                for block in blocks:
                    block.isBoundaryPresent(self.x, self.y)
                    if block.getOnPlatform():
                        bty = block.getBlockYPosition()
                        _land(block, bty)
                        return

            else:
                # ---- Case 2: launched from another platform ------------------
                source_bty = self.initialHeight + 100

                for block in blocks:
                    bty = block.getBlockYPosition()
                    if bty == source_bty:
                        continue
                    blx = block.getBlockXPosition()
                    brx = blx + block.getWidth()

                    if prev_feet <= bty and feet >= bty and bx2 > blx and self.x < brx + 30:
                        _land(block, bty)
                        return

                # Secondary fallback (skip source block)
                for block in blocks:
                    bty = block.getBlockYPosition()
                    if bty == source_bty:
                        continue
                    block.isBoundaryPresent(self.x, self.y)
                    if block.getOnPlatform():
                        bty = block.getBlockYPosition()
                        _land(block, bty)
                        return

        # Floor landing – use sprite height (100) so bear sits flush on floor
        if self.y + 100 >= 400:
            self.y = 300
            self.setJumpStatus(False)
            self.setLeftJumpStatus(False)
            self.jumpVelocity = 0.0

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

    def isBearHurt(self, positionRelative, bearXPosition, bearYPosition,
                   objectXPosition, objectYPosition, objectName):
        return isBearHurt(positionRelative, bearXPosition, bearYPosition,
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

    def displayDamageOnBear(self, damage):
        _render_damage_text(self.screen, _FONT_DAMAGE, damage,
                            self.getXPosition() + 60, self.getYPosition() - 60)

    def displayBearHp(self):
        pygame.draw.rect(self.screen, (0, 0, 0), pygame.Rect(10, 10, 300, 40))
        hp_text = "Health : " + str(self.getHp()) + "/" + str(self.getMaxHp())
        text = _FONT_HUD.render(hp_text, False, (255, 255, 255))
        self.screen.blit(text, (20, 20))

    def displayBearExp(self):
        self.levelUpCheck()
        pygame.draw.rect(self.screen, (0, 0, 0), pygame.Rect(400, 10, 400, 40))
        exp_text = _FONT_HUD.render(
            'Exp: ' + str(self.getCurrentExp()) + "/" + str(self.getMaxExp()),
            False, (255, 255, 255))
        self.screen.blit(exp_text, (400, 20))
        lvl_text = _FONT_HUD.render('Power Level: ' + str(self.level), False, (255, 255, 255))
        self.screen.blit(lvl_text, (600, 20))

    def setMaxHp(self, maxHp):
        self.maxHp = maxHp

    def getMaxHp(self):
        return self.maxHp

    def setCurrentExp(self, exp):
        self.exp = exp

    def getCurrentExp(self):
        return self.exp

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
                         or len(cur_line_text) == self.indexArray + 1)):
                self.indexArray = 0
                self.line += 1
                if self.line == 1:
                    self.text2 = self.textArray[self.tupleIndex][self.line]
                elif self.line == 2:
                    self.text3 = self.textArray[self.tupleIndex][self.line]
            elif self.line == 0:
                self.text1 = self.textArray[self.tupleIndex][0]

            self.blinkTimer += 1
            _show_bear = (self.tupleIndex < len(self.showBearArray)
                          and self.showBearArray[self.tupleIndex])
            popup_img = self.talking if _show_bear else self.talkingNoBear
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
            self.setEndText(False)
            self.level += 1
            self.maxExp += 20
            self.exp = 0
            self.maxHp += random.randint(5, 15)
            self.hp = self.maxHp
            self.attack += random.randint(2, 5)
            self.damageAttack += random.randint(2, 5)
            self.textArray = []
            self.textArray.append(['LEVEL UP!', '', 'Press "s" to continue'])
            self.textArray.append([
                'Max HP is now: ' + str(self.maxHp),
                'Attack is now: ' + str(self.damageAttack),
                'Press "s" to continue'
            ])
            self.line = 0
            self.tupleIndex = 0
            self.indexArray = 0


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
        floorHeight = 400
        if self.getYPosition() + 120 <= floorHeight:
            self.setYPosition(self.getYPosition() + JUMP_STEP)


# ---------------------------------------------------------------------------
class SpikeBlock():
    def __init__(self, x, y, screen):
        self.x = x
        self.y = y
        self.screen = screen
        self.stunned = False
        self.health = 1
        self.damageAttack = random.randint(10, 20)
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
class FrankenBear():
    def __init__(self, x, y, screen):
        self.destructionAnimation = 0
        self.x = x
        self.y = y
        self.screen = screen
        self.stunned = False
        self.health = 6
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
        self.randomAttack = random.randint(25, 45)
        self.bossDisplay = self.boss3
        self.blinked = False
        self.attacked = False
        self.throwFireBallLeft = False
        self.throwFireBallRight = False
        self.damageAttack = 15
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
        _render_damage_text(self.screen, _FONT_BOSS_DAMAGE, damage, 450, 130)

    def drawMonster(self):
        self.blinkTimer += 1
        self.attackTimer += 1

        if (self.blinkTimer < self.randomBlink
                and self.attackTimer < self.randomAttack):
            self.screen.blit(self.boss1, (300, 40))
        elif (self.blinkTimer >= self.randomBlink
              and self.blinkTimer <= self.randomBlink + 10
              and not self.attacked):
            self.screen.blit(self.boss2, (300, 40))
            self.bossDisplay = self.boss2
            self.blinked = True
        elif (self.attackTimer >= self.randomAttack
              and self.attackTimer <= self.randomAttack + 30):
            self.screen.blit(self.bossDisplay, (300, 40))
            self.attacked = True
        else:
            if self.blinked:
                self.randomBlink = random.randint(50, 150)
                self.blinked = False
                self.blinkTimer = 0
            if self.attacked:
                # Enrage: attack faster when health is low
                if self.health <= 3:
                    self.randomAttack = random.randint(5, 18)
                else:
                    self.randomAttack = random.randint(12, 30)
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
            self.screen.blit(self.boss1, (300, 40))

        if self.stunned > 0:
            self.stunned += 1
            self.displayDamageOnMonster(self.damageReceived)
            if self.stunned == 20:
                self.stunned = 0

    def setStartDestructionAnimation(self, v):
        self.startDestructionAnimation = v

    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation

    def drawDestruction(self, damage):
        self.displayDamageOnMonster(damage)
        self.destructionAnimation += 1
        if self.destructionAnimation < 30 and self.destructionAnimation % 2 < 10:
            self.screen.blit(self.fire,
                             (self.x + random.randint(-300, 0),
                              self.y + random.randint(-300, 0)))

    def getDestructionAnimationCount(self):
        return self.destructionAnimation

    def getExp(self):
        return self.exp
