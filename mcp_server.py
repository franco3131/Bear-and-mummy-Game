from mcp.server.fastmcp import FastMCP
import json
from pathlib import Path

mcp = FastMCP("pygame-helper")

PROJECT_ROOT = Path(__file__).parent


@mcp.tool()
def list_game_files() -> str:
    """List important game files in the project."""
    files = []
    for path in PROJECT_ROOT.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".json", ".txt"}:
            files.append(str(path.relative_to(PROJECT_ROOT)))
    return json.dumps(files, indent=2)


@mcp.tool()
def read_main_game_file() -> str:
    """Read the main.py file."""
    main_file = PROJECT_ROOT / "main.py"
    if not main_file.exists():
        return "main.py not found"
    return main_file.read_text(encoding="utf-8")


@mcp.tool()
def explain_game_loop() -> str:
    """Give a high-level explanation of a standard Pygame loop."""
    return (
        "A basic Pygame loop usually initializes pygame, creates the screen, "
        "processes events, updates game state, renders the frame, and caps FPS."
    )


if __name__ == "__main__":
    mcp.run()