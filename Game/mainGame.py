import pygame
import time
import random


class mainGame:
    def __init__(self):

        pygame.init()
        self.screen = pygame.display.set_mode((900, 700))
        self.font = pygame.font.SysFont('Verdana', 25)
        # This is the default standing bear image
        self.standingBear = pygame.image.load(
            "Game/Images/Bear/standBear2.png")
        self.standingBear = pygame.transform.scale(self.standingBear,
                                                   (80, 100))

        self.standingBearLeft = pygame.transform.flip(self.standingBear, True,
                                                      False)

        self.bearWalking1 = pygame.image.load(
            "Game/Images/Bear/bearWalking1.png")
        self.bearWalking1 = pygame.transform.scale(self.bearWalking1,
                                                   (100, 100))
        self.bearWalking2 = pygame.image.load(
            "Game/Images/Bear/bearWalking2.png")
        self.bearWalking2 = pygame.transform.scale(self.bearWalking2,
                                                   (100, 100))
        white = (255, 255, 255)
        self.screen.fill((white))
        pygame.display.update()
        self.bearWalkingLeft1 = pygame.transform.flip(self.bearWalking1, True,
                                                      False)
        self.bearWalkingLeft2 = pygame.transform.flip(self.bearWalking2, True,
                                                      False)

        self.bearAttacking = pygame.image.load(
            "Game/Images/Bear/bearAttacking.png")
        self.bearAttacking = pygame.transform.scale(self.bearAttacking,
                                                    (190, 100))

        self.bearAttackingLeft = pygame.image.load(
            "Game/Images/Bear/bearAttacking.png")
        self.bearAttackingLeft = pygame.transform.flip(self.bearAttacking,
                                                       True, False)
        self.bearAttackingLeft = pygame.transform.scale(
            self.bearAttackingLeft, (180, 100))

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
        white = (255, 255, 255)
        self.screen.fill((white))
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
        x = 330
        for mummy in range(10):
            x = x + 220
            mummy = Mummy(x, 300, 100, 100, self.mummy1, self.mummy2,
                          self.screen)
            self.mummys.append(mummy)

        self.activeMonsters = [
            False, False, False, False, False, False, False, False, False,
            False, False, False, False, False
        ]

        block1 = Block(550, 340, 130, 60, "red", self.screen)
        block2 = Block(1090, 190, 130, 60, "monster", self.screen)
        block3 = Block(1390, 190, 130, 60, "red", self.screen)
        # block4 = Block(1740, 190, 100, 60, "monster", self.screen)
        block5 = Block(2090, 190, 130, 60, "red", self.screen)
        block7 = Block(2440, 190, 130, 60, "monster", self.screen)
        block6 = Block(2800, 190, 130, 60, "monster", self.screen)
        block8 = Block(3100, 100, 300, 300, "monster", self.screen)

        self.door = []
        self.keys = []

        self.blocks.append(block1)
        self.blocks.append(block2)
        self.blocks.append(block3)
        self.blocks.append(block5)
        self.blocks.append(block6)
        self.blocks.append(block7)
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
        # set to 0 every time bear attacks
        attackCounterReady = 0
        # totalDistance = 64000

        for mummy in self.mummys:
            mummy.setStunned(0)
        for witch in self.witches:
            witch.setStunned(0)
        self.door = []
        self.spikes = []

        triggerWitchFireBallAnimation = 0

        #///////////////////////////////////////////////////////////////////////////////////////
        while continueLoop:

            background.render()

            if bear.getEndText() == True:

                #a3
                keys = pygame.key.get_pressed()
                if keys[pygame.K_z] and keys[
                        pygame.K_RIGHT] and jumpTimer > 20:
                    totalDistance = totalDistance + 30
                    if bear.getJumpStatus(
                    ) == False and bear.getLeftJumpStatus() == False:

                        if bear.getXPosition() < self.rightBoundary:
                            for block in self.blocks:
                                block.isBoundaryPresent(
                                    bear.getXPosition(), bear.getYPosition())
                                if block.getIsLeftBoundary() == True:
                                    bear.setXPosition(bear.getXPosition() - 30)
                                    totalDistance = totalDistance - 30

                            backgroundScrollX = bear.getXPosition() - 30
                            background.setXPosition(backgroundScrollX)
                            bear.setXPosition(bear.getXPosition() + 30)

                        else:
                            moveObjects = []
                            moveObjects = self.mummys + self.fires + self.witches + self.greenBlobs + self.door + self.keys + self.spikes
                            for objects in moveObjects:
                                objects.setXPosition(objects.getXPosition() -
                                                     30)

                            for block in self.blocks:
                                block.isBoundaryPresent(
                                    bear.getXPosition(), bear.getYPosition())
                                if block.getIsLeftBoundary() == False:
                                    block.setblockXPosition(
                                        block.getBlockXPosition() - 30)
                                    backgroundScrollX = bear.getXPosition(
                                    ) + 30
                                    background.setXPosition(backgroundScrollX)

                        backgroundScrollX = backgroundScrollX - 30
                        background.setXPosition(backgroundScrollX)
                        bear.setJumpStatus(True)
                        background.update(bear.getXPosition(),
                                          bear.getYPosition())
                        bear.setComingUpStatus(True)
                    #  bear.setLeftJumpStatus(True)
    # Jump =True ////////////////////////////////////////////////////////////
                    else:
                        if bear.getXPosition() < self.rightBoundary:
                            jumpTimer = 0
                            for block in self.blocks:
                                block.isBoundaryPresent(
                                    bear.getXPosition(), bear.getYPosition())
                                if block.getIsLeftBoundary() == True:
                                    bear.setXPosition(bear.getXPosition() - 30)
                                    totalDistance = totalDistance - 30
                                    #

                            bear.setXPosition(bear.getXPosition() + 30)
                            totalDistance = totalDistance + 30

                            backgroundScrollX = bear.getXPosition() - 30
                            background.setXPosition(backgroundScrollX)

                        else:
                            jumpTimer = 0
                            moveObjects = []
                            moveObjects = self.mummys + self.fires + self.witches + self.greenBlobs + self.door + self.keys + self.spikes
                            for objects in moveObjects:
                                objects.setXPosition(objects.getXPosition() -
                                                     30)
                            for block in self.blocks:
                                block.isBoundaryPresent(
                                    bear.getXPosition(), bear.getYPosition())
                                if block.getIsLeftBoundary() == False:
                                    block.setblockXPosition(
                                        block.getBlockXPosition() - 30)
                                    backgroundScrollX = bear.getXPosition(
                                    ) + 30
                                    background.setXPosition(backgroundScrollX)
                    for block in self.blocks:
                        if block.getIsLeftBoundary() == True:
                            bear.setXPosition(bear.getXPosition() - 30)
                            totalDistance = totalDistance + 30
                            #

                    dangerousObjects = self.mummys + self.fires + self.witches + self.greenBlobs + self.spikes + self.bossFires + self.frankenbear

                    for monster in dangerousObjects:
                        if bear.isBearHurt(
                                "RIGHT", bear.getXPosition(),
                                bear.getYPosition(), monster.getXPosition(),
                                monster.getYPosition(),
                                monster.getName()) == True and hurtTimer > 25:
                            hurtTimer = 0

                            bear.displayDamageOnBear(monster.getDamageAttack())
                            bear.setHp(bear.getHp() -
                                       monster.getDamageAttack())
                            self.screen.blit(
                                self.hurtBear,
                                (bear.getXPosition(), bear.getYPosition()))

                            if bear.getXPosition() <= 400:
                                bear.setXPosition(bear.getXPosition() + 30)
                                totalDistance = totalDistance + 30
                                self.screen.blit(
                                    self.hurtBear,
                                    (bear.getXPosition(), bear.getYPosition()))
                                bear.displayDamageOnBear(
                                    monster.getDamageAttack())
                            monster.setHurtTimer(monster.getHurtTimer() + 1)
                        elif monster.getHurtTimer(
                        ) < 15 and monster.getHurtTimer() > 0:
                            monster.setHurtTimer(monster.getHurtTimer() + 1)

                            bear.displayDamageOnBear(monster.getDamageAttack())

                            self.screen.blit(
                                self.hurtBear,
                                (bear.getXPosition(), bear.getYPosition()))
                        else:
                            monster.setHurtTimer(0)
                        bear.setLeftDirection(False)
                        bear.setLeftJumpStatus(False)

                        bear.setComingUpStatus(True)

                    background.update(bear.getXPosition(), bear.getYPosition())
                    # background.render()

                elif keys[pygame.K_z] and keys[
                        pygame.K_LEFT] and jumpTimer > 10:

                    totalDistance = totalDistance - 30
                    if bear.getJumpStatus(
                    ) == False and bear.getLeftJumpStatus() == False:
                        jumpTimer = 0

                        if bear.getXPosition() > self.leftBoundary:
                            for block in self.blocks:
                                block.isBoundaryPresent(
                                    bear.getXPosition(), bear.getYPosition())
                                if block.getIsRightBoundary() == True:
                                    backgroundScrollX = bear.getXPosition(
                                    ) + 30
                                    background.setXPosition(backgroundScrollX)
                                    totalDistance = totalDistance + 30

                            backgroundScrollX = bear.getXPosition() - 30
                            background.setXPosition(backgroundScrollX)
                            bear.setXPosition(bear.getXPosition() + 30)
                            totalDistance = totalDistance - 30

                            # background.render()

                        else:
                            moveObjects = []
                            moveObjects = self.mummys + self.fires + self.witches + self.greenBlobs + self.spikes
                            for objects in moveObjects:
                                objects.setXPosition(objects.getXPosition() +
                                                     30)

                            for block in self.blocks:
                                block.isBoundaryPresent(
                                    bear.getXPosition(), bear.getYPosition())
                                if block.getIsRightBoundary() == False:

                                    block.setblockXPosition(
                                        block.getBlockXPosition() - 30)
                                    backgroundScrollX = bear.getXPosition(
                                    ) - 30
                                    background.setXPosition(backgroundScrollX)
                            backgroundScrollX = bear.getXPosition() + 30
                            background.setXPosition(backgroundScrollX)
                        background.update(backgroundScrollX,
                                          bear.getYPosition())
                        # background.render()
                        bear.setJumpStatus(True)
                        bear.setComingUpStatus(True)
                    else:
                        if bear.getXPosition() > self.leftBoundary:
                            jumpTimer = 0
                            bear.setXPosition(bear.getXPosition() - 30)
                            totalDistance = totalDistance - 30
                            #

                            backgroundScrollX = bear.getXPosition() + 30
                            background.setXPosition(backgroundScrollX)
                            # background.render()
                        else:
                            jumpTimer = 0
                            moveObjects = []
                            moveObjects = self.mummys + self.fires + self.witches + self.greenBlobs + self.door + self.keys + self.spikes
                            for objects in moveObjects:
                                objects.setXPosition(objects.getXPosition() +
                                                     30)

                            for block in self.blocks:
                                block.isBoundaryPresent(
                                    bear.getXPosition(), bear.getYPosition())
                                if block.getIsRightBoundary() == False:
                                    block.setblockXPosition(
                                        block.getBlockXPosition() + 30)
                                    backgroundScrollX = bear.getXPosition(
                                    ) - 30
                                    background.setXPosition(backgroundScrollX)
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)
                        for block in self.blocks:
                            if block.getIsRightBoundary() == True:
                                bear.setXPosition(bear.getXPosition() + 30)
                                totalDistance = totalDistance + 30
                        dangerousObjects = self.mummys + self.fires + self.witches + self.greenBlobs + self.spikes + self.bossFires + self.frankenbear

                        for monster in dangerousObjects:
                            if bear.isBearHurt("RIGHT", bear.getXPosition(),
                                               bear.getYPosition(),
                                               monster.getXPosition(),
                                               monster.getYPosition(),
                                               monster.getName()
                                               ) == True and hurtTimer > 25:
                                hurtTimer = 0

                                bear.displayDamageOnBear(
                                    monster.getDamageAttack())
                                bear.setHp(bear.getHp() -
                                           monster.getDamageAttack())
                                self.screen.blit(
                                    self.hurtBear,
                                    (bear.getXPosition(), bear.getYPosition()))
                                if bear.getXPosition() > self.leftBoundary:
                                    bear.setXPosition(bear.getXPosition() + 30)
                                    totalDistance = totalDistance + 30

                                    self.screen.blit(self.hurtBear,
                                                     (bear.getXPosition(),
                                                      bear.getYPosition()))
                                monster.setHurtTimer(monster.getHurtTimer() +
                                                     1)
                            elif monster.getHurtTimer(
                            ) < 15 and monster.getHurtTimer() > 0:
                                monster.setHurtTimer(monster.getHurtTimer() +
                                                     1)

                                bear.displayDamageOnBear(
                                    monster.getDamageAttack())

                                self.screen.blit(
                                    self.hurtBear,
                                    (bear.getXPosition(), bear.getYPosition()))
                            else:
                                monster.setHurtTimer(0)
                            bear.setLeftDirection(True)
                            bear.setLeftJumpStatus(True)
                            bear.setComingUpStatus(True)

                    background.update(backgroundScrollX, bear.getYPosition())
                    # background.render()

                elif keys[pygame.K_z] and (bear.getJumpStatus() != True
                                           and bear.getLeftJumpStatus() != True
                                           ) and jumpTimer > 6:

                    jumpTimer = 0
                    bear.setJumpStatus(True)
                    bear.setLeftJumpStatus(True)
                    bear.setComingUpStatus(True)

                    background.update(backgroundScrollX, bear.getYPosition())

                elif keys[pygame.K_a] and keys[
                        pygame.
                        K_RIGHT] and attackingAnimationCounter == 0 and attackingLeftAnimtationCounter == 0 and attackCounterReady > 20:

                    attackingAnimationCounter = attackingAnimationCounter + 1
                    bear.setLeftDirection(False)
                    attackCounterReady = 0
                    # background.update(backgroundScrollX, bear.getYPosition())
                    monsters = self.mummys + self.witches + self.greenBlobs + self.frankenbear

                    for monster in monsters:

                        if isMonsterHurt(bear.getXPosition(),
                                         bear.getYPosition(),
                                         monster.getXPosition(),
                                         monster.getYPosition(),
                                         bear.getLeftDirection(),
                                         monster.getName()) == True:

                            if len(self.frankenbear) == 0:
                                monster.setXPosition(monster.getXPosition() +
                                                     30)

                            monster.setDamageReceived(bear.getDamageAttack())
                            monster.setStunned(1)
                            monster.setHealth(monster.getHealth() -
                                              bear.getDamageAttack())
                            hurtTimer = 0

                    for block in self.blocks:
                        if block.getIsLeftBoundary() == True:
                            bear.setXPosition(bear.getXPosition() - 30)
                            totalDistance = totalDistance - 30

                elif keys[pygame.K_a] and keys[
                        pygame.
                        K_LEFT] and attackingAnimationCounter == 0 and attackingLeftAnimtationCounter == 0 and attackCounterReady > 20:

                    attackingAnimationCounter = attackingAnimationCounter + 1

                    attackCounterReady = 0
                    bear.setLeftDirection(True)
                    # background.update(backgroundScrollX, bear.getYPosition())
                    monsters = self.mummys + self.witches + self.greenBlobs + self.frankenbear
                    for monster in monsters:

                        if isMonsterHurt(bear.getXPosition(),
                                         bear.getYPosition(),
                                         monster.getXPosition(),
                                         monster.getYPosition(),
                                         bear.getLeftDirection(),
                                         monster.getName()) == True:
                            if len(self.frankenbear) == 0:
                                monster.setXPosition(monster.getXPosition() +
                                                     30)

                            monster.setDamageReceived(bear.getDamageAttack())
                            monster.setStunned(1)
                            monster.setHealth(monster.getHealth() -
                                              bear.getDamageAttack())
                            hurtTimer = 0
                    for block in self.blocks:
                        if block.getIsLeftBoundary() == True:
                            bear.setXPosition(bear.getXPosition() - 30)
                            totalDistance = totalDistance + 30
                elif keys[
                        pygame.
                        K_RIGHT] and attackingAnimationCounter == 0 and attackingLeftAnimtationCounter == 0:
                    # if keys[pygame.K_RIGHT]:
                    if attackingAnimationCounter == 0:
                        totalDistance = totalDistance + 30

                    self.deleteAndCreateObjects(totalDistance)
                    bear.setLeftDirection(False)

                    if (bear.getJumpStatus() != True
                            and bear.getLeftJumpStatus() != True
                            and attackingAnimationCounter == 0):
                        if bear.getXPosition() < self.rightBoundary:

                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)
                            bear.setXPosition(bear.getXPosition() + 30)

                        else:

                            moveObjects = []
                            moveObjects = self.mummys + self.fires + self.witches + self.greenBlobs + self.door + self.keys + self.spikes
                            for objects in moveObjects:
                                objects.setXPosition(objects.getXPosition() -
                                                     30)

                            for block in self.blocks:
                                if block.getIsLeftBoundary() == False:
                                    block.isBoundaryPresent(
                                        bear.getXPosition(),
                                        bear.getYPosition())
                                    block.setblockXPosition(
                                        block.getBlockXPosition() - 30)
                                elif block.getIsLeftBoundary() == True:
                                    block.isBoundaryPresent(
                                        bear.getXPosition(),
                                        bear.getYPosition())
                                    block.setblockXPosition(
                                        block.getBlockXPosition() - 30)
                                    totalDistance = totalDistance - 30

                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)

                        for block in self.blocks:
                            if block.getIsLeftBoundary() == True:
                                bear.setXPosition(bear.getXPosition() - 30)

                                totalDistance = totalDistance - 30

                        if bearAnimation % 120 < 40:
                            self.screen.blit(
                                self.bearWalking1,
                                (bear.getXPosition(), bear.getYPosition()))
                        else:

                            self.screen.blit(
                                self.bearWalking2,
                                (bear.getXPosition(), bear.getYPosition()))
                        dangerousObjects = self.mummys + self.fires + self.witches + self.greenBlobs + self.spikes + self.bossFires + self.frankenbear
                        for monster in dangerousObjects:

                            if bear.isBearHurt("RIGHT", bear.getXPosition(),
                                               bear.getYPosition(),
                                               monster.getXPosition(),
                                               monster.getYPosition(),
                                               monster.getName()
                                               ) == True and hurtTimer > 25:

                                hurtTimer = 0
                                bear.displayDamageOnBear(
                                    monster.getDamageAttack())
                                bear.setHp(bear.getHp() -
                                           monster.getDamageAttack())
                                self.screen.blit(
                                    self.hurtBear,
                                    (bear.getXPosition(), bear.getYPosition()))
                                bear.setXPosition(bear.getXPosition() - 30)
                                totalDistance = totalDistance - 30

                                monster.setHurtTimer(monster.getHurtTimer() +
                                                     1)
                            elif monster.getHurtTimer(
                            ) < 15 and monster.getHurtTimer() > 0:
                                monster.setHurtTimer(monster.getHurtTimer() +
                                                     1)

                                bear.displayDamageOnBear(
                                    monster.getDamageAttack())

                                self.screen.blit(
                                    self.hurtBear,
                                    (bear.getXPosition(), bear.getYPosition()))
                            else:
                                monster.setHurtTimer(0)

    # Jump =True ////////////////////////////////////////////////////////////
                    elif ((bear.getJumpStatus() == True
                           or bear.getLeftJumpStatus() == True)):

                        if bear.getXPosition() < self.rightBoundary:

                            jumpTimer = 0
                            for block in self.blocks:
                                block.isBoundaryPresent(
                                    bear.getXPosition(), bear.getYPosition())
                                if block.getIsLeftBoundary() == True:
                                    bear.setXPosition(bear.getXPosition() - 30)
                                    totalDistance = totalDistance - 30

                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)

                            bear.setXPosition(bear.getXPosition() + 30)
                            # totalDistance = totalDistance + 30

                        else:

                            jumpTimer = 0
                            moveObjects = []
                            moveObjects = self.mummys + self.fires + self.witches + self.greenBlobs + self.door + self.keys + self.spikes
                            for objects in moveObjects:
                                objects.setXPosition(objects.getXPosition() -
                                                     30)

                            for block in self.blocks:
                                block.isBoundaryPresent(
                                    bear.getXPosition(), bear.getYPosition())
                                if block.getIsLeftBoundary() == False:
                                    block.setblockXPosition(
                                        block.getBlockXPosition() - 30)
                                    backgroundScrollX = bear.getXPosition()
                                    background.setXPosition(backgroundScrollX)
                                elif block.getIsLeftBoundary() == True:
                                    block.setblockXPosition(
                                        block.getBlockXPosition() - 30)

                                    backgroundScrollX = bear.getXPosition()
                                    background.setXPosition(backgroundScrollX)

                        for block in self.blocks:
                            block.isBoundaryPresent(bear.getXPosition(),
                                                    bear.getYPosition())
                            if block.getIsLeftBoundary() == True:
                                bear.setXPosition(bear.getXPosition() - 30)
                                totalDistance = totalDistance - 30

                    bearAnimation = bearAnimation - 30
                    background.update(backgroundScrollX, bear.getYPosition())
                    self.deleteAndCreateObjects(totalDistance)
                elif keys[
                        pygame.
                        K_LEFT] and attackingAnimationCounter == 0 and attackingLeftAnimtationCounter == 0:
                    if attackingAnimationCounter == 0:
                        totalDistance = totalDistance - 30
                    bear.setLeftDirection(True)
                    if (bear.getJumpStatus() != True
                            and bear.getLeftJumpStatus() != True
                            and attackingAnimationCounter == 0):
                        if bear.getXPosition() > self.leftBoundary:
                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)
                            bear.setXPosition(bear.getXPosition() - 30)

                        else:
                            moveObjects = []
                            moveObjects = self.mummys + self.fires + self.witches + self.greenBlobs + self.door + self.keys + self.spikes
                            for objects in moveObjects:
                                objects.setXPosition(objects.getXPosition() +
                                                     30)

                            for block in self.blocks:
                                if block.getIsRightBoundary() == False:
                                    block.isBoundaryPresent(
                                        bear.getXPosition(),
                                        bear.getYPosition())
                                    block.setblockXPosition(
                                        block.getBlockXPosition() + 30)
                                if block.getIsRightBoundary() == True:
                                    totalDistance = totalDistance + 30
                                    block.isBoundaryPresent(
                                        bear.getXPosition(),
                                        bear.getYPosition())
                                    block.setblockXPosition(
                                        block.getBlockXPosition() + 30)

                            backgroundScrollX = bear.getXPosition()
                            background.setXPosition(backgroundScrollX)

                        for block in self.blocks:
                            if block.getIsRightBoundary() == True:
                                totalDistance = totalDistance + 30
                                bear.setXPosition(bear.getXPosition() + 30)

                        if bearAnimation % 188 < 80:
                            self.screen.blit(
                                self.bearWalkingLeft1,
                                (bear.getXPosition(), bear.getYPosition()))
                        else:
                            self.screen.blit(
                                self.bearWalkingLeft2,
                                (bear.getXPosition(), bear.getYPosition()))

                        dangerousObjects = self.mummys + self.fires + self.witches + self.greenBlobs + self.spikes + self.bossFires + self.frankenbear
                        for monster in dangerousObjects:
                            if bear.isBearHurt("RIGHT", bear.getXPosition(),
                                               bear.getYPosition(),
                                               monster.getXPosition(),
                                               monster.getYPosition(),
                                               monster.getName()
                                               ) == True and hurtTimer > 25:
                                bear.displayDamageOnBear(
                                    monster.getDamageAttack())
                                bear.setHp(bear.getHp() -
                                           monster.getDamageAttack())
                                hurtTimer = 0
                                self.screen.blit(
                                    self.hurtBear,
                                    (bear.getXPosition(), bear.getYPosition()))
                                bear.setXPosition(bear.getXPosition() + 30)
                                totalDistance = totalDistance + 30

                                monster.setHurtTimer(monster.getHurtTimer() +
                                                     1)
                            elif monster.getHurtTimer(
                            ) < 15 and monster.getHurtTimer() > 0:
                                monster.setHurtTimer(monster.getHurtTimer() +
                                                     1)

                                bear.displayDamageOnBear(
                                    monster.getDamageAttack())

                                self.screen.blit(
                                    self.hurtBear,
                                    (bear.getXPosition(), bear.getYPosition()))
                            else:
                                monster.setHurtTimer(0)

                    elif ((bear.getJumpStatus() == True
                           or bear.getLeftJumpStatus() == True)):
                        jumpTimer = 0
                        if bear.getXPosition() > self.leftBoundary:
                            backgroundScrollX = bear.getXPosition() + 30
                            background.setXPosition(backgroundScrollX)
                            bear.setXPosition(bear.getXPosition() - 30)
                            # totalDistance = totalDistance - 30

                        else:
                            moveObjects = []
                            moveObjects = self.mummys + self.fires + self.greenBlobs + self.witches + self.door + self.keys + self.spikes
                            for objects in moveObjects:
                                objects.setXPosition(objects.getXPosition() +
                                                     30)

                            for block in self.blocks:
                                block.isBoundaryPresent(
                                    bear.getXPosition(), bear.getYPosition())
                                if block.getIsRightBoundary() == False:
                                    block.setblockXPosition(
                                        block.getBlockXPosition() + 30)
                                    backgroundScrollX = bear.getXPosition()
                                    background.setXPosition(backgroundScrollX)
                                elif block.getIsRightBoundary() == True:
                                    block.setblockXPosition(
                                        block.getBlockXPosition() + 30)
                                    totalDistance = totalDistance + 30

                                    backgroundScrollX = bear.getXPosition()
                                    background.setXPosition(backgroundScrollX)
                        for block in self.blocks:
                            block.isBoundaryPresent(bear.getXPosition(),
                                                    bear.getYPosition())
                            if block.getIsRightBoundary() == True:
                                bear.setXPosition(bear.getXPosition() + 30)
                                totalDistance = totalDistance + 30
                    bearAnimation = bearAnimation - 30
                    background.update(backgroundScrollX, bear.getYPosition())

                elif keys[
                        pygame.
                        K_a] and attackingAnimationCounter == 0 and attackingLeftAnimtationCounter == 0 and attackCounterReady > 20:

                    attackingAnimationCounter = attackingAnimationCounter + 1
                    attackCounterReady = 0
                    monsters = self.mummys + self.witches + self.greenBlobs + self.frankenbear
                    for monster in monsters:

                        if isMonsterHurt(bear.getXPosition(),
                                         bear.getYPosition(),
                                         monster.getXPosition(),
                                         monster.getYPosition(),
                                         bear.getLeftDirection(),
                                         monster.getName()) == True:
                            if len(self.frankenbear) == 0:
                                monster.setXPosition(monster.getXPosition() +
                                                     30)

                            monster.setDamageReceived(bear.getDamageAttack())
                            monster.setStunned(1)
                            monster.setHealth(monster.getHealth() -
                                              bear.getDamageAttack())
                            hurtTimer = 0
                elif keys[pygame.K_ESCAPE]:
                    print(totalDistance)
                    pygame.quit()
                elif keys[pygame.K_f]:
                    print(totalDistance)

                    # elif monster.getIsMonsterHurtAnimation(
                    # ) < 90 and monster.getIsMonsterHurtAnimation() > 0:
                    #     monster.setIsMonsterHurtAnimation(
                    #         monster.getIsMonsterHurtAnimation() + 1)
                    #     # monster.setStunned(1)

                    # else:
                    #     monster.setStunned(0)
                    #     monster.setIsMonsterHurtAnimation(0)

                else:
                    # otherwise if bear not in jumping state display just standing or not attacking either (if animation not running)
                    if (bear.getJumpStatus() == False
                            and bear.getLeftJumpStatus()
                            == False) and attackingAnimationCounter == 0 and (
                                attackingLeftAnimtationCounter == 0
                                and attackingAnimationCounter == 0
                                and isBearHurtAnimation == 0):

                        if bear.getLeftDirection() == False:
                            self.screen.blit(
                                self.standingBear,
                                (bear.getXPosition(), bear.getYPosition()))
                        else:
                            self.screen.blit(
                                self.standingBearLeft,
                                (bear.getXPosition(), bear.getYPosition()))
                    dangerousObjects = self.mummys + self.fires + self.witches + self.greenBlobs + self.spikes + self.bossFires + self.frankenbear
                    for monster in dangerousObjects:
                        if bear.isBearHurt(
                                "LEFT",
                                bear.getXPosition(), bear.getYPosition(),
                                monster.getXPosition(), monster.getYPosition(),
                                monster.getName()) == True and hurtTimer > 25:
                            bear.displayDamageOnBear(monster.getDamageAttack())
                            bear.setHp(bear.getHp() -
                                       monster.getDamageAttack())
                            hurtTimer = 0
                            self.screen.blit(
                                self.hurtBear,
                                (bear.getXPosition(), bear.getYPosition()))

                            if (positionRelativeToMonster(
                                    bear.getXPosition(), bear.getYPosition(),
                                    monster.getXPosition(),
                                    monster.getYPosition()) == "RIGHT"):
                                backgroundScrollX = bear.getXPosition() + 30
                                background.setXPosition(backgroundScrollX)
                                bear.setXPosition(bear.getXPosition() + 30)
                                totalDistance = totalDistance + 30

                                self.screen.blit(
                                    self.hurtBear,
                                    (bear.getXPosition(), bear.getYPosition()))

                            else:
                                backgroundScrollX = bear.getXPosition() - 60
                                background.setXPosition(backgroundScrollX)
                                bear.setXPosition(bear.getXPosition() - 60)

                                totalDistance = totalDistance - 60

                                self.screen.blit(
                                    self.hurtBear,
                                    (bear.getXPosition(), bear.getYPosition()))
                                monster.setHurtTimer(monster.getHurtTimer() +
                                                     1)
                        elif monster.getHurtTimer(
                        ) < 15 and monster.getHurtTimer() > 0:
                            monster.setHurtTimer(monster.getHurtTimer() + 1)

                            bear.displayDamageOnBear(monster.getDamageAttack())

                            self.screen.blit(
                                self.hurtBear,
                                (bear.getXPosition(), bear.getYPosition()))
                        else:
                            monster.setHurtTimer(0)

    # /////////////////////////////////////////////////////////////////////////////////////////////////////////////

                if attackingAnimationCounter < 12 and attackingAnimationCounter >= 1:
                    attackingAnimationCounter = attackingAnimationCounter + 1
                    if (bear.getLeftDirection() == True):
                        self.screen.blit(
                            self.bearAttackingLeft,
                            (bear.getXPosition() - 80, bear.getYPosition()))
                    else:
                        self.screen.blit(
                            self.bearAttacking,
                            (bear.getXPosition(), bear.getYPosition()))

                elif attackingAnimationCounter >= 12:
                    attackingAnimationCounter = 0
                elif attackingLeftAnimtationCounter < 12 and attackingLeftAnimtationCounter >= 1:
                    attackingLeftAnimtationCounter = attackingLeftAnimtationCounter + 1
                    self.screen.blit(
                        self.bearAttackingLeft,
                        (bear.getXPosition(), bear.getYPosition()))

                elif attackingLeftAnimtationCounter >= 12:
                    attackingLeftAnimtationCounter = 0

                elif bear.getJumpStatus() == True:
                    bear.jump(self.blocks)

                elif bear.getLeftJumpStatus() == True:
                    bear.leftJump(self.blocks)

