"""RoboManager brain: a Claude Agent SDK agent that reads a Markdown knowledge base,
appends to it (within guardrails), and optionally drives ClickUp.
"""
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, SystemMessage
import config
from vault_tool import vault_server

_private = ", ".join(config.PRIVATE_DIRS) or "(none configured)"

SYSTEM_PROMPT = f"""You are RoboManager — {config.PERSONA}, talking to the user in Slack.

Your job: remove "what do I even do right now" paralysis. Decide the single highest-leverage next
action, one step at a time. Warm, direct, decisive. Keep replies short and Slack-friendly.

YOUR KNOWLEDGE BASE: a folder of Markdown notes at the working directory. Read what's relevant
(priorities, logs, projects) to ground your advice.

RULES:
- PRIVACY WALL: never read or reference these private folders: {_private}. Don't surface their contents.
- WRITES ARE LIMITED: you may READ the knowledge base and APPEND to notes via the `vault_append`
  tool — append-only; you can NEVER edit or delete existing content. Never run git commit/push.
- Act on optional integrations (e.g. ClickUp) only when the user clearly asks.
- Decide ONE clear next action + why, then stop. Don't dump the whole backlog.
"""


def _options(resume=None) -> ClaudeAgentOptions:
    mcp = {"vault": vault_server}
    allowed = ["Read", "Glob", "Grep", "mcp__vault__*"]
    if config.CLICKUP_API_KEY:
        mcp["clickup"] = {
            "command": "npx",
            "args": ["-y", "@taazkareem/clickup-mcp-server"],
            "env": {"CLICKUP_API_KEY": config.CLICKUP_API_KEY, "CLICKUP_TEAM_ID": config.CLICKUP_TEAM_ID},
        }
        allowed.append("mcp__clickup__*")
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=config.MODEL,
        cwd=config.KNOWLEDGE_PATH,
        allowed_tools=allowed,
        disallowed_tools=["Write", "Edit", "Bash", "WebSearch", "WebFetch"],
        mcp_servers=mcp,
        permission_mode="bypassPermissions",  # bounded: only the tools above are available
        setting_sources=[],
        resume=resume,
    )


async def run_agent(prompt: str, resume: str | None = None) -> tuple[str, str | None]:
    """Run one turn. Returns (reply_text, session_id) so callers can resume the conversation."""
    reply, session_id = "", resume
    async for message in query(prompt=prompt, options=_options(resume)):
        if isinstance(message, SystemMessage) and getattr(message, "subtype", None) == "init":
            session_id = message.data.get("session_id", session_id)
        elif isinstance(message, ResultMessage):
            reply = (message.result or reply)
    return (reply or "(no response — check the logs)", session_id)
