from Game.mainGame import mainGame

game = mainGame()
result = game.showStartMenu()
if result is not None:
    game.runGame()