# # /////////////////////////////////////////////////////////////////////////////////////////////////////////////

            bear.boundaryExtraCheck()
            jumpTimer = jumpTimer + 1
            monsters = self.mummys + self.witches + self.greenBlobs

            for monster in monsters:

                if monster.getHealth() > 0:

                    monster.drawMonster()
                elif monster.getHealth(
                ) <= 0 and monster.getDestructionAnimationCount(
                ) < 20 and monster.getStartDestructionAnimationStatus(
                ) == False:

                    monster.setStartDestructionAnimation(True)

                elif monster.getStartDestructionAnimationStatus() == True:

                    monster.drawDestruction(bear.getDamageAttack())

                    if monster.getDestructionAnimationCount() >= 30:
                        monster.setStartDestructionAnimation(False)

                        bear.setCurrentExp(bear.getCurrentExp() +
                                           monster.getExp())

                else:

                    try:
                        self.mummys.remove(monster)
                    except:
                        print("couldnt remove")
                    try:
                        self.witches.remove(monster)
                    except:
                        print("couldnt remove object")
                    try:
                        self.greenBlobs.remove(monster)
                    except:
                        print("couldnt delete blob")

                    if monster.getName() == "greenBlob" and monster.getHeight(
                    ) == 100:

                        greenBlob = GreenBlob(monster.getXPosition() - 40, 350,
                                              70, 100, self.screen)
                        self.greenBlobs.append(greenBlob)
                        greenBlob = GreenBlob(monster.getXPosition() + 40, 350,
                                              70, 100, self.screen)
                        self.greenBlobs.append(greenBlob)
                    elif monster.getName() == "bigMummy":
                        key = KeyItem(self.screen, monster.getXPosition(),
                                      monster.getYPosition())
                        self.keys.append(key)

                    del monster
