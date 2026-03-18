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


def _init_fonts():
    global _FONT_DAMAGE, _FONT_HUD, _FONT_BOSS_DAMAGE
    _FONT_DAMAGE = pygame.font.SysFont("Italic", 40)
    _FONT_HUD = pygame.font.SysFont("Italic", 40)
    _FONT_BOSS_DAMAGE = pygame.font.SysFont("Italic", 60)


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
    if monsterType != "frankenbears":
        m_w, m_h = 100, 100
    else:
        m_w, m_h = 300, 300

    monster_rect = pygame.Rect(mummyXPosition, mummyYPosition, m_w, m_h)

    # Attack reach mirrors the attack-sprite widths (190 right / 180 left)
    if not facingLeft:
        attack_rect = pygame.Rect(bearXPosition, bearYPosition + 10, 190, 80)
    else:
        attack_rect = pygame.Rect(bearXPosition - 180, bearYPosition + 10,
                                  180, 80)
    return attack_rect.colliderect(monster_rect)


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
        _init_fonts()

        self.screen = pygame.display.set_mode((900, 700), pygame.DOUBLEBUF)
        self.clock = pygame.time.Clock()

        self.standingBear = pygame.image.load("Game/Images/Bear/standBear2.png")
        self.standingBear = pygame.transform.scale(self.standingBear, (80, 100))
        self.standingBearLeft = pygame.transform.flip(self.standingBear, True, False)

        self.bearWalking1 = pygame.image.load("Game/Images/Bear/bearWalking1.png")
        self.bearWalking1 = pygame.transform.scale(self.bearWalking1, (100, 100))
        self.bearWalking2 = pygame.image.load("Game/Images/Bear/bearWalking2.png")
        self.bearWalking2 = pygame.transform.scale(self.bearWalking2, (100, 100))

        self.screen.fill((255, 255, 255))
        pygame.display.update()

        self.bearWalkingLeft1 = pygame.transform.flip(self.bearWalking1, True, False)
        self.bearWalkingLeft2 = pygame.transform.flip(self.bearWalking2, True, False)

        self.bearAttacking = pygame.image.load("Game/Images/Bear/bearAttacking.png")
        self.bearAttacking = pygame.transform.scale(self.bearAttacking, (190, 100))
        self.bearAttackingLeft = pygame.transform.flip(
            pygame.image.load("Game/Images/Bear/bearAttacking.png"), True, False)
        self.bearAttackingLeft = pygame.transform.scale(self.bearAttackingLeft, (180, 100))

        self.hurtBear = pygame.image.load("Game/Images/Bear/hurtBear.png")
        self.hurtBear = pygame.transform.scale(self.hurtBear, (130, 100))

        self.mummy1 = pygame.image.load("Game/Images/Mummy/mummy1.png")
        self.mummy2 = pygame.image.load("Game/Images/Mummy/mummy2.png")
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
        bear = Bear(190, 300, self.screen)
        bear.setJumpStatus(False)
        bear.setLeftJumpStatus(False)

        attackingAnimationCounter = 0
        attackingLeftAnimtationCounter = 0
        hurtTimer = 0
        background = Background(self.screen)
        x = 320
        for _ in range(10):
            x += 80
            mummy = Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen)
            self.mummys.append(mummy)

        self.activeMonsters = [False] * 14

        # Initial obstacle platforms – each clearly separated with ~80 px gaps
        block1 = Block(370,  340, 100, 60,  "red",     self.screen)
        block2 = Block(550,  190, 100, 60,  "monster", self.screen)
        block3 = Block(730,  190, 100, 60,  "red",     self.screen)
        block5 = Block(910,  190, 100, 60,  "red",     self.screen)
        block7 = Block(1090, 190, 100, 60,  "monster", self.screen)
        block6 = Block(1270, 190, 100, 60,  "monster", self.screen)
        block8 = Block(1200, 100, 250, 250, "monster", self.screen)

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
        totalDistance = 190
        bear.setLeftDirection(False)
        jumpTimer = 0
        attackCounterReady = 0

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

            background.render()

            if bear.getEndText():

                keys = pygame.key.get_pressed()

                # ---- Z + RIGHT: jump-right --------------------------------
                if keys[pygame.K_z] and keys[pygame.K_RIGHT] and jumpTimer > 20:
                    totalDistance += STEP
                    if not bear.getJumpStatus() and not bear.getLeftJumpStatus():
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
                        background.update(bear.getXPosition(), bear.getYPosition())
                        bear.setComingUpStatus(True)

                    else:
                        if bear.getXPosition() < self.rightBoundary:
                            jumpTimer = 0
                            for block in self.blocks:
                                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                                if block.getIsLeftBoundary():
                                    bear.setXPosition(bear.getXPosition() - STEP)
                                    totalDistance -= STEP
                            bear.setXPosition(bear.getXPosition() + STEP)
                            totalDistance += STEP
                            backgroundScrollX = bear.getXPosition() - STEP
                            background.setXPosition(backgroundScrollX)
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
                                    backgroundScrollX = bear.getXPosition() + STEP
                                    background.setXPosition(backgroundScrollX)

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
                        bear.setLeftJumpStatus(False)
                        bear.setComingUpStatus(True)

                    background.update(bear.getXPosition(), bear.getYPosition())

                # ---- Z + LEFT: jump-left ---------------------------------
                elif keys[pygame.K_z] and keys[pygame.K_LEFT] and jumpTimer > 10:
                    totalDistance -= STEP
                    if not bear.getJumpStatus() and not bear.getLeftJumpStatus():
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
                        bear.setComingUpStatus(True)
                    else:
                        if bear.getXPosition() > self.leftBoundary:
                            jumpTimer = 0
                            bear.setXPosition(bear.getXPosition() - STEP)
                            totalDistance -= STEP
                            backgroundScrollX = bear.getXPosition() + STEP
                            background.setXPosition(backgroundScrollX)
                        else:
                            jumpTimer = 0
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
                            bear.setComingUpStatus(True)

                    background.update(backgroundScrollX, bear.getYPosition())

                # ---- Z only: vertical jump --------------------------------
                elif (keys[pygame.K_z]
                      and not bear.getJumpStatus()
                      and not bear.getLeftJumpStatus()
                      and jumpTimer > 6):
                    jumpTimer = 0
                    bear.setJumpStatus(True)
                    bear.setLeftJumpStatus(True)
                    bear.setComingUpStatus(True)
                    background.update(backgroundScrollX, bear.getYPosition())

                # ---- A + RIGHT: attack right ------------------------------
                elif (keys[pygame.K_a] and keys[pygame.K_RIGHT]
                      and attackingAnimationCounter == 0
                      and attackingLeftAnimtationCounter == 0
                      and attackCounterReady > 20):
                    attackingAnimationCounter += 1
                    bear.setLeftDirection(False)
                    attackCounterReady = 0
                    monsters = self.mummys + self.witches + self.greenBlobs + self.frankenbear
                    for monster in monsters:
                        if isMonsterHurt(bear.getXPosition(), bear.getYPosition(),
                                         monster.getXPosition(), monster.getYPosition(),
                                         bear.getLeftDirection(), monster.getName()):
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
                    monsters = self.mummys + self.witches + self.greenBlobs + self.frankenbear
                    for monster in monsters:
                        if isMonsterHurt(bear.getXPosition(), bear.getYPosition(),
                                         monster.getXPosition(), monster.getYPosition(),
                                         bear.getLeftDirection(), monster.getName()):
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

                    if (not bear.getJumpStatus() and not bear.getLeftJumpStatus()
                            and attackingAnimationCounter == 0):
                        _right_scrolled = False
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

                        # Undo world scroll when the bear was blocked by a wall
                        if _right_scrolled and any(b.getIsLeftBoundary() for b in self.blocks):
                            for obj in (self.mummys + self.fires + self.witches +
                                        self.greenBlobs + self.door + self.keys +
                                        self.spikes):
                                obj.setXPosition(obj.getXPosition() + STEP)
                            for b in self.blocks:
                                b.setblockXPosition(b.getBlockXPosition() + STEP)
                            totalDistance += STEP
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)

                        if bearAnimation % 120 < 40:
                            self.screen.blit(self.bearWalking1,
                                             (bear.getXPosition(), bear.getYPosition()))
                        else:
                            self.screen.blit(self.bearWalking2,
                                             (bear.getXPosition(), bear.getYPosition()))

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

                    bearAnimation -= STEP
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

                        if bearAnimation % 188 < 80:
                            self.screen.blit(self.bearWalkingLeft1,
                                             (bear.getXPosition(), bear.getYPosition()))
                        else:
                            self.screen.blit(self.bearWalkingLeft2,
                                             (bear.getXPosition(), bear.getYPosition()))

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

                    bearAnimation -= STEP
                    background.update(backgroundScrollX, bear.getYPosition())

                # ---- A only: attack (no direction) -----------------------
                elif (keys[pygame.K_a]
                      and attackingAnimationCounter == 0
                      and attackingLeftAnimtationCounter == 0
                      and attackCounterReady > 20):
                    attackingAnimationCounter += 1
                    attackCounterReady = 0
                    monsters = self.mummys + self.witches + self.greenBlobs + self.frankenbear
                    for monster in monsters:
                        if isMonsterHurt(bear.getXPosition(), bear.getYPosition(),
                                         monster.getXPosition(), monster.getYPosition(),
                                         bear.getLeftDirection(), monster.getName()):
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
                        bear.setArrayText(['   Thank you for playing!   ', '     ',
                                           ' Press "s" to continue  '])
                        bear.setArrayText([' The screen will close now  ', '      ',
                                           ' Press "s" to continue  '])
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
                            for _ in range(3):
                                self.bossFires.append(
                                    FireBall(frankenbear.getXPosition() + 200,
                                             frankenbear.getYPosition() + 100,
                                             random.randint(-22, -4),
                                             random.randint(7, 12),
                                             self.fireBossBall, self.screen))
                        elif frankenbear.getThrowFireBallRight() and not self.bossFires:
                            frankenbear.setThrowFireBallLeft(False)
                            for _ in range(3):
                                self.bossFires.append(
                                    FireBall(frankenbear.getXPosition() + 200,
                                             frankenbear.getYPosition() + 100,
                                             random.randint(4, 22),
                                             random.randint(7, 12),
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
                block.isBoundaryPresent(bear.getXPosition(), bear.getYPosition())
                if block.getDropStatus() and not bear.getComingUp():
                    if bear.getYPosition() + 100 < floorHeight:
                        bear.setYPosition(bear.getYPosition() + JUMP_STEP)
                    elif bear.getYPosition() + 100 == floorHeight:
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
                bear.setArrayText(['   The big mummy ahead has   ',
                                   ' a red thing on its forhead       ',
                                   '    Press "s" to continue  '])
                bear.setArrayText([' Attack It there! ', '  Hes carrying a key. ',
                                   '   Press "s" to continue  '])

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
                            bear.setArrayText(['   Attack the Mummys forhead    ', '     ',
                                               ' Press "s" to continue  '])
                            bear.setArrayText([' To grab the key  ',
                                               ' For the locked door.     ',
                                               ' Press "s" to continue  '])
                            self.triggerText3 = True
                            bear.setEndText(False)

                if self.isDoor1Open and not self.triggerText2:
                    bear.setArrayText(['   Grabbed Key!   ', '     ',
                                       ' Press "s" to continue  '])
                    bear.setArrayText(['  You can open the door now.  ', '      ',
                                       '  Press "s" to continue  '])
                    self.triggerText2 = True
                    bear.setEndText(False)
                elif (self.isDoor1Open
                      and door.getXPosition() - 90 <= bear.getXPosition()
                      and not self.triggerText5):
                    bear.setXPosition(bear.getXPosition() - STEP)
                    totalDistance -= STEP
                    self.triggerText5 = True
                    bear.setArrayText(['   You used key!   ', '     ',
                                       ' Press "s" to continue  '])
                    bear.setArrayText(['  The door is unlocked.  ', '      ',
                                       '  Press "s" to continue  '])
                    bear.setEndText(False)

            if not bear.getEndText():
                bear.displayTextBox()

            if bear.getHealth() <= 0 and not self.triggerText4:
                bear.setEndText(False)
                self.triggerText4 = True
                bear.setArrayText(['   GAME OVER!   ', '     ',
                                   ' Press "s" to continue  '])
                bear.setArrayText(['  GAME OVER! : Please try again  ', '     ',
                                   '  Press "s" to continue    '])
                self.escape = True
            elif self.escape and bear.getEndText():
                pygame.quit()
                return

            pygame.display.flip()
            self.clock.tick(60)

    # -----------------------------------------------------------------------
    def deleteAndCreateObjects(self, backgroundScrollX):
        # All spawn X positions are screen-relative and start just ahead of
        # the player (~400-500 px) so objects appear immediately on zone entry.

        if backgroundScrollX > 2200 and not self.activeMonsters[1]:
            self.activeMonsters[1] = True
            self.mummys = []
            self.witches = []
            self.blocks = []
            self.greenBlobs = []
            self.fires = []

            # Platforms for the big-mummy / key / door room
            block5 = Block(450,  340, 100, 60, "red",      self.screen)
            block7 = Block(640,  340, 100, 60, "monster",  self.screen)
            block6 = Block(850,  340, 100, 60, "monster",  self.screen)
            block8 = Block(1100, 340,  50, 60, "red",      self.screen)
            self.blocks.extend([block5, block6, block7, block8])

            # Big mummy carrying the key – spawns close so player sees it
            mummy = Mummy(480, 100, 300, 450, self.mummy1, self.mummy2, self.screen)
            self.mummys.append(mummy)
            self.door1 = Door(self.screen, 1400)
            self.door.append(self.door1)
            # Ceiling block that runs through this zone
            block9 = Block(1500, 0, 2000, 100, "greyRock", self.screen)
            self.blocks.append(block9)

        elif backgroundScrollX > 3200 and not self.activeMonsters[2]:
            self.activeMonsters[2] = True
            self.door = []
            self.mummys = []
            self.witches = []
            self.blocks = []
            self.greenBlobs = []
            self.fires = []

            # Platforms – within visible range
            block1 = Block(500,  340, 100, 60,  "greyRock", self.screen)
            block2 = Block(820,  100, 150, 300, "monster",  self.screen)
            block6 = Block(660,  160, 130, 60,  "greyRock", self.screen)
            block4 = Block(350,  340, 600, 60,  "greyRock", self.screen)
            self.blocks.extend([block1, block2, block6, block4])

            # Six witches spread across the visible area
            witch  = Witch(600,  100, self.witch, self.witch2, self.screen)
            witch2 = Witch(900,  200, self.witch, self.witch2, self.screen)
            witch3 = Witch(700,  250, self.witch, self.witch2, self.screen)
            witch4 = Witch(500,  250, self.witch, self.witch2, self.screen)
            witch5 = Witch(400,  250, self.witch, self.witch2, self.screen)
            witch6 = Witch(1100, 150, self.witch, self.witch2, self.screen)
            self.witches.extend([witch, witch2, witch3, witch4, witch5, witch6])
            self.triggerFire = True

        elif backgroundScrollX > 4800 and not self.activeMonsters[3]:
            self.activeMonsters[3] = True
            self.mummys = []
            self.witches = []
            self.blocks = []
            self.greenBlobs = []
            self.fires = []

            # Ground-level platform starts just ahead
            block1 = Block(400, 340, 900, 60, "greyRock", self.screen)
            self.blocks.append(block1)

            # Green blobs spread across near-visible range
            greenBlob  = GreenBlob(420,  300, 100, 100, self.screen)
            greenBlob2 = GreenBlob(600,  300, 100, 100, self.screen)
            greenBlob3 = GreenBlob(800,  300, 100, 100, self.screen)
            greenBlob4 = GreenBlob(1100, 300, 100, 100, self.screen)
            greenBlob5 = GreenBlob(1400, 300, 100, 100, self.screen)
            self.greenBlobs.extend([greenBlob, greenBlob2, greenBlob3,
                                    greenBlob4, greenBlob5])

            # Upper platform further ahead
            block2 = Block(1300, 220, 2000, 60, "greyRock", self.screen)
            self.blocks.append(block2)

            # 12 mummies spread ahead – start close, space by 300
            x = 450
            for _ in range(12):
                mummy = Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen)
                self.mummys.append(mummy)
                x += 300

        elif backgroundScrollX > 6933 and not self.activeMonsters[4]:
            self.activeMonsters[4] = True

            # Platforms just ahead instead of at 8000+
            block1 = Block(500, 280, 2000, 60, "greyRock", self.screen)
            block2 = Block(700, 340, 1000, 60, "greyRock", self.screen)
            self.blocks.extend([block1, block2])

            # 10 mummies starting close, spaced 150 px
            x = 450
            for _ in range(10):
                mummy = Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen)
                self.mummys.append(mummy)
                x += 150

        elif backgroundScrollX > 8800 and not self.activeMonsters[5]:
            self.activeMonsters[5] = True
            self.mummys = []
            self.witches = []
            self.blocks = []
            self.greenBlobs = []
            self.fires = []

            # Tiered striped platforms – already well-positioned
            block1 = Block(450,  220, 3000, 60, "striped",     self.screen)
            block2 = Block(600,  280, 2000, 60, "stripedFlip", self.screen)
            block3 = Block(800,  340, 1000, 60, "striped",     self.screen)
            self.blocks.extend([block1, block2, block3])

            # 6 mummies starting immediately ahead
            x = 450
            for _ in range(6):
                mummy = Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen)
                self.mummys.append(mummy)
                x += 250

            witch  = Witch(900,  100, self.witch, self.witch2, self.screen)
            witch2 = Witch(1100, 100, self.witch, self.witch2, self.screen)
            self.witches.extend([witch, witch2])

        elif backgroundScrollX > 10400 and not self.activeMonsters[6]:
            self.activeMonsters[6] = True
            self.mummys = []
            self.witches = []
            self.greenBlobs = []
            self.fires = []

            # Layered checkered platforms starting from visible range
            block1 = Block(500,  220, 3500, 60, "checkered", self.screen)
            block2 = Block(420,  280, 3500, 60, "checkered", self.screen)
            block3 = Block(350,  340, 3000, 60, "checkered", self.screen)
            block4 = Block(500,  100, 1000, 60, "greyRock",  self.screen)
            self.blocks.extend([block1, block2, block3, block4])

            # Green blobs right in front of the player
            greenBlob  = GreenBlob(430,  300, 100, 100, self.screen)
            greenBlob2 = GreenBlob(600,  300, 100, 100, self.screen)
            greenBlob3 = GreenBlob(750,  300, 100, 100, self.screen)
            greenBlob4 = GreenBlob(1000, 300, 100, 100, self.screen)
            greenBlob5 = GreenBlob(380,  300, 100, 100, self.screen)
            self.greenBlobs.extend([greenBlob, greenBlob2, greenBlob3,
                                    greenBlob4, greenBlob5])

            # 3 mummies a bit further ahead
            x = 900
            for _ in range(3):
                mummy = Mummy(x, 300, 100, 100, self.mummy1, self.mummy2, self.screen)
                self.mummys.append(mummy)
                x += 450

        elif backgroundScrollX > 12800 and not self.activeMonsters[7]:
            self.activeMonsters[7] = True
            self.mummys = []
            self.witches = []
            self.blocks = []
            self.greenBlobs = []
            self.fires = []

            # Small platforms and a ceiling – pulled in from 4500+
            block1 = Block(420,  340, 100, 60, "checkered",  self.screen)
            block2 = Block(700,  340, 100, 60, "checkered",  self.screen)
            block3 = Block(950,  0,  5000, 80, "checkered",  self.screen)
            self.blocks.extend([block1, block2, block3])

            # Witches just ahead of the player
            witch  = Witch(1000, 200, self.witch, self.witch2, self.screen)
            witch2 = Witch(900,  250, self.witch, self.witch2, self.screen)
            witch3 = Witch(1100, 250, self.witch, self.witch2, self.screen)
            witch4 = Witch(1200, 150, self.witch, self.witch2, self.screen)
            self.witches.extend([witch, witch2, witch3, witch4])

        elif backgroundScrollX > 14400 and not self.activeMonsters[8]:
            self.activeMonsters[8] = True
            self.mummys = []
            self.witches = []
            self.greenBlobs = []
            self.fires = []

            # Spike-and-platform gauntlet – pulled from 4000-6200 down to 350-1200
            block1 = Block(450,  220, 100, 60, "checkered", self.screen)
            block2 = Block(700,  220, 100, 60, "checkered", self.screen)
            block3 = Block(950,  280, 100, 60, "checkered", self.screen)
            block4 = Block(350,  340, 100, 60, "checkered", self.screen)
            block5 = Block(1200, 280, 100, 60, "checkered", self.screen)
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
        self.maxBlinkTime = random.randint(10, 100)
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
        elif self.monsterBlockTimer < self.maxBlinkTime + 10:
            self.screen.blit(self.blockClosedEyes,
                             (self.getBlockXPosition(), self.getBlockYPosition()))
        else:
            self.monsterBlockTimer = 1
            self.maxBlinkTime = random.randint(30, 150)
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
        self.bgimage = pygame.image.load('Game/Images/background1.png')
        self.bgimage = pygame.transform.scale(self.bgimage, (900, 700))
        self.bgBlack  = pygame.image.load('Game/Images/black.png')
        self.bgBlack  = pygame.transform.scale(self.bgBlack, (900, 700))
        self.floor = pygame.image.load('Game/Images/wood.png')
        self.floor = pygame.transform.scale(self.floor, (900, 200))
        self.roof  = pygame.image.load('Game/Images/cobstone.png')
        self.roof  = pygame.transform.scale(self.roof, (900, 20))
        self.water = pygame.image.load('Game/Images/water.png')
        self.water = pygame.transform.scale(self.water, (900, 100))

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

    def render(self):
        self.surface.fill((0, 0, 0))
        self.surface.blit(self.bgimage, (self.bgX1, self.bgY1))
        self.surface.blit(self.bgimage, (self.bgX2 + 5, self.bgY2))
        self.surface.blit(self.floor, (self.bgX1, self.bgY1 + 400))
        self.surface.blit(self.floor, (self.bgX2 + 5, self.bgY2 + 400))
        self.surface.blit(self.water, (self.bgX1, self.bgY1 + 600))
        self.surface.blit(self.water, (self.bgX2, self.bgY2 + 600))
        self.surface.blit(self.roof, (self.bgX1, self.bgY1))
        self.surface.blit(self.roof, (self.bgX2, self.bgY2))

    def update(self, characterPosition, height):
        if self.getBlackBackground():
            # Pre-loaded – only swap reference, no disk I/O
            self.bgimage = self.bgBlack
            self.setBlackBackground(False)
            return

        if self.getStopBackground():
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
        self.rand = random.randint(1, 2)
        randomMax = random.randint(60, 90)
        self.changeDirection = random.randint(30, randomMax)
        self.storeDirection = 1
        self.health = random.randint(6, 13)
        self.fire = pygame.image.load("Game/Images/fire.png")
        self.fire = pygame.transform.scale(self.fire, (60, 60))
        self.hurtMummy = pygame.image.load("Game/Images/Mummy/hurtMummy.png")
        self.hurtMummy = pygame.transform.scale(self.hurtMummy, (width, height))
        self.hurtLeftMummy = pygame.transform.flip(self.hurtMummy, True, False)
        self.hurtLeftMummy = pygame.transform.scale(self.hurtLeftMummy, (width + 100, height))
        self.damageAttack = 8
        self.hp = 100
        self.height = height
        self.hurtTimer = 0
        self.isMonsterHurtAnimation = 0
        self.damageReceived = 0
        self.exp = 10
        self.isHurtAnimationStarted = False
        self.isHurtTimer = 0
        self.startDestructionAnimation = False

        if self.height > 100:
            self.damageAttack = 10
            self.exp = 20
            self.health = 20
            self.mummy1 = pygame.image.load("Game/Images/Mummy/mummy1Big.png")
            self.mummy1 = pygame.transform.scale(self.mummy1, (width, height))
            self.mummy2 = pygame.image.load("Game/Images/Mummy/mummy2Big.png")
            self.mummy2 = pygame.transform.scale(self.mummy2, (width, height))

    def setStartDestructionAnimation(self, v):
        self.startDestructionAnimation = v

    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation

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

    def drawMonster(self):
        if self.x % 90 < 40 and self.stunned == 0:
            self.screen.blit(self.mummy1, (self.x, self.y))
        elif self.stunned == 0:
            self.screen.blit(self.mummy2, (self.x, self.y))

        if self.stunned == 0:
            self.x += self.direction * self.rand
        elif self.stunned > 0 and self.direction > 0:
            self.stunned += 1
            self.displayDamageOnMonster(self.damageReceived)
            self.screen.blit(self.hurtMummy, (self.x, self.y))
            if self.stunned == 20:
                self.stunned = 0
        elif self.stunned > 0 and self.direction < 0:
            self.stunned += 1
            self.screen.blit(self.hurtLeftMummy, (self.x, self.y))
            self.displayDamageOnMonster(self.damageReceived)
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
        self.level = 1
        self.textHeight = 30
        self.randomBlink = random.randint(15, 30)
        self.talking  = pygame.image.load("Game/Images/Talking.png")
        self.talking  = pygame.transform.scale(self.talking,  (900, 250))
        self.talking2 = pygame.image.load("Game/Images/Talking2.png")
        self.talking2 = pygame.transform.scale(self.talking2, (900, 250))
        self.bearJumping1 = pygame.image.load("Game/Images/Bear/bearJump1.png")
        self.bearJumping1 = pygame.transform.scale(self.bearJumping1, (100, 100))
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
            ['To jump press "z"  ', 'To attack press "a"      ',
             '   Press "s" to continue  '],
            [' Press "ESC" to end game   ',
             ' Defeat frankenbear at end of castle !!    ',
             '  Press "s" to continue   ']
        ]
        self.tupleIndex = 0
        self.bearJumping2 = pygame.image.load("Game/Images/Bear/bearJump2.png")
        self.bearJumping2 = pygame.transform.scale(self.bearJumping2, (100, 100))
        self.bearJumpingLeft1 = pygame.transform.flip(
            pygame.image.load("Game/Images/Bear/bearJump1.png"), True, False)
        self.bearJumpingLeft1 = pygame.transform.scale(self.bearJumpingLeft1, (100, 100))
        self.bearJumpingLeft2 = pygame.transform.flip(
            pygame.image.load("Game/Images/Bear/bearJump2.png"), True, False)
        self.bearJumpingLeft2 = pygame.transform.scale(self.bearJumpingLeft2, (100, 100))
        self.damageAttack = 2
        self.hurtTimer = 0
        self.leftDirection = False
        self.comingUp = False

    def setArrayText(self, text):
        self.textArray.append(text)

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

    def jump(self, blocks):
        for block in blocks:
            block.setOnPlatform(False)
        if not self.getLeftDirection():
            self.screen.blit(self.bearJumping1, (self.getXPosition(), self.y))
        else:
            self.screen.blit(self.bearJumpingLeft1, (self.getXPosition(), self.y))

        if self.y >= (self.initialHeight - 200) and self.comingUp:
            self.y -= JUMP_STEP
        elif self.y >= (self.initialHeight - 230):
            self.comingUp = False
            self.y += JUMP_STEP
            for block in blocks:
                # Range-check landing: bear feet within one step of platform top
                bty = block.getBlockYPosition()
                blx = block.getBlockXPosition()
                brx = blx + block.getWidth()
                by2 = self.y + 100
                bx2 = self.x + 100
                if bty <= by2 <= bty + JUMP_STEP and bx2 > blx and self.x < brx + 30:
                    self.y = bty - 100   # snap exactly onto platform surface
                    block.setOnPlatform(True)
                    block.setDropStatus(False)
                    self.setJumpStatus(False)
                    self.setLeftJumpStatus(False)
                    self.initialHeight = self.y
                    break
                block.isBoundaryPresent(self.getXPosition(), self.y)
                if block.getOnPlatform():
                    self.y = block.getBlockYPosition() - 100
                    self.setJumpStatus(False)
                    self.setLeftJumpStatus(False)
                    self.initialHeight = self.y

        # Floor landing – >= catches steps that overshoot the exact floor pixel
        if self.y + 100 >= 400:
            self.y = 300
            self.setJumpStatus(False)
            self.setLeftJumpStatus(False)

    def leftJump(self, blocks):
        for block in blocks:
            block.setOnPlatform(False)

        if (self.y <= self.initialHeight
                and self.y >= (self.initialHeight - 200)
                and self.getComingUp()):
            self.y -= JUMP_STEP
            self.screen.blit(self.bearJumpingLeft1, (self.getXPosition(), self.y))
        elif self.y >= (self.initialHeight - 230) and self.y < self.initialHeight:
            self.y += JUMP_STEP
            self.setComingUpStatus(False)
            for block in blocks:
                # Range-check landing: bear feet within one step of platform top
                bty = block.getBlockYPosition()
                blx = block.getBlockXPosition()
                brx = blx + block.getWidth()
                by2 = self.y + 100
                bx2 = self.x + 100
                if bty <= by2 <= bty + JUMP_STEP and bx2 > blx and self.x < brx + 30:
                    self.y = bty - 100   # snap exactly onto platform surface
                    block.setOnPlatform(True)
                    block.setDropStatus(False)
                    self.setJumpStatus(False)
                    self.setLeftJumpStatus(False)
                    self.initialHeight = self.y
                    break
                block.isBoundaryPresent(self.getXPosition(), self.y)
                if block.getOnPlatform():
                    self.y = block.getBlockYPosition() - 100
                    self.setJumpStatus(False)
                    self.setLeftJumpStatus(False)
                    self.initialHeight = self.y

        if not self.getLeftDirection():
            self.screen.blit(self.bearJumping2, (self.getXPosition(), self.getYPosition()))
        else:
            self.screen.blit(self.bearJumpingLeft2, (self.getXPosition(), self.getYPosition()))

        # Floor landing – >= catches steps that overshoot the exact floor pixel
        if self.getYPosition() + 100 >= 400:
            self.setYPosition(300)
            self.setJumpStatus(False)
            self.setLeftJumpStatus(False)

    def isBearHurt(self, positionRelative, bearXPosition, bearYPosition,
                   objectXPosition, objectYPosition, objectName):
        return isBearHurt(positionRelative, bearXPosition, bearYPosition,
                          objectXPosition, objectYPosition, objectName)

    def boundaryExtraCheck(self):
        floorHeight = 400
        if self.getXPosition() <= 30:
            self.setXPosition(self.getXPosition() + STEP)
        if self.getYPosition() + 100 == floorHeight:
            self.initialHeight = self.getYPosition()
        if self.getYPosition() + 100 > floorHeight:
            self.setYPosition(floorHeight - 100)
            self.initialHeight = floorHeight
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
            if (self.line != len(self.textArray[self.tupleIndex])
                    and len(self.textArray[self.tupleIndex][self.line]) == self.indexArray + 1):
                self.indexArray = 0
                self.line += 1
                if self.line == 1:
                    self.text2 = self.textArray[self.tupleIndex][self.line]
                elif self.line == 2:
                    self.text3 = self.textArray[self.tupleIndex][self.line]
            elif self.line == 0:
                self.text1 = self.textArray[self.tupleIndex][0]

            self.blinkTimer += 1
            if self.blinkTimer < self.randomBlink:
                self.screen.blit(self.talking, (0, 0))
            elif self.blinkTimer <= self.randomBlink + 10:
                self.screen.blit(self.talking2, (0, 0))
            else:
                self.screen.blit(self.talking2, (0, 0))
                self.randomBlink = random.randint(100, 250)
                self.blinkTimer = 0

            self.textTimer += 1
            text1 = _FONT_HUD.render(self.totalText1, False, (0, 0, 0))
            self.screen.blit(text1, (380, 60))
            text2 = _FONT_HUD.render(self.totalText2, False, (0, 0, 0))
            self.screen.blit(text2, (380, 80 + self.textHeight))
            text3 = _FONT_HUD.render(self.totalText3, False, (0, 0, 0))
            self.screen.blit(text3, (380, 110 + self.textHeight))
            self.xText += 5

            if self.textTimer % 3 < 2:
                if self.line == 0:
                    self.totalText1 += self.text1[self.indexArray]
                elif self.line == 1:
                    self.totalText2 += self.text2[self.indexArray]
                elif self.line == 2:
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
            self.textArray.append(['    LEVEL UP !  ', '   ', '   press "s" to continue  '])
            self.textArray.append([
                ' maxHP is now :' + str(self.maxHp) + ' ',
                ' attack is now : ' + str(self.damageAttack) + ' ',
                '    "press "s" to continue  '
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
        self.health = 3
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
        self.randomAttack = random.randint(50, 80)
        self.bossDisplay = self.boss3
        self.blinked = False
        self.attacked = False
        self.throwFireBallLeft = False
        self.throwFireBallRight = False
        self.damageAttack = 10
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
                self.randomAttack = random.randint(20, 70)
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
