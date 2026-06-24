"""RoboManager — a two-way Slack manager bot on the Claude Agent SDK.

Uses Slack's native Assistant framework (Agents & AI Apps): a dedicated AI pane,
suggested prompts on open, and the real "is thinking…" status indicator — plus
proactive nudges and channel @mentions.

Run:  python3 bot.py   (after `pip install -r requirements.txt` and setting tokens)
"""
import asyncio
import logging

import config
from manager_agent import run_agent
import nudges

from slack_bolt.async_app import AsyncApp, AsyncAssistant
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("robomanager")

config.require("SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "ROBOMANAGER_KNOWLEDGE_PATH")
if not config.ANTHROPIC_API_KEY:
    log.info("No ANTHROPIC_API_KEY set — using your Claude Code login (subscription auth).")

app = AsyncApp(token=config.SLACK_BOT_TOKEN)
assistant = AsyncAssistant()
SESSIONS: dict[str, str] = {}  # thread key -> Agent SDK session_id (conversation continuity)

# Words that wipe a thread's memory and start fresh.
_RESET = {"reset", "clear", "clear chat", "new chat", "start over", "forget", "wipe"}


async def _handle(text: str, key: str, say, set_status=None) -> None:
    """One conversational turn, shared by the assistant pane and channel @mentions."""
    if (text or "").strip().lower() in _RESET:
        SESSIONS.pop(key, None)
        await say("Fresh start — wiped this thread's memory. What's next?")
        return
    try:
        if set_status:
            await set_status("is thinking…")  # native Slack assistant status indicator
        reply, session = await run_agent(text, resume=SESSIONS.get(key))
        if session:
            SESSIONS[key] = session
        await say(reply or "…")
    except Exception as e:  # keep the bot alive on any single-turn failure
        log.exception("agent error")
        await say(f"I hit an error: {e}")


# ---------------- Assistant: the AI pane (Agents & AI Apps) ----------------

@assistant.thread_started
async def on_thread_started(say, set_suggested_prompts):
    await say("RoboManager here — I read your notes and help you pick the single "
              "highest-leverage next thing to do. What are we working on?")
    try:
        await set_suggested_prompts(prompts=[
            {"title": "Plan my day", "message": "What should I work on next?"},
            {"title": "What's due?", "message": "What's overdue or due soon in my notes?"},
            {"title": "Summarize", "message": "Summarize my most recent daily note."},
            {"title": "Where am I?", "message": "Give me a quick status of my current priorities."},
        ])
    except Exception:
        log.exception("set_suggested_prompts failed")


@assistant.user_message
async def on_user_message(message, say, set_status):
    key = message.get("thread_ts") or message.get("ts") or message.get("channel")
    await _handle(message.get("text", ""), key, say, set_status)


app.use(assistant)


# ---------------- Channel @mentions ----------------

@app.event("app_mention")
async def on_mention(event, say):
    await _handle(event.get("text", ""), f"mention:{event['channel']}", say)


# ---------------- Proactive nudges ----------------

scheduler = AsyncIOScheduler(timezone=config.TIMEZONE)


async def _post(text: str | None) -> None:
    if text and config.NUDGE_CHANNEL:
        await app.client.chat_postMessage(channel=config.NUDGE_CHANNEL, text=text)


async def _morning_job():
    await _post(await nudges.morning())


async def _eod_job():
    await _post(await nudges.eod())


def _schedule() -> None:
    if not config.NUDGE_CHANNEL:
        log.info("ROBOMANAGER_CHANNEL not set — proactive nudges off (chat still works).")
        return
    scheduler.add_job(_morning_job, "cron", hour=7, minute=0)
    scheduler.add_job(_eod_job, "cron", hour=18, minute=0)
    scheduler.start()
    log.info("Nudges scheduled: morning 07:00, EOD 18:00.")


async def main() -> None:
    _schedule()
    log.info("RoboManager connecting to Slack (Socket Mode)...")
    handler = AsyncSocketModeHandler(app, config.SLACK_APP_TOKEN)
    await handler.start_async()


if __name__ == "__main__":
    asyncio.run(main())