# boss7
            for monster in self.frankenbear:
                print(monster.getHealth())
                if monster.getHealth(
                ) <= 0 and monster.getDestructionAnimationCount(
                ) < 20 and monster.getStartDestructionAnimationStatus(
                ) == False:

                    monster.setStartDestructionAnimation(True)

                elif monster.getStartDestructionAnimationStatus() == True:
                    monster.drawDestruction(bear.getDamageAttack())

                    if monster.getDestructionAnimationCount() >= 30:
                        monster.setStartDestructionAnimation(False)

                        bear.setCurrentExp(bear.getCurrentExp() +
                                           monster.getExp())
                        try:
                            self.frankenbear.remove(monster)
                            del monster
                        except:
                            print("couldnt delete frankenBear")
                        bear.setArrayText([
                            '   Thank you for playing!   ', '     ',
                            ' Press "s" to continue  '
                        ])
                        bear.setArrayText([
                            ' The screen will close now  ', '      ',
                            ' Press "s" to continue  '
                        ])

                        bear.setEndText(False)
                        self.isFinalBossDestroyed = True

            for key in self.keys:
                key.drawKey()
                key.boundaryExtraCheck()
                if key.isKeyGrabbed(bear.getXPosition(), bear.getYPosition(),
                                    key.getXPosition(),
                                    key.getYPosition()) == True:
                    self.keys.remove(key)
                    self.isDoor1Open = True

            for fire in self.fires:
                fire.drawFireBall()

                if fire.getXPosition() < 30 or fire.getXPosition(
                ) > 500 or fire.getYPosition() < 0:
                    self.triggerFire = True
                    self.fires.remove(fire)
                    del fire

            if self.triggerFire == True and len(
                    self.fires) == 0 and len(self.witches) != 0:
                self.triggerFire = False

                for witch in self.witches:
                    witch.setThrowsFireBalls(True)
                    for iteration in range(3):
                        randomXVelocity = random.randint(-7, 7)
                        randomYVelocity = random.randint(1, 12)
                        self.fires.append(
                            FireBall(witch.getXPosition(),
                                     witch.getYPosition(), randomXVelocity,
                                     randomYVelocity, self.fireBall,
                                     self.screen))

