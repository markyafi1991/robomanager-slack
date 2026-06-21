"""RoboManager config — all secrets and paths come from the environment.

Copy .env.example to ~/.config/robomanager/env and fill it in.
Nothing secret is ever committed to this repo.
"""
import os
from pathlib import Path


def _load_env_file(path: Path) -> None:
    """Load simple KEY=value lines into os.environ (existing env wins; blank values skipped)."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip()
        # Skip blanks so an empty ANTHROPIC_API_KEY= can't shadow the Claude Code login.
        if key and val and key not in os.environ:
            os.environ[key] = val


_load_env_file(Path.home() / ".config" / "robomanager" / "env")


def _csv(name: str) -> list[str]:
    return [x.strip() for x in os.environ.get(name, "").split(",") if x.strip()]


# --- Core ---
# A folder of Markdown notes the bot reads as its knowledge base (e.g. an Obsidian vault).
KNOWLEDGE_PATH = os.environ.get("ROBOMANAGER_KNOWLEDGE_PATH", "")

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")
# Optional: if unset, the Agent SDK falls back to your Claude Code login.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# --- Write guardrails (append-only) ---
# Top-level folders inside the knowledge base the bot may APPEND to. Empty = read-only.
WRITE_ALLOW = _csv("ROBOMANAGER_WRITE_ALLOW")
# Top-level folders the bot must NEVER read or write — your privacy wall.
PRIVATE_DIRS = _csv("ROBOMANAGER_PRIVATE_DIRS")

# --- Optional ClickUp integration ---
CLICKUP_API_KEY = os.environ.get("CLICKUP_API_KEY", "")
CLICKUP_TEAM_ID = os.environ.get("CLICKUP_TEAM_ID", "")

# --- Nudges & misc ---
NUDGE_CHANNEL = os.environ.get("ROBOMANAGER_CHANNEL", "")  # Slack channel ID; blank = nudges off
MODEL = os.environ.get("ROBOMANAGER_MODEL", "claude-sonnet-4-6")
TIMEZONE = os.environ.get("ROBOMANAGER_TZ", "America/Chicago")
PERSONA = os.environ.get("ROBOMANAGER_PERSONA", "a personal operations manager")


def require(*names: str) -> None:
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise SystemExit(
            "Missing required config: " + ", ".join(missing) +
            "\nSet them in ~/.config/robomanager/env — see .env.example."
        )
