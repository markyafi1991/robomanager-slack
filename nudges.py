"""Scheduled, proactive nudges posted to Slack.

These are intentionally simple prompts. Extend them to read your knowledge base
(e.g. pull today's plan from a daily note) for richer, data-driven nudges.
"""


async def morning() -> str:
    return ("🌅 *Morning.* What's the one thing that, if it gets done today, makes the day a win? "
            "Tell me and I'll help you start.")


async def eod() -> str:
    return "🌙 *EOD check-in.* What moved today — and what's the first action for tomorrow?"