# **************************************************
            for witch in self.witches:
                witch.drawMonster()

            time.sleep(0.010)
            hurtTimer = hurtTimer + 1
            # boss5
            if totalDistance > 66900 and totalDistance < 67000 and self.createdBoss == False:
                self.createdBoss = True
                print("hhhhhsdjfdsajhkfhdakfhdajsk")
                # frankenbear = FrankenBear(300, 40, self.screen)
                # self.frankenbear.append(frankenbear)

            if totalDistance > 67000 and self.activeMonsters[9] == False:
                try:
                    for block in self.blocks:
                        del block
                except:
                    print("")
                try:
                    for spike in self.spikes:
                        del spike
                except:
                    print("")
                try:
                    for mummy in self.mummys:
                        del mummy
                except:
                    print("")
                try:
                    for witch in self.witches:
                        del witch
                except:
                    print("")
                self.spikes = []
                self.activeMonsters[9] = True
                self.mummys = []
                self.witches = []
                self.blocks = []
                self.greenBlobs = []
                self.fires = []
                self.activeMonsters[1] = True

            if totalDistance > 67000:
                totalDistance = 700000

                background.setStopBackground(True)
                self.leftBoundary = 80
                self.rightBoundary = 700
                self.screen.blit(self.pillar, (-40, 0))
                self.screen.blit(self.pillar, (800, 0))
                self.bossTimerAnimation = self.bossTimerAnimation + 1

                if self.bossTimerAnimation > 30:
                    background.setBlackBackground(True)

    # boss6
                if self.bossTimerAnimation > 170:
                    if self.showBoss == True:
                        frankenbear = FrankenBear(300, 40, self.screen)
                        self.frankenbear.append(frankenbear)
                        self.showBoss = False
                    for frankenbear in self.frankenbear:
                        frankenbear.drawMonster()
                        if (frankenbear.getThrowFireBallLeft()
                                == True) and len(self.bossFires) == 0:
                            frankenbear.setThrowFireBallLeft(False)
                            for iteration in range(3):
                                randomXVelocity = random.randint(-22, -4)
                                randomYVelocity = random.randint(7, 12)
                                self.bossFires.append(
                                    FireBall(frankenbear.getXPosition() + 200,
                                             frankenbear.getYPosition() + 100,
                                             randomXVelocity, randomYVelocity,
                                             self.fireBossBall, self.screen))
                        elif (frankenbear.getThrowFireBallRight()
                              == True) and len(self.bossFires) == 0:
                            frankenbear.setThrowFireBallLeft(False)
                            for iteration in range(3):
                                randomXVelocity = random.randint(4, 22)
                                randomYVelocity = random.randint(7, 12)

                                self.bossFires.append(
                                    FireBall(frankenbear.getXPosition() + 200,
                                             frankenbear.getYPosition() + 100,
                                             randomXVelocity, randomYVelocity,
                                             self.fireBossBall, self.screen))

                    for fire in self.bossFires:
                        fire.drawFireBall()

                        if fire.getXPosition() < 30 or fire.getXPosition(
                        ) > 800 or fire.getYPosition() < 0:
                            self.triggerFire = True
                            self.bossFires.remove(fire)
                            del fire

                # print(len(self.fires))
                # for fire in self.fires:
                #     fire.drawFireBall()
                #     print("fiiiiiiirrreee")
                #     print(fire.getXPosition())

                # if fire.getXPosition() < 30 or fire.getXPosition(
                # ) > 500 or fire.getYPosition() < 0:
                #     frankenbear.setThrowFireBallLeft(True)

                #     self.fires.remove(fire)
                #     del fire
                # if frankenbear.getThrowFireBallLeft() == True and len(
                #         self.fires) == 0:

                #     randomXVelocity = random.randint(-1, 1)
                #     randomYVelocity = random.randint(-1, 1)
                #     for iteration in range(3):
                #         randomXVelocity = random.randint(-1, 1)
                #         randomYVelocity = random.randint(1, 2)
                #         self.fires.append(
                #             FireBall(frankenbear.getXPosition(),
                #                      frankenbear.getYPosition(),
                #                      randomXVelocity, randomYVelocity,
                #                      self.fireBall, self.screen))
                bear.displayBearExp()
            triggerWitchFireBallAnimation = triggerWitchFireBallAnimation + 1
            attackCounterReady = attackCounterReady + 1
            for block in self.blocks:
                block.drawRectangle()
                block.isBoundaryPresent(bear.getXPosition(),
                                        bear.getYPosition())
                if block.getDropStatus() == True and bear.getComingUp(
                ) == False:
                    if bear.getYPosition() + 100 < floorHeight:
                        bear.setYPosition(bear.getYPosition() + 30)

                    elif bear.getYPosition() + 100 == floorHeight:
                        block.setDropStatus(False)
                        block.setOnPlatform(False)
                        bear.setJumpStatus(False)
                        bear.setLeftJumpStatus(False)
            bear.displayBearHp()
            bear.displayBearExp()

            if totalDistance > 5630 and self.triggerText1 == False:
                bear.setEndText(False)
                self.triggerText1 = True

                bear.setArrayText([
                    '   The big mummy ahead has   ',
                    ' a red thing on its forhead       ',
                    '    Press "s" to continue  '
                ])
                bear.setArrayText([
                    ' Attack It there! ', '  Hes carrying a key. ',
                    '   Press "s" to continue  '
                ])

            for spike in self.spikes:
                spike.draw()
            for door in self.door:
                door.drawRectangle()
                for mummy in self.mummys:
                    if mummy.getXPosition() >= door.getXPosition():
                        mummy.setXPosition(mummy.getXPosition() - 40)
                        mummy.setDirection(mummy.getDirection() * -1)
                if self.isDoor1Open == False and door.getXPosition(
                ) - 90 <= bear.getXPosition():
                    bear.setXPosition(bear.getXPosition() - 30)
                    # self.door1.setIsOpen(True)
                    totalDistance = totalDistance - 30
                    if self.triggerText3 == False and self.isDoor1Open == False:

                        bear.setArrayText([
                            '   Attack the Mummys forhead    ', '     ',
                            ' Press "s" to continue  '
                        ])
                        bear.setArrayText([
                            ' To grab the key  ', ' For the locked door.     ',
                            ' Press "s" to continue  '
                        ])

                        self.triggerText3 = True
                        bear.setEndText(False)

                elif self.isDoor1Open == True and self.triggerText2 == False:

                    bear.setArrayText([
                        '   Grabbed Key!   ', '     ',
                        ' Press "s" to continue  '
                    ])
                    bear.setArrayText([
                        '  You can open the door now.  ', '      ',
                        '  Press "s" to continue  '
                    ])

                    self.triggerText2 = True
                    bear.setEndText(False)
                elif self.isDoor1Open == True and door.getXPosition(
                ) - 90 <= bear.getXPosition() and self.triggerText5 == False:
                    bear.setXPosition(bear.getXPosition() - 30)
                    totalDistance = totalDistance - 30
                    self.triggerText5 = True

                    bear.setArrayText([
                        '   You used key!   ', '     ',
                        ' Press "s" to continue  '
                    ])
                    bear.setArrayText([
                        '  The door is unlocked.  ', '      ',
                        '  Press "s" to continue  '
                    ])
                    bear.setEndText(False)

            if bear.getEndText() == False:
                bear.displayTextBox()
            if bear.getHealth() <= 0 and self.triggerText4 == False:
                bear.setEndText(False)
                self.triggerText4 = True

                bear.setArrayText(
                    ['   GAME OVER!   ', '     ', ' Press "s" to continue  '])
                bear.setArrayText([
                    '  GAME OVER! : Please try again  ', '     ',
                    '  Press "s" to continue    '
                ])
                self.escape = True

            elif self.escape == True and bear.getEndText() == True:
                pygame.quit()

            pygame.display.flip()
            pygame.event.pump()
            # **************************************************


