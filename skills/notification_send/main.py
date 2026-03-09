# Notification sending — routes through configured messenger.
# Primary execution path is via the pipeline handler (_sys_notification_send).

async def execute(title, message, priority="normal"):
    """Send a notification to the owner. Requires pipeline context for messenger access."""
    return {
        "error": "notification_send requires messenger context from the pipeline. "
                 "This skill must be executed through the pipeline handler."
    }
