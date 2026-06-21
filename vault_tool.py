"""Append-only writes to the knowledge base, enforced in code.

The bot never gets the general Write/Edit/Bash tools. This is the *only* way it can write,
and it can only:
  - APPEND (never edit or delete existing content)
  - to .md notes in the folders you allow (ROBOMANAGER_WRITE_ALLOW)
  - never your private folders (ROBOMANAGER_PRIVATE_DIRS), dotfolders, or the root
Every append is wrapped in a timestamped `> [!robomanager]` callout so it's obvious and reversible.
"""
import datetime
from pathlib import Path
from claude_agent_sdk import tool, create_sdk_mcp_server
import config

ROOT = Path(config.KNOWLEDGE_PATH).resolve() if config.KNOWLEDGE_PATH else None
ALLOWED_TOP = set(config.WRITE_ALLOW)
DENY_TOP = set(config.PRIVATE_DIRS)


def _validate(rel: str) -> Path:
    if ROOT is None:
        raise ValueError("ROBOMANAGER_KNOWLEDGE_PATH is not set")
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("path must be relative to the knowledge base and contain no '..'")
    target = (ROOT / p).resolve()
    if target != ROOT and ROOT not in target.parents:
        raise ValueError("path escapes the knowledge base")
    if target.suffix.lower() != ".md":
        raise ValueError("only .md notes can be appended to")
    parts = target.relative_to(ROOT).parts
    if not parts:
        raise ValueError("cannot write to the root")
    top = parts[0]
    if top.startswith(".") or top in DENY_TOP:
        raise ValueError(f"'{top}' is off-limits (private / hidden)")
    if top not in ALLOWED_TOP:
        raise ValueError(f"'{top}' is not in ROBOMANAGER_WRITE_ALLOW")
    return target


@tool(
    "vault_append",
    "Append text to an EXISTING Markdown note in the knowledge base. APPEND-ONLY — it never edits "
    "or deletes existing content. Args: 'path' (relative to the knowledge base root, e.g. "
    "'Logs/2026-06-21.md') and 'text'.",
    {"path": str, "text": str},
)
async def vault_append(args):
    try:
        target = _validate(args["path"])
    except ValueError as e:
        return {"content": [{"type": "text", "text": f"Refused: {e}"}], "is_error": True}
    if not target.exists():
        return {"content": [{"type": "text", "text":
            f"Refused: {args['path']} doesn't exist (append-only to existing notes)."}], "is_error": True}
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    body = "\n".join("> " + line for line in args["text"].splitlines())
    with open(target, "a", encoding="utf-8") as f:
        f.write(f"\n\n> [!robomanager] appended {stamp}\n{body}\n")
    return {"content": [{"type": "text", "text": f"Appended to {target.relative_to(ROOT)}."}]}


vault_server = create_sdk_mcp_server(name="vault", version="1.0.0", tools=[vault_append])