###delete2

    def deleteAndCreateObjects(self, backgroundScrollX):

        if backgroundScrollX > 3850 and self.activeMonsters[1] == False:
            try:
                for block in self.blocks:
                    del block
            except:
                print("")
            try:
                for mummy in self.mummys:
                    del mummy
            except:
                print("")
            try:
                for witch in self.witches:
                    del witch
            except:
                print("")

            self.activeMonsters[1] = True
            self.mummys = []
            self.witches = []
            self.blocks = []
            self.greenBlobs = []
            self.fires = []

            block5 = Block(3030, 340, 100, 60, "red", self.screen)
            block7 = Block(3240, 340, 100, 60, "monster", self.screen)
            block6 = Block(3500, 340, 100, 60, "monster", self.screen)
            block8 = Block(3900, 340, 50, 60, "red", self.screen)
            self.blocks.append(block5)
            self.blocks.append(block6)
            self.blocks.append(block7)
            self.blocks.append(block8)

            mummy = Mummy(3030, 100, 200, 300, self.mummy1, self.mummy2,
                          self.screen)
            self.mummys.append(mummy)
            self.door1 = Door(self.screen, 4200)

            self.door.append(self.door1)
            block9 = Block(4300, 0, 2800, 100, "greyRock", self.screen)
            self.blocks.append(block9)
        elif backgroundScrollX > 12000 and self.activeMonsters[2] == False:
            try:
                for block in self.blocks:
                    del block
            except:
                print("")
            try:
                for mummy in self.mummys:
                    del mummy
            except:
                print("")
            try:
                for witch in self.witches:
                    del witch
            except:
                print("")
            self.activeMonsters[2] = True
            self.door = []
            self.mummys = []
            self.witches = []
            self.blocks = []
            self.greenBlobs = []
            self.fires = []

            block1 = Block(2800, 340, 100, 60, "greyRock", self.screen)
            block2 = Block(3900, 100, 150, 300, "monster", self.screen)
            block6 = Block(3400, 160, 130, 60, "greyRock", self.screen)
            block4 = Block(2000, 340, 600, 60, "greyRock", self.screen)
            self.blocks.append(block1)
            self.blocks.append(block2)
            self.blocks.append(block6)
            self.blocks.append(block4)
            witch = Witch(4200, 100, self.witch, self.witch2, self.screen)
            # witch2 = Witch(600, 100, self.screen)
            self.witches.append(witch)
            witch2 = Witch(4500, 200, self.witch, self.witch2, self.screen)
            # witch2 = Witch(600, 100, self.screen)
            self.witches.append(witch2)
            witch3 = Witch(3300, 250, self.witch, self.witch2, self.screen)
            # witch2 = Witch(600, 100, self.screen)
            self.witches.append(witch)
            witch4 = Witch(3100, 250, self.witch, self.witch2, self.screen)
            # witch2 = Witch(600, 100, self.screen)

            witch5 = Witch(3000, 250, self.witch, self.witch2, self.screen)
            # witch2 = Witch(600, 100, self.screen)
            self.witches.append(witch3)
            self.witches.append(witch4)
            self.witches.append(witch5)

            witch6 = Witch(2900, 250, self.witch, self.witch2, self.screen)
            self.witches.append(witch6)
            self.triggerFire = True

        elif backgroundScrollX > 18000 and self.activeMonsters[3] == False:
            self.activeMonsters[3] = True
            try:
                for block in self.blocks:
                    del block
            except:
                print("")
            try:
                for mummy in self.mummys:
                    del mummy
            except:
                print("")
            try:
                for witch in self.witches:
                    del witch
            except:
                print("")

            self.mummys = []
            self.witches = []
            self.blocks = []
            self.greenBlobs = []
            self.fires = []
            block1 = Block(4000, 340, 900, 60, "greyRock", self.screen)

            self.blocks.append(block1)
            greenBlob = GreenBlob(3100, 300, 100, 100, self.screen)
            self.greenBlobs.append(greenBlob)
            greenBlob2 = GreenBlob(3200, 300, 100, 100, self.screen)
            self.greenBlobs.append(greenBlob2)
            greenBlob3 = GreenBlob(4000, 300, 100, 100, self.screen)
            self.greenBlobs.append(greenBlob3)
            block1 = Block(4000, 280, 1000, 60, "greyRock", self.screen)
            greenBlob4 = GreenBlob(5800, 300, 100, 100, self.screen)
            self.greenBlobs.append(greenBlob4)
            greenBlob5 = GreenBlob(6100, 300, 100, 100, self.screen)
            self.greenBlobs.append(greenBlob5)
            block2 = Block(6000, 220, 2000, 60, "greyRock", self.screen)

            self.blocks.append(block2)
            x = 1000
            for mummy in range(12):
                x = x + 620
                mummy = Mummy(x, 300, 100, 100, self.mummy1, self.mummy2,
                              self.screen)
                self.mummys.append(mummy)
        elif backgroundScrollX > 26000 and self.activeMonsters[4] == False:
            self.activeMonsters[4] = True
            try:
                for block in self.blocks:
                    del block
            except:
                print("")
            try:
                for mummy in self.mummys:
                    del mummy
            except:
                print("")
            try:
                for witch in self.witches:
                    del witch
            except:
                print("")
            block1 = Block(8000, 280, 2000, 60, "greyRock", self.screen)

            self.blocks.append(block1)
            block2 = Block(8500, 340, 1000, 60, "greyRock", self.screen)

            self.blocks.append(block2)
            x = 4000

            for mummy in range(10):
                x = x + 150
                mummy = Mummy(x, 300, 100, 100, self.mummy1, self.mummy2,
                              self.screen)
                self.mummys.append(mummy)

        elif backgroundScrollX > 33000 and self.activeMonsters[5] == False:
            self.mummys = []
            self.witches = []
            self.blocks = []
            self.greenBlobs = []
            self.fires = []
            self.activeMonsters[5] = True
            try:
                for block in self.blocks:
                    del block
            except:
                print("")
            try:
                for mummy in self.mummys:
                    del mummy
            except:
                print("")
            try:
                for witch in self.witches:
                    del witch
            except:
                print("")

            block1 = Block(610, 220, 3000, 60, "striped", self.screen)

            self.blocks.append(block1)
            block2 = Block(800, 280, 2000, 60, "stripedFlip", self.screen)

            self.blocks.append(block2)
            block3 = Block(1100, 340, 1000, 60, "striped", self.screen)

            self.blocks.append(block3)
            x = 400
            for mummy in range(6):
                x = x + 250
                mummy = Mummy(x, 300, 100, 100, self.mummy1, self.mummy2,
                              self.screen)
                self.mummys.append(mummy)
            witch = Witch(1100, 100, self.witch, self.witch2, self.screen)
            # witch2 = Witch(600, 100, self.screen)
            self.witches.append(witch)
            witch2 = Witch(1300, 100, self.witch, self.witch2, self.screen)
            # witch2 = Witch(600, 100, self.screen)
            self.witches.append(witch2)

        elif backgroundScrollX > 39000 and self.activeMonsters[6] == False:
            self.mummys = []
            self.witches = []

            self.greenBlobs = []
            self.fires = []
            self.activeMonsters[6] = True

            try:
                for mummy in self.mummys:
                    del mummy
            except:
                print("")
            try:
                for witch in self.witches:
                    del witch
            except:
                print("")

            block1 = Block(1710, 220, 3500, 60, "checkered", self.screen)

            block2 = Block(1600, 280, 3500, 60, "checkered", self.screen)

            block3 = Block(1500, 340, 3000, 60, "checkered", self.screen)
            self.blocks.append(block2)
            self.blocks.append(block1)
            self.blocks.append(block3)

            greenBlob = GreenBlob(900, 300, 100, 100, self.screen)
            self.greenBlobs.append(greenBlob)
            greenBlob2 = GreenBlob(1200, 300, 100, 100, self.screen)
            self.greenBlobs.append(greenBlob2)
            greenBlob3 = GreenBlob(1300, 300, 100, 100, self.screen)
            self.greenBlobs.append(greenBlob3)
            block1 = Block(1500, 100, 1000, 60, "greyRock", self.screen)
            greenBlob4 = GreenBlob(1900, 300, 100, 100, self.screen)
            self.greenBlobs.append(greenBlob4)
            greenBlob5 = GreenBlob(800, 300, 100, 100, self.screen)
            self.greenBlobs.append(greenBlob5)

            x = 16000
            for mummy in range(3):
                x = x + 450
                mummy = Mummy(x, 300, 100, 100, self.mummy1, self.mummy2,
                              self.screen)
                self.mummys.append(mummy)
        elif backgroundScrollX > 48000 and self.activeMonsters[7] == False:
            self.mummys = []
            self.witches = []
            self.blocks = []
            self.greenBlobs = []
            self.fires = []
            self.activeMonsters[6] = True
            try:
                for mummy in self.mummys:
                    del mummy
            except:
                print("")
            try:
                for witch in self.witches:
                    del witch
            except:
                print("")
            block1 = Block(2300, 340, 100, 60, "checkered", self.screen)
            block2 = Block(3000, 340, 100, 60, "checkered", self.screen)
            self.blocks.append(block2)
            self.blocks.append(block1)
            self.activeMonsters[7] = True
            witch = Witch(4900, 200, self.witch, self.witch2, self.screen)
            # witch2 = Witch(600, 100, self.screen)
            self.witches.append(witch)
            witch2 = Witch(4800, 250, self.witch, self.witch2, self.screen)
            # witch2 = Witch(600, 100, self.screen)
            self.witches.append(witch2)
            witch3 = Witch(5000, 250, self.witch, self.witch2, self.screen)
            # witch2 = Witch(600, 100, self.screen)
            self.witches.append(witch)
            witch4 = Witch(5100, 150, self.witch, self.witch2, self.screen)
            # witch2 = Witch(600, 100, self.screen)

            self.witches.append(witch)
            self.witches.append(witch2)
            self.witches.append(witch3)
            self.witches.append(witch4)
            block1 = Block(4510, 0, 5000, 80, "checkered", self.screen)

            self.blocks.append(block1)
        elif backgroundScrollX > 54000 and self.activeMonsters[8] == False:
            self.activeMonsters[8] = True
            self.mummys = []
            self.witches = []
            self.greenBlobs = []
            self.fires = []
            self.activeMonsters[6] = True

            try:
                for mummy in self.mummys:
                    del mummy
            except:
                print("")
            try:
                for witch in self.witches:
                    del witch
            except:
                print("")

            block1 = Block(4310, 220, 100, 60, "checkered", self.screen)
            block2 = Block(4810, 220, 100, 60, "checkered", self.screen)
            self.blocks.append(block1)
            self.blocks.append(block2)
            block3 = Block(5310, 280, 100, 60, "checkered", self.screen)
            block4 = Block(3900, 340, 100, 60, "checkered", self.screen)
            self.blocks.append(block3)
            self.blocks.append(block4)
            self.spike = SpikeBlock(4100, 340, self.screen)
            self.spike2 = SpikeBlock(4600, 340, self.screen)
            self.spike3 = SpikeBlock(5100, 340, self.screen)
            self.spike4 = SpikeBlock(5900, 340, self.screen)
            self.spikes.append(self.spike)
            self.spikes.append(self.spike2)
            self.spikes.append(self.spike3)
            self.spikes.append(self.spike4)

            block5 = Block(6200, 280, 100, 60, "checkered", self.screen)
            self.blocks.append(block5)
            # self.blocks.append(block6)


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
        self.redBlock = pygame.image.load("Game/Images/Bear/redBlock.png")
        self.redBlock = pygame.transform.scale(self.redBlock, (width, height))
        self.blockClosedEyes = pygame.image.load(
            "Game/Images/monsterBlock3.png")
        self.blockClosedEyes = pygame.transform.scale(self.blockClosedEyes,
                                                      (width, height))
        self.monsterBlockTimer = 0
        if self.type == "monster":
            self.redBlock = pygame.image.load("Game/Images/monsterBlock1.png")
            self.redBlock = pygame.transform.scale(self.redBlock,
                                                   (width, height))
        elif self.type == "greyRock":
            self.redBlock = pygame.image.load("Game/Images/rocks.png")
            self.redBlock = pygame.transform.scale(self.redBlock,
                                                   (width, height))
        elif self.type == "checkered":
            self.redBlock = pygame.image.load("Game/Images/checkered.png")
            self.redBlock = pygame.transform.scale(self.redBlock,
                                                   (width, height))
        elif self.type == "striped":
            self.redBlock = pygame.image.load("Game/Images/stripes.png")
            self.redBlock = pygame.transform.scale(self.redBlock,
                                                   (width, height))

        elif self.type == "stripedFlip":
            self.redBlock = pygame.image.load("Game/Images/stripes.png")
            self.redBlock = pygame.transform.flip(self.redBlock, True, False)
            self.redBlock = pygame.transform.scale(self.redBlock,
                                                   (width, height))

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
            self.monsterBlockTimer = self.monsterBlockTimer + 1
        if self.monsterBlockTimer <= self.maxBlinkTime:
            self.screen.blit(
                self.redBlock,
                (self.getBlockXPosition(), self.getBlockYPosition()))
        elif self.monsterBlockTimer > self.maxBlinkTime and self.monsterBlockTimer < (
                self.maxBlinkTime + 10):
            self.screen.blit(
                self.blockClosedEyes,
                (self.getBlockXPosition(), self.getBlockYPosition()))

        else:
            self.monsterBlockTimer = 1
            self.maxBlinkTime = random.randint(30, 150)
            self.screen.blit(
                self.blockClosedEyes,
                (self.getBlockXPosition(), self.getBlockYPosition()))

    def isBoundaryPresent(self, bearX, bearY):
        floorHeight = 400
        self.setIsLeftBoundary(False)
        self.setIsRightBoundary(False)
        # ///////////////////////////////////////////// ON PLATFORM
        if ((bearX + 100 > self.getBlockXPosition() + self.getWidth()
             and bearX < self.getBlockXPosition() + self.getWidth() + 30) and
            (bearY + 100 <= self.getBlockYPosition() + self.getHeight()
             and bearY + 100 == self.getBlockYPosition())):

            self.setOnPlatform(True)
            self.setDropStatus(False)

        elif ((bearX > self.getBlockXPosition())
              and (bearX < self.getBlockXPosition() + self.getWidth() + 30) and
              (bearX + 100 < self.getBlockXPosition() + self.getWidth() + 30)
              and (bearX + 100 > self.getBlockXPosition())
              and (bearY + 100 == self.getBlockYPosition())):
            self.setOnPlatform(True)

        elif (
            (bearX < self.getBlockXPosition() + self.getWidth() + 30
             and bearX + 100 > self.getBlockXPosition() + self.getWidth() + 30)
                and (bearY + 100 == self.getBlockYPosition())):

            self.setDropStatus(False)
            self.setOnPlatform(True)
        elif ((bearX > self.getBlockXPosition() + self.getWidth()) and
              (bearX + 100 < self.getBlockXPosition() + self.getWidth() + 30)
              and (bearY + 100 == self.getBlockYPosition())):
            self.setOnPlatform(True)
            self.setDropStatus(False)

        elif ((bearX < self.getBlockXPosition())
              and (bearX + 100 > self.getBlockXPosition())
              and (bearY + 100 == self.getBlockYPosition())):
            self.setOnPlatform(True)
            self.setDropStatus(False)

        elif (
            (bearX + 100 > self.getBlockXPosition()
             and bearX + 100 < self.getBlockXPosition() + self.getWidth() + 30)
                and
            (bearY + 100 <= self.getBlockYPosition() + self.getHeight()
             and bearY + 100 == self.getBlockYPosition())):

            self.setOnPlatform(True)
            self.setDropStatus(False)

# ///////////////////////////////////////////// OFF PLATFORM

        if ((bearX > self.getBlockXPosition()) and
            (bearX + 100 < self.getBlockXPosition() + self.getWidth() + 30)
                and (bearY + 100 < self.getBlockYPosition())):

            self.setOnPlatform(False)

        elif ((bearX < self.getBlockXPosition()
               and bearX + 100 < self.getBlockXPosition())
              and (bearY + 100 == self.getBlockYPosition())
              and self.getOnPlatform() == True):

            self.setDropStatus(True)
            self.setOnPlatform(False)

        elif ((bearX + 100 > self.getBlockXPosition() + self.getWidth()
               and bearX > self.getBlockXPosition() + self.getWidth())
              and (bearY + 100 == self.getBlockYPosition())
              and self.getOnPlatform() == True):

            self.setDropStatus(True)
            self.setOnPlatform(False)

        if ((bearX + 100 > self.getBlockXPosition() + self.getWidth()
             and bearX > self.getBlockXPosition() + self.getWidth())
                and (bearY + 100 < self.getBlockYPosition())
                and self.getOnPlatform() == True):

            self.setDropStatus(True)
            self.setOnPlatform(False)

        if ((bearX < self.getBlockXPosition()
             and bearX + 100 < self.getBlockXPosition())
                and (bearY + 100 < self.getBlockYPosition())
                and self.getOnPlatform() == True):

            self.setDropStatus(True)
            self.setOnPlatform(False)

        # Right foot out left foot in
        if ((bearX + 100 > self.getBlockXPosition()
             and bearX + 100 < self.getBlockXPosition() + self.getWidth() - 30)
                and
            (bearY + 100 <= self.getBlockYPosition() + self.getHeight()
             and bearY + 100 > self.getBlockYPosition())):

            self.setIsInsideBox(True)
        elif ((bearX > self.getBlockXPosition()
               and bearX < self.getBlockXPosition() + self.getWidth())
              and (bearY + 100 == floorHeight)
              and self.getBlockYPosition() == floorHeight):

            self.setIsInsideBox(True)

        if ((bearX + 100 < self.getBlockXPosition() + self.getWidth() + 30
             and bearX + 100 > self.getBlockXPosition())
                and (bearY <= self.getBlockYPosition() + self.getHeight()
                     and bearY > self.getBlockYPosition())):

            self.setIsLeftBoundary(True)
            self.setDropStatus(False)

# ///////////////////////////////////////////// Left or right boundary
        if ((bearX + 100 < self.getBlockXPosition() + self.getWidth() + 30
             and bearX + 100 > self.getBlockXPosition()) and
            (bearY + 100 <= self.getBlockYPosition() + self.getHeight()
             and bearY + 100 > self.getBlockYPosition())):
            self.setIsLeftBoundary(True)
            self.setDropStatus(False)

        elif ((bearX > self.getBlockXPosition() + 30
               and bearX < self.getBlockXPosition() + self.getWidth())
              and (bearY + 100 <= self.getBlockYPosition() + self.getHeight()
                   and bearY + 100 > self.getBlockYPosition())):

            self.setIsRightBoundary(True)
            self.setDropStatus(False)
        if bearY + 100 == floorHeight:
            self.setDropStatus(False)
            self.setOnPlatform(False)


# ///////////////////////////////////////////////////////////////////////////////////////////////////////////////


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


def isBearHurt(positionRelative, bearXPosition, bearYPosition, objectXPosition,
               objectYPosition, object):
    width = 0
    height = 0
    if object == "mummy":
        width = 100
        height = 100
    elif object == "bigMummy":
        width = 200
        height = 500
    elif object == "fireBall":
        width = 110
        height = 110
    elif object == "witch":
        width = 100
        height = 180
    elif object == "greenBlob":
        width = 130
        height = 120
    elif object == "bigGreenBlob":
        width = 300
        height = 400
    elif object == "spikes":
        width = 600
        height = 60
    elif object == "frankenbears":
        width = 300
        height = 300
    else:
        return False

    if ((bearXPosition + 70 >= objectXPosition
         and bearXPosition + 70 <= objectXPosition + width)
            and (bearYPosition + 100 <= objectYPosition + height
                 and bearYPosition + 100 >= objectYPosition)):
        return True
    if ((bearXPosition >= objectXPosition
         and bearXPosition <= objectXPosition + width)
            and (bearYPosition + 100 <= objectYPosition + height
                 and bearYPosition + 100 >= objectYPosition)):

        return True
    if ((bearXPosition <= objectXPosition + width
         and bearXPosition >= objectXPosition)
            and (bearYPosition + 100 <= objectYPosition + height
                 and bearYPosition + 100 >= objectYPosition)):

        return True

    elif (bearYPosition + 100 >= objectYPosition + height - 70
          and bearXPosition >= objectXPosition + width
          and bearXPosition <= objectXPosition + width - 10):

        return True
    else:
        return False


