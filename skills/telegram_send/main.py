# Telegram message sending — requires running Telethon client from messenger config.
# Primary execution path is via the pipeline handler (_sys_telegram_send).
# This standalone fallback will not work without active messenger sessions.

async def execute(messenger_id, chat_id, text, parse_mode="markdown"):
    """Send a Telegram message. Requires active messenger session in pipeline context."""
    return {
        "error": "telegram_send requires an active Telethon session. "
                 "This skill must be executed through the pipeline handler, "
                 "not standalone. Ensure a Telegram messenger is configured and running."
    }
