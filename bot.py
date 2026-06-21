"""RoboManager — a two-way Slack manager bot (Socket Mode) + proactive nudges.

Run:  python3 bot.py   (after `pip install -r requirements.txt` and setting tokens)
"""
import asyncio
import logging

import config
from manager_agent import run_agent
import nudges

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("robomanager")

config.require("SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "ROBOMANAGER_KNOWLEDGE_PATH")
if not config.ANTHROPIC_API_KEY:
    log.info("No ANTHROPIC_API_KEY set — using your Claude Code login (subscription auth).")

app = AsyncApp(token=config.SLACK_BOT_TOKEN)
SESSIONS: dict[str, str] = {}  # channel -> Agent SDK session_id (conversation continuity)


async def _respond(text: str, channel: str, say) -> None:
    try:
        reply, session = await run_agent(text, resume=SESSIONS.get(channel))
        if session:
            SESSIONS[channel] = session
        await say(reply)
    except Exception as e:  # keep the bot alive on any single-turn failure
        log.exception("agent error")
        await say(f"⚠️ I hit an error: {e}")


@app.event("app_mention")
async def on_mention(event, say):
    await _respond(event.get("text", ""), event["channel"], say)


@app.event("message")
async def on_message(event, say):
    # Only respond to direct messages; never to bots or our own messages.
    if event.get("channel_type") == "im" and not event.get("bot_id") and event.get("subtype") is None:
        await _respond(event.get("text", ""), event["channel"], say)


# --- Proactive nudges ---
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