def isMonsterHurt(bearXPosition, bearYPosition, mummyXPosition, mummyYPosition,
                  facingMonsterFrom, monsterType):

    if monsterType != "frankenbears":

        if ((bearXPosition + 220 >= mummyXPosition
             and bearXPosition <= mummyXPosition)
                and bearXPosition < mummyXPosition
                and facingMonsterFrom == False
                and bearYPosition + 50 > mummyYPosition
                and bearYPosition + 50 < mummyYPosition + 100):

            return True

        elif ((bearXPosition - 140 <= mummyXPosition + 100)
              and bearXPosition - 140 >= mummyXPosition
              and bearXPosition > mummyXPosition
              and bearYPosition + 50 > mummyYPosition
              and bearYPosition + 50 < mummyYPosition + 100):

            return True
        # elif ((bearXPosition - 140 >= mummyXPosition + 100)
        #       and bearXPosition - 140 <= mummyXPosition
        #       and bearXPosition > mummyXPosition
        #       and bearYPosition + 50 > mummyYPosition
        #       and bearYPosition + 50 < mummyYPosition + 100):
        #     print("got here 1")
        #     return True
        elif ((bearXPosition <= mummyXPosition + 100
               and bearXPosition >= mummyXPosition)
              and (bearYPosition + 50 <= mummyYPosition + 100
                   and bearYPosition + 50 >= mummyYPosition)):

            return True
    else:

        if ((bearXPosition + 220 >= mummyXPosition
             and bearXPosition <= mummyXPosition)
                and bearXPosition < mummyXPosition
                and facingMonsterFrom == False
                and bearYPosition + 50 > mummyYPosition
                and bearYPosition + 50 < mummyYPosition + 240):

            return True

        elif ((bearXPosition - 140 <= mummyXPosition + 300)
              and bearXPosition - 140 >= mummyXPosition
              and bearXPosition > mummyXPosition
              and bearYPosition + 50 > mummyYPosition
              and bearYPosition + 50 < mummyYPosition + 240):

            return True
        elif ((bearXPosition <= mummyXPosition + 300
               and bearXPosition >= mummyXPosition)
              and (bearYPosition + 50 <= mummyYPosition + 240
                   and bearYPosition + 50 >= mummyYPosition)):

            return True


class Background():
    def __init__(self, surface):
        self.bgimage = pygame.image.load('Game/Images/background1.png')
        self.bgimage = pygame.transform.scale(self.bgimage, (900, 700))
        self.floor = pygame.image.load('Game/Images/wood.png')
        self.floor = pygame.transform.scale(self.floor, (900, 200))
        self.roof = pygame.image.load('Game/Images/cobstone.png')
        self.roof = pygame.transform.scale(self.roof, (900, 20))
        self.water = pygame.image.load('Game/Images/water.png')
        self.water = pygame.transform.scale(self.water, (900, 100))
        self.blackBackground = pygame.image.load('Game/Images/black.png')
        self.blackBackground = pygame.transform.scale(self.blackBackground,
                                                      (700, 700))
        self.rectBGimg = self.bgimage.get_rect()
        self.bgY1 = 0
        self.bgX1 = 0
        self.bgY2 = 0
        self.bgX2 = self.rectBGimg.width
        self.surface = surface
        self.moving_speed = 10
        self.totalX = 0
        self.stopBackground = False
        self.isBlackBackground = False
        self.bgwX1 = 0
        self.bgwX2 = 0

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
        if self.getStopBackground() == False and self.getBlackBackground(
        ) == False:
            if characterPosition >= 290:
                self.totalX = self.totalX + 30
                self.bgX1 -= self.moving_speed
                self.bgX2 -= self.moving_speed

                if self.bgX1 <= -self.rectBGimg.width:
                    self.bgX1 = self.rectBGimg.width + 15
                if self.bgX2 <= -self.rectBGimg.width:
                    self.bgX2 = self.rectBGimg.width + 15

        # a2
            elif characterPosition <= 180:
                self.totalX = self.totalX - 30
                self.bgX1 += self.moving_speed
                self.bgX2 += self.moving_speed

                if self.bgX1 >= self.rectBGimg.width:
                    self.bgX1 = -self.rectBGimg.width
                if self.bgX2 >= self.rectBGimg.width:
                    self.bgX2 = -self.rectBGimg.width
        elif self.getBlackBackground() == True:
            self.bgimage = pygame.image.load('Game/Images/black.png')
            self.bgimage = pygame.transform.scale(self.bgimage, (900, 700))
            self.setBlackBackground(False)

        # elif self.getBlackBackground() == True:

        # self.surface.blit(self.pillar, (0, 0))
        # self.surface.blit(self.pillar, (20, 700))


class Mummy():
    def __init__(self, x, y, width, height, mummy1Image, mummy2Image, screen):
        self.mummy1 = mummy1Image
        self.mummy2 = mummy2Image
        self.mummy1 = pygame.transform.scale(self.mummy1, (width, height))
        self.mummy2 = pygame.transform.scale(self.mummy2, (width, height))
        self.direction = -1 * random.randint(1, 2)
        self.x = x
        self.y = y
        self.destructionAnimation = 0
        self.stunned = 0
        self.screen = screen
        self.rand = random.randint(2, 5)
        randomMax = random.randint(60, 90)
        self.changeDirection = random.randint(30, randomMax)
        self.hurtMummy = pygame.image.load("Game/Images/Mummy/hurtMummy.png")

        self.storeDirection = 1
        # self.health = 16

        self.health = random.randint(6, 13)
        self.fire = pygame.image.load("Game/Images/fire.png")
        self.fire = pygame.transform.scale(self.fire, (60, 60))
        self.hurtMummy = pygame.transform.scale(self.hurtMummy,
                                                (width, height))

        self.hurtLeftMummy = pygame.transform.flip(self.hurtMummy, True, False)
        self.hurtLeftMummy = pygame.transform.scale(self.hurtLeftMummy,
                                                    (width + 100, height))
        self.damageAttack = 8
        self.hp = 100
        self.height = height
        self.hurtTimer = 0
        self.isMonsterHurtAnimation = 0
        self.damageReceived = 0
        self.exp = 10
        self.isHurtAnimationStarted = False

        if self.height > 100:
            self.damageAttack = 10
            self.exp = 20
            self.health = 20
            self.mummy1 = pygame.image.load("Game/Images/Mummy/mummy1Big.png")
            self.mummy1 = pygame.transform.scale(self.mummy1, (width, height))
            self.mummy2 = pygame.image.load("Game/Images/Mummy/mummy2Big.png")
            self.mummy2 = pygame.transform.scale(self.mummy2, (width, height))
        self.isHurtTimer = 0
        self.startDestructionAnimation = False

    def setStartDestructionAnimation(self, startDestructionAnimation):
        self.startDestructionAnimation = startDestructionAnimation

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

    def setIsHurtAnimationStarted(self, isHurtAnimationStarted):
        self.isHurtAnimationStarted = isHurtAnimationStarted

    def getIsHurtAnimationStarted(self):
        return self.isHurtAnimationStarted

    def getExp(self):
        return self.exp

    def setIsMonsterHurtAnimation(self, isMonsterHurtAnimation):
        self.isMonsterHurtAnimation = isMonsterHurtAnimation

    def getIsMonsterHurtAnimation(self):
        return self.isMonsterHurtAnimation

    def setHp(self, hp):
        self.hp = hp

    def getHp(self):
        return self.hp

    def setDamageAttack(self, damageAttack):
        self.damageAttack = damageAttack

    def getDamageAttack(self):
        return self.damageAttack

    def __del__(self):
        print("  ")

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
        if self.height > 100:
            return "bigMummy"
        else:
            return "mummy"

    def getDestructionAnimationCount(self):
        return self.destructionAnimation

    def drawDestruction(self, damage):
        self.destructionAnimation = self.destructionAnimation + 1
        self.displayDamageOnMonster(damage)
        xRandom = random.randint(-100, 0)
        yRandom = random.randint(-100, 0)
        if self.destructionAnimation < 30:
            if self.destructionAnimation % 2 == 0:
                x = self.x + xRandom
                y = self.y + yRandom
                self.screen.blit(self.fire, (x, y))

    def displayDamageOnMonster(self, damage):

        # System Font

        white = pygame.Color(255, 255, 255)
        black = pygame.Color(0, 0, 0)
        font = pygame.font.SysFont("Italic", 40)

        text = font.render(str(damage), True, black)
        x = self.getXPosition() + 60
        y = self.getYPosition() - 60
        self.screen.blit(text, (x - 2, y - 2))
        self.screen.blit(text, (x + 2, y - 2))
        self.screen.blit(text, (x + 2, y + 2))
        self.screen.blit(text, (x - 2, y + 2))
        text = font.render(str(damage), True, white)
        self.screen.blit(text, (x, y))

    def getDamageReceived(self):
        return self.damageReceived

    def setDamageReceived(self, damageReceived):
        self.damageReceived = damageReceived

    def drawMonster(self):

        if self.x % 90 < 40 and self.getStunned() == 0:
            self.screen.blit(self.mummy1, (self.x, self.y))
        elif self.getStunned() == 0:
            self.screen.blit(self.mummy2, (self.x, self.y))
        if self.getStunned() == 0:
            self.x = self.x + self.direction * self.rand

        elif self.getStunned() > 0 and self.direction > 0:
            self.setStunned(self.getStunned() + 1)
            self.displayDamageOnMonster(self.getDamageReceived())
            self.screen.blit(self.hurtMummy, (self.x, self.y))

            if self.getStunned() == 20:
                self.setStunned(0)
        elif self.getStunned() > 0 and self.direction < 0:
            self.setStunned(self.getStunned() + 1)
            self.screen.blit(self.hurtLeftMummy, (self.x, self.y))
            self.displayDamageOnMonster(self.getDamageReceived())
            if self.getStunned() == 20:
                self.setStunned(0)

        if self.x % self.changeDirection == 0 and self.getStunned() == 0:
            self.direction = self.direction * (-1)
            self.mummy1 = pygame.transform.flip(self.mummy1, True, False)
            self.mummy2 = pygame.transform.flip(self.mummy2, True, False)


