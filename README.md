# RoboManager

**A Slack AI manager you can safely point at your real notes — because its permissions are enforced in code, not by a prompt.**

A two-way **Slack manager bot** powered by the **Claude Agent SDK**. Chat with it like a manager, and it nudges you proactively. It reads a folder of Markdown notes as its "knowledge base" (an Obsidian vault works great), so its advice is grounded in *your* actual priorities — not generic platitudes.

Built to kill the "what do I even do right now?" feeling: it decides the single highest-leverage next action, one step at a time.

```text
You  ▸  @RoboManager what should I work on today?
Bot  ▸  Your proposals are the priority and you've sent 0 this week.
        Start there: draft one for that role you saved. Want me to make a ClickUp task?
```

## What it does
- **Two-way chat** — DM it or @mention it in a channel; it answers as your manager.
- **Knowledge-grounded** — reads your Markdown notes (priorities, logs, projects) before answering.
- **Proactive nudges** — scheduled morning + end-of-day check-ins.
- **Optional ClickUp** — create/update tasks when you ask.
- **Runs locally** — Slack **Socket Mode**, so no public URL, no server, no inbound webhooks.

## The interesting part: guardrails as code
The bot has access to your notes — so the safety model matters. Permissions are enforced by **what tools exist**, not by asking the model to behave:

- **Read-only by default.** The general `Write` / `Edit` / `Bash` tools are disabled.
- **Append-only writes.** The *only* write path is a custom `vault_append` tool that can append to notes but **can never edit or delete** existing content — and only in folders you allow (`ROBOMANAGER_WRITE_ALLOW`).
- **A privacy wall.** Folders you list in `ROBOMANAGER_PRIVATE_DIRS` are off-limits — the bot won't read or write them.
- **No auto-commit.** It writes local files; you review and commit.

So you can point it at a vault that mixes work and private notes, and it's *physically* unable to leak or destroy the parts you fence off.

## Architecture
```text
Slack (Socket Mode)  ──►  bot.py (Bolt)  ──►  manager_agent.py (Claude Agent SDK)
                                                 ├─ Read / Glob / Grep   (your notes, read-only)
                                                 ├─ vault_append          (append-only, guarded)
                                                 └─ ClickUp MCP           (optional)
APScheduler  ──►  proactive nudges
```
Default model: **Claude Sonnet** (configurable). Auth uses your **Claude Code login** if no API key is set, or the Anthropic API if you provide one.

## Setup
Requires Python 3.10+ and the [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (the Agent SDK uses it).

```bash
git clone https://github.com/markyafi1991/robomanager-slack.git
cd robomanager-slack
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Create a Slack app (From scratch) and enable:
- **Socket Mode** → generate an App-Level Token (`connections:write`) → `xapp-…`
- **Bot Token Scopes:** `chat:write`, `app_mentions:read`, `im:history`, `im:read`, `im:write`
- **Event Subscriptions** → bot events `app_mention` + `message.im`
- **Install to Workspace** → Bot User OAuth Token → `xoxb-…`
- **App Home** → enable the Messages tab and check *"Allow users to send messages…"*

Copy `.env.example` to `~/.config/robomanager/env` and fill it in.

## Run
```bash
python3 bot.py
# keep it alive on a Mac: caffeinate -is python3 bot.py
```
Then DM the bot in Slack, or @mention it in a channel it's been invited to.

## Extending
- **More tools:** add custom SDK tools (see `vault_tool.py`) or wire up other MCP servers (Toggl, GitHub, Notion…) in `manager_agent.py`.
- **Richer nudges:** have `nudges.py` read your daily note for a real morning brief.
- **Persona:** set `ROBOMANAGER_PERSONA` to retune its voice and role.

## License
MIT — see [LICENSE](LICENSE).