class Witch():
    def __init__(self, x, y, witch1Image, witch2Image, screen):
        self.witch = witch1Image
        self.witch2 = witch2Image
        self.witch = pygame.transform.scale(self.witch, (100, 100))
        self.witch2 = pygame.transform.scale(self.witch2, (100, 100))
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
        self.hurtTimer = 0
        self.isMonsterHurtAnimation = 0
        self.damageReceived = 0
        self.exp = 12
        self.isHurtAnimationStarted = False
        self.isHurtTimer = 0
        self.startDestructionAnimation = False

    def setStartDestructionAnimation(self, startDestructionAnimation):
        self.startDestructionAnimation = startDestructionAnimation

    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer

    def getHurtTimer(self):
        return self.isHurtTimer

    def setIsHurtAnimationStarted(self, isHurtAnimationStarted):
        self.isHurtAnimationStarted = isHurtAnimationStarted

    def getIsHurtAnimationStarted(self):
        return self.isHurtAnimationStarted

    def getExp(self):
        return self.exp

    def setIsMonsterHurtAnimation(self, isMonsterHurtAnimation):
        self.isMonsterHurtAnimation = isMonsterHurtAnimation

    def getIsMonsterHurtAnimation(self):
        return self.isMonsterHurtAnimation

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

    def __del__(self):
        print(" ")

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

    def setThrowsFireBalls(self, setFireBall):
        self.setThrowsFireBall = setFireBall

    def getThrowsFireBalls(self):
        return self.setThrowsFireBall

    def drawDestruction(self, damage):
        self.destructionAnimation = self.destructionAnimation + 1
        self.displayDamageOnMonster(damage)
        xRandom = random.randint(-100, 0)
        yRandom = random.randint(-100, 0)
        if self.destructionAnimation < 30:
            if self.destructionAnimation % 2 < 10:
                x = self.x + xRandom
                y = self.y + yRandom
                self.screen.blit(self.fire, (x, y))

    def displayDamageOnMonster(self, damage):

        # System Font

        white = pygame.Color(255, 255, 255)
        black = pygame.Color(0, 0, 0)
        font = pygame.font.SysFont("Italic", 40)

        text = font.render(str(damage), True, black)
        x = self.getXPosition() + 60
        y = self.getYPosition() - 60
        self.screen.blit(text, (x - 2, y - 2))
        self.screen.blit(text, (x + 2, y - 2))
        self.screen.blit(text, (x + 2, y + 2))
        self.screen.blit(text, (x - 2, y + 2))
        text = font.render(str(damage), True, white)
        self.screen.blit(text, (x, y))

    def getDamageReceived(self):
        return self.damageReceived

    def setDamageReceived(self, damageReceived):
        self.damageReceived = damageReceived

    def drawMonster(self):

        if self.getStunned() == 0:
            if self.getThrowsFireBalls() == False:
                self.screen.blit(self.witch, (self.x, self.y))
            else:
                self.fireBallAnimationCounter = self.fireBallAnimationCounter + 1
                self.screen.blit(self.witch2, (self.x, self.y))
        if self.fireBallAnimationCounter > 50:

            self.fireBallAnimationCounter = 0
            self.setThrowsFireBalls(False)
        if self.getStunned() == 0:
            self.x = self.x + self.directionX * self.rand
            self.y = self.y + self.directionY * self.rand

        elif self.getStunned() > 0 and self.directionX > 0:
            self.setStunned(self.getStunned() + 1)
            self.screen.blit(self.hurtWitch, (self.x, self.y))
            self.displayDamageOnMonster(self.getDamageReceived())
            if self.getStunned() == 20:
                self.setStunned(0)
        elif self.getStunned() > 0 and self.directionX < 0:
            self.setStunned(self.getStunned() + 1)
            self.screen.blit(self.hurtWitch, (self.x, self.y))
            self.displayDamageOnMonster(self.getDamageReceived())
            if self.getStunned() == 20:
                self.setStunned(0)

        if self.x % self.changeDirectionX == 0 and self.getStunned() == 0:
            self.directionX = self.directionX * (-1)
            if self.getThrowsFireBalls() == False:
                self.witch = pygame.transform.flip(self.witch, True, False)
            else:
                self.fireBallAnimationCounter = self.fireBallAnimationCounter + 1
                self.witch2 = pygame.transform.flip(self.witch2, True, False)

        if self.y % self.changeDirectionY == 0 and self.getStunned() == 0:
            self.directionY = self.directionY * (-1)
            if self.getThrowsFireBalls() == False:
                self.witch = pygame.transform.flip(self.witch, True, False)
            else:
                self.witch2 = pygame.transform.flip(self.witch2, True, False)


class FireBall():
    def __init__(self, x, y, vel_x, vel_y, fireballImage, screen):
        self.x = x
        self.y = y
        self.vel_x = vel_x
        self.vel_y = -1 * vel_y
        self.screen = screen
        self.fireBall = fireballImage
        self.stunned = False
        self.health = 1
        self.damageAttack = 5
        self.isHurtTimer = 0

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer

    def getHurtTimer(self):
        return self.isHurtTimer

    def setDamageAttack(self, damageAttack):
        self.damageAttack = damageAttack

    def getDamageAttack(self):
        return self.damageAttack

    def __del__(self):
        print("  ")

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
        return self.health

    def getHealth(self):
        return self.health

    def drawFireBall(self):
        # if self.x < 0 or self.x > 900:
        #     self.vel_x *= -1
        if self.y < 370:
            self.y -= self.vel_y
            self.x += self.vel_x
        else:
            self.vel_y *= -1
            self.y -= self.vel_y

        self.fire = pygame.transform.scale(self.fireBall, (60, 60))
        self.fire = self.screen.blit(self.fire, (self.x, self.y))

    def drawDestruction(self):
        self.destructionAnimation = self.destructionAnimation + 1


class GreenBlob():
    def __init__(self, x, y, height, width, screen):
        self.height = height
        self.width = width
        self.greenBlob = pygame.image.load("Game/Images/greenBlob.png")
        self.greenBlob = pygame.transform.scale(self.greenBlob,
                                                (self.width, self.height))

        self.comingUp = False
        self.direction = -1 * random.randint(1, 2)
        self.x = x
        self.y = y
        self.health = 22
        self.destructionAnimation = 0
        self.stunned = 0
        self.screen = screen
        self.rand = random.randint(2, 5)
        randomMax = random.randint(30, 80)
        self.changeDirection = random.randint(30, randomMax)
        self.jump = False
        self.comingDown = False
        self.nextJumpTimer = random.randint(20, 90)
        self.timer = 0
        self.hurtGreenBlob = pygame.image.load("Game/Images/greenBlob2.png")
        self.hurtGreenBlob = pygame.transform.scale(self.hurtGreenBlob,
                                                    (100, 100))
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

    def setStartDestructionAnimation(self, startDestructionAnimation):
        self.startDestructionAnimation = startDestructionAnimation

    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer

    def getHurtTimer(self):
        return self.isHurtTimer

    def setIsHurtAnimationStarted(self, isHurtAnimationStarted):
        self.isHurtAnimationStarted = isHurtAnimationStarted

    def getIsHurtAnimationStarted(self):
        return self.isHurtAnimationStarted

    def getExp(self):
        return self.exp

    def getDamageReceived(self):
        return self.damageReceived

    def setDamageReceived(self, damageReceived):
        self.damageReceived = damageReceived

    def setIsMonsterHurtAnimation(self, isMonsterHurtAnimation):
        self.isMonsterHurtAnimation = isMonsterHurtAnimation

    def getIsMonsterHurtAnimation(self):
        return self.isMonsterHurtAnimation

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

    def __del__(self):
        print(" ")

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
        if self.height >= 200:
            return "bigGreenBlob"
        else:
            return "greenBlob"

    def getDestructionAnimationCount(self):
        return self.destructionAnimation

    def drawDestruction(self, damage):
        self.destructionAnimation = self.destructionAnimation + 1
        self.displayDamageOnMonster(damage)
        xRandom = random.randint(-100, 0)
        yRandom = random.randint(-100, 0)
        if self.destructionAnimation < 30:
            if self.destructionAnimation % 2 == 0:
                x = self.x + xRandom
                y = self.y + yRandom
                self.screen.blit(self.fire, (x, y))

    def displayDamageOnMonster(self, damage):

        # System Font

        white = pygame.Color(255, 255, 255)
        black = pygame.Color(0, 0, 0)
        font = pygame.font.SysFont("Italic", 40)

        text = font.render(str(damage), True, black)
        x = self.getXPosition() + 60
        y = self.getYPosition() - 60
        self.screen.blit(text, (x - 2, y - 2))
        self.screen.blit(text, (x + 2, y - 2))
        self.screen.blit(text, (x + 2, y + 2))
        self.screen.blit(text, (x - 2, y + 2))
        text = font.render(str(damage), True, white)
        self.screen.blit(text, (x, y))

    def drawMonster(self):

        self.timer = self.timer + 1
        if self.jump == True:
            if self.y + self.height <= 80 and self.comingDown == False:
                self.comingDown = True
                self.y = self.y + 15

            elif self.comingDown == False:
                self.y = self.y - 15

            elif self.y + self.height < 400 and self.comingDown == True:
                self.y = self.y + 15

            elif self.y + self.height >= 400 and self.comingDown == True:
                self.jump = False
                self.timer = 0
                self.comingDown = False
                self.nextJump = random.randint(30, 80)

        if self.timer == self.nextJumpTimer:
            self.jump = True

        if self.getStunned() == 0:
            self.screen.blit(self.greenBlob, (self.x, self.y))
        if self.getStunned() == 0:
            self.x = self.x + self.direction * self.rand

        elif self.getStunned() > 0 and self.direction > 0:
            self.setStunned(self.getStunned() + 1)
            self.displayDamageOnMonster(self.getDamageReceived())
            self.screen.blit(self.hurtGreenBlob, (self.x, self.y))
            if self.getStunned() == 20:
                self.setStunned(0)
        elif self.getStunned() > 0 and self.direction < 0:
            self.setStunned(self.getStunned() + 1)
            self.screen.blit(self.hurtGreenBlob, (self.x, self.y))
            self.displayDamageOnMonster(self.getDamageReceived())
            if self.getStunned() == 20:
                self.setStunned(0)

        if self.x % self.changeDirection == 0 and self.getStunned() == 0:
            self.direction = self.direction * (-1)
            self.greenBlob = pygame.transform.flip(self.greenBlob, True, False)


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
        self.talking = pygame.image.load("Game/Images/Talking.png")
        self.talking = pygame.transform.scale(self.talking, (900, 250))
        self.talking2 = pygame.image.load("Game/Images/Talking2.png")
        self.talking2 = pygame.transform.scale(self.talking2, (900, 250))
        self.bearJumping1 = pygame.image.load("Game/Images/Bear/bearJump1.png")
        self.bearJumping1 = pygame.transform.scale(self.bearJumping1,
                                                   (100, 100))
        self.endText = False
        self.maxHp = 100
        self.attack = 10
        self.hp = 100
        self.maxExp = 12
        self.exp = 0

        self.text1 = ""
        self.text2 = ""
        self.text3 = ""

        self.textArray = [[
            'To jump press "z"  ', 'To attack press "a"      ',
            '   Press "s" to continue  '
        ],
                          [
                              ' Press "ESC" to end game   ',
                              ' Defeat frankenbear at end of castle !!    ',
                              '  Press "s" to continue   '
                          ]]
        self.tupleIndex = 0
        self.bearJumping2 = pygame.image.load("Game/Images/Bear/bearJump2.png")
        self.bearJumping2 = pygame.transform.scale(self.bearJumping2,
                                                   (100, 100))
        self.bearJumpingLeft1 = pygame.image.load(
            "Game/Images/Bear/bearJump1.png")

        self.bearJumpingLeft1 = pygame.transform.flip(self.bearJumpingLeft1,
                                                      True, False)
        self.bearJumpingLeft1 = pygame.transform.scale(self.bearJumpingLeft1,
                                                       (100, 100))

        self.bearJumpingLeft2 = pygame.image.load(
            "Game/Images/Bear/bearJump2.png")
        self.bearJumpingLeft2 = pygame.transform.flip(self.bearJumpingLeft2,
                                                      True, False)
        self.bearJumpingLeft2 = pygame.transform.scale(self.bearJumpingLeft2,
                                                       (100, 100))
        self.damageAttack = 2
        self.hp = 100
        self.hurtTimer = 0

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
        self.leftJump = leftJump

    def getLeftJumpStatus(self):
        return self.leftJump

    def setLeftDirection(self, direction):
        self.leftDirection = direction

    def getLeftDirection(self):
        return self.leftDirection

    def setComingUpStatus(self, comingUp):
        self.comingUp = comingUp

    def getComingUp(self):
        return self.comingUp

    def setHealth(self, health):
        self.health = health

    def getHealth(self):
        return self.hp

    def setLevel(self, level):
        self.level = level

    def getLevel(self):
        return self.level

    def jump(self, blocks):
        for block in blocks:
            block.setOnPlatform(False)
        if self.getLeftDirection() == False:
            self.screen.blit(self.bearJumping1, (self.getXPosition(), self.y))
        else:
            self.screen.blit(self.bearJumpingLeft1,
                             (self.getXPosition(), self.y))
        if self.y >= (self.initialHeight - 200) and self.comingUp == True:

            self.y = self.y - 15

        elif self.y >= (self.initialHeight - 230):

            self.comingUp = False
            self.y = self.y + 15

            for block in blocks:
                block.isBoundaryPresent(self.getXPosition(), self.y)
                if block.getOnPlatform() == True:
                    self.setJumpStatus(False)
                    self.setLeftJumpStatus(False)

                    self.initialHeight = self.y
        if self.y + 100 == 400:
            self.setJumpStatus(False)
            self.setLeftJumpStatus(False)

    def leftJump(self, blocks):
        for block in self.blocks:
            block.setOnPlatform(False)
        if self.y <= self.initialHeight and self.y >= (
                self.initialHeight - 200) and self.getComingUp() == True:
            self.y = self.y - 15
            self.screen.blit(self.bearJumpingLeft1,
                             (self.getXPosition(), self.y))
        elif self.y >= (self.initialHeight -
                        230) and self.y < self.initialHeight:
            self.y = self.y + 15

            self.setComingUpStatus(False)

            for block in self.blocks:
                block.isBoundaryPresent(self.getXPosition(), self.y)
                if block.getOnPlatform() == True:
                    self.setJumpStatus(False)
                    self.setLeftJumpStatus(False)

                    self.initialHeight = self.y
        if self.getLeftDirection() == False:
            self.screen.blit(self.bearJumping2,
                             (self.getXPosition(), self.getYPosition()))
        else:
            self.screen.blit(self.bearJumpingLeft2,
                             (self.getXPosition(), self.getYPosition()))
        if self.getYPosition() + 100 == 400:
            self.setJumpStatus(False)
            self.setLeftJumpStatus(False)

    def isBearHurt(self, positionRelative, bearXPosition, bearYPosition,
                   objectXPosition, objectYPosition, object):
        width = 0
        height = 0

        if object == "mummy":
            width = 100
            height = 100
        elif object == "bigMummy":
            width = 100
            height = 300
        elif object == "fireBall":
            width = 110
            height = 110
        elif object == "witch":
            width = 100
            height = 180
        elif object == "greenBlob":
            width = 100
            height = 120
        elif object == "bigGreenBlob":
            width = 300
            height = 400
        elif object == "spikes":
            width = 600
            height = 60
        elif object == "frankenbears":
            width = 300
            height = 300
        else:
            return False

        if ((bearXPosition + 70 >= objectXPosition
             and bearXPosition + 70 <= objectXPosition + width)
                and (bearYPosition + 100 <= objectYPosition + height
                     and bearYPosition + 100 >= objectYPosition)):
            return True
        if ((bearXPosition >= objectXPosition
             and bearXPosition <= objectXPosition + width)
                and (bearYPosition + 100 <= objectYPosition + height
                     and bearYPosition + 100 >= objectYPosition)):

            return True
        if ((bearXPosition <= objectXPosition + width
             and bearXPosition >= objectXPosition)
                and (bearYPosition + 100 <= objectYPosition + height
                     and bearYPosition + 100 >= objectYPosition)):

            return True

        elif (bearYPosition + 100 >= objectYPosition + height - 70
              and bearXPosition >= objectXPosition + width
              and bearXPosition <= objectXPosition + width - 10):

            return True
        else:
            return False

    def boundaryExtraCheck(self):
        floorHeight = 400
        if self.getXPosition() <= 30:
            self.setXPosition(self.getXPosition() + 30)

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

        # System Font
        white = pygame.Color(255, 255, 255)
        black = pygame.Color(0, 0, 0)
        font = pygame.font.SysFont("Italic", 40)

        text = font.render(str(damage), True, black)
        x = self.getXPosition() + 60
        y = self.getYPosition() - 60
        self.screen.blit(text, (x - 2, y - 2))
        self.screen.blit(text, (x + 2, y - 2))
        self.screen.blit(text, (x + 2, y + 2))
        self.screen.blit(text, (x - 2, y + 2))
        text = font.render(str(damage), True, white)
        self.screen.blit(text, (x, y))

    def displayBearHp(self):

        # System Font
        pygame.draw.rect(self.screen, (0, 0, 0), pygame.Rect(10, 10, 300, 40))
        font = pygame.font.SysFont("Italic", 40)
        hp = "Health : " + str(self.getHp()) + "/" + str(self.getMaxHp())
        text = font.render(hp, False, (255, 255, 255))
        self.screen.blit(text, (20, 20))

    def displayBearExp(self):

        # System Font
        self.levelUpCheck()
        font = pygame.font.SysFont("Italic", 40)
        pygame.draw.rect(self.screen, (0, 0, 0), pygame.Rect(600, 10, 200, 40))
        text = font.render(
            'Exp: ' + str(self.getCurrentExp()) + "/" + str(self.getMaxExp()),
            False, (255, 255, 255))
        pygame.draw.rect(self.screen, (0, 0, 0), pygame.Rect(400, 10, 200, 40))
        self.screen.blit(text, (400, 20))

        text2 = font.render('Power Level: ' + str(self.level), False,
                            (255, 255, 255))
        self.screen.blit(text2, (600, 20))

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
        if self.getEndText() == False:
            if self.line != len(self.textArray[self.tupleIndex]) and len(
                    self.textArray[self.tupleIndex][
                        self.line]) == self.indexArray + 1:
                self.indexArray = 0

                self.line = self.line + 1
                if self.line == 1:

                    self.text2 = self.textArray[self.tupleIndex][self.line]

                elif self.line == 2:
                    self.line = 2

                    self.text3 = self.textArray[self.tupleIndex][self.line]

            elif self.line == 0:
                self.text1 = self.textArray[self.tupleIndex][0]

            self.blinkTimer = self.blinkTimer + 1
            # System Font
            if self.blinkTimer < self.randomBlink:

                self.screen.blit(self.talking, (0, 0))
            elif self.blinkTimer >= self.randomBlink and self.blinkTimer <= self.randomBlink + 10:
                self.screen.blit(self.talking2, (0, 0))
            else:
                self.screen.blit(self.talking2, (0, 0))
                self.randomBlink = random.randint(100, 250)
                self.blinkTimer = 0
            self.textTimer = self.textTimer + 1
            font = pygame.font.SysFont("Italic", 40)
            text1 = font.render(self.totalText1, False, (0, 0, 0))
            self.screen.blit(text1, (380, 60))
            text2 = font.render(self.totalText2, False, (0, 0, 0))
            self.screen.blit(text2, (380, 80 + self.textHeight))
            text3 = font.render(self.totalText3, False, (0, 0, 0))
            self.screen.blit(text3, (380, 110 + self.textHeight))
            self.xText = self.xText + 5
            if self.textTimer % 3 < 2:

                if self.line == 0:
                    self.totalText1 = self.totalText1 + self.text1[
                        self.indexArray]
                elif self.line == 1:
                    self.totalText2 = self.totalText2 + self.text2[
                        self.indexArray]
                elif self.line == 2:
                    self.totalText3 = self.totalText3 + self.text3[
                        self.indexArray]

                self.indexArray = self.indexArray + 1

                for ev in pygame.event.get():
                    if ev.type == pygame.KEYDOWN:
                        if ev.key == pygame.K_s:
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
                                self.tupleIndex = self.tupleIndex + 1
                                self.totalText1 = ""
                                self.totalText2 = ""
                                self.totalText3 = ""
                                self.line = 0
                                self.indexArray = 0

    def levelUpCheck(self):
        if self.maxExp <= self.exp:

            self.setEndText(False)

            self.level = self.level + 1
            self.maxExp = self.maxExp + 20
            self.exp = 0
            self.maxHp = self.maxHp + random.randint(5, 15)
            self.hp = self.maxHp
            self.attack = self.attack + random.randint(2, 5)
            self.damageAttack = self.damageAttack + random.randint(2, 5)
            self.textArray = []
            self.textArray.append(
                ['    LEVEL UP !  ', '   ', '   press "s" to continue  '])
            self.textArray.append([
                ' maxHP is now :' + str(self.maxHp) + ' ',
                ' attack is now : ' + str(self.damageAttack) + ' ',
                '    "press "s" to continue  '
            ])
            self.line = 0
            self.tupleIndex = 0
            self.indexArray = 0
            print(self.textArray)


class HealthPowerItem():
    def __init__(self, x, y, width, height, screen):

        self.damageAttack = 2
        self.hp = 100

    def setIsMonsterHurtAnimation(self, isMonsterHurtAnimation):
        self.isMonsterHurtAnimation = isMonsterHurtAnimation


class Door:
    def __init__(self, screen, xPosition):
        self.screen = screen
        self.x = xPosition
        # self.doorImage = doorImage
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

    def isKeyGrabbed(self, bearXPosition, bearYPosition, objectXPosition,
                     objectYPosition):
        width = 60
        height = 100

        if ((bearXPosition + 70 >= objectXPosition
             and bearXPosition + 70 <= objectXPosition + width)
                and (bearYPosition + 100 <= objectYPosition + height
                     and bearYPosition + 100 >= objectYPosition)):
            self.isOpen = True
            return True
        if ((bearXPosition >= objectXPosition
             and bearXPosition <= objectXPosition + width)
                and (bearYPosition + 100 <= objectYPosition + height
                     and bearYPosition + 100 >= objectYPosition)):
            self.isOpen = True
            return True
        if ((bearXPosition <= objectXPosition + width
             and bearXPosition >= objectXPosition)
                and (bearYPosition + 100 <= objectYPosition + height
                     and bearYPosition + 100 >= objectYPosition)):
            self.isOpen = True
            return True

        elif (bearYPosition + 100 >= objectYPosition + height - 70
              and bearXPosition >= objectXPosition + width
              and bearXPosition <= objectXPosition + width - 10):
            self.isOpen = True
            return True
        else:
            return False

    def boundaryExtraCheck(self):
        floorHeight = 400
        if self.getYPosition() + 120 <= floorHeight:
            self.setYPosition(self.getYPosition() + 30)


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

    def setIsHurtAnimationStarted(self, isHurtAnimationStarted):
        self.isHurtAnimationStarted = isHurtAnimationStarted

    def getIsHurtAnimationStarted(self):
        return self.isHurtAnimationStarted

    def setDamageAttack(self, damageAttack):
        self.damageAttack = damageAttack

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
        return self.health

    def getHealth(self):
        return self.health

    def draw(self):
        self.screen.blit(self.spike, (self.x, self.y))
        self.screen.blit(self.spike, (self.x + 100, self.y))
        self.screen.blit(self.spike, (self.x + 200, self.y))
        self.screen.blit(self.spike, (self.x + 300, self.y))
        self.screen.blit(self.spike, (self.x + 400, self.y))
        self.screen.blit(self.spike, (self.x + 500, self.y))

    def drawDestruction(self):
        self.destructionAnimation = self.destructionAnimation + 1


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

    def setDamageReceived(self, damageReceived):
        self.damageReceived = damageReceived

    def setThrowFireBallLeft(self, throwFireBallLeft):
        self.throwFireBallLeft = throwFireBallLeft

    def getThrowFireBallLeft(self):
        return self.throwFireBallLeft

    def setThrowFireBallRight(self, throwFireBallRight):
        self.throwFireBallRight = throwFireBallRight

    def getThrowFireBallRight(self):
        return self.throwFireBallRight

    def setHurtTimer(self, timer):
        self.isHurtTimer = timer

    def getHurtTimer(self):
        return self.isHurtTimer

    def setIsHurtAnimationStarted(self, isHurtAnimationStarted):
        self.isHurtAnimationStarted = isHurtAnimationStarted

    def getIsHurtAnimationStarted(self):
        return self.isHurtAnimationStarted

    def setDamageAttack(self, damageAttack):
        self.damageAttack = damageAttack

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

        # System Font

        white = pygame.Color(255, 255, 255)
        black = pygame.Color(0, 0, 0)
        font = pygame.font.SysFont("Italic", 60)

        text = font.render(str(damage), True, black)
        x = 450
        y = 130
        self.screen.blit(text, (x - 2, y - 2))
        self.screen.blit(text, (x + 2, y - 2))
        self.screen.blit(text, (x + 2, y + 2))
        self.screen.blit(text, (x - 2, y + 2))
        text = font.render(str(damage), True, white)
        self.screen.blit(text, (x, y))

    def drawMonster(self):
        self.blinkTimer = self.blinkTimer + 1
        self.attackTimer = self.attackTimer + 1

        # System Font
        if self.blinkTimer < self.randomBlink and self.attackTimer < self.randomAttack:

            self.screen.blit(self.boss1, (300, 40))
        elif self.blinkTimer >= self.randomBlink and self.blinkTimer <= self.randomBlink + 10 and self.attacked == False:
            self.screen.blit(self.boss2, (300, 40))
            self.bossDisplay = self.boss2
            self.blinked = True
        elif self.attackTimer >= self.randomAttack and self.attackTimer <= self.randomAttack + 30:
            self.screen.blit(self.bossDisplay, (300, 40))
            self.attacked = True

        else:
            if self.blinked == True:
                self.randomBlink = random.randint(50, 150)
                self.blinked = False
                self.blinkTimer = 0
            if self.attacked == True:
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
            self.screen.blit(self.boss1, (300, 40))

        if self.getStunned() > 0:
            self.setStunned(self.getStunned() + 1)
            self.displayDamageOnMonster(self.getDamageReceived())
            # self.screen.blit(self.hurtGreenBlob, (self.x, self.y))
            if self.getStunned() == 20:
                self.setStunned(0)

    def setStartDestructionAnimation(self, startDestructionAnimation):
        self.startDestructionAnimation = startDestructionAnimation

    def getStartDestructionAnimationStatus(self):
        return self.startDestructionAnimation

    def drawDestruction(self, damage):
        self.displayDamageOnMonster(damage)
        self.destructionAnimation = self.destructionAnimation + 1

        xRandom = random.randint(-300, 0)
        yRandom = random.randint(-300, 0)
        if self.destructionAnimation < 30:
            if self.destructionAnimation % 2 < 10:
                x = self.x + xRandom
                y = self.y + yRandom
                self.screen.blit(self.fire, (x, y))

    def getDestructionAnimationCount(self):
        return self.destructionAnimation

    def getExp(self):
        return self.exp
