# Reminder scheduling — creates a task in MongoDB.
# Primary execution path is via the pipeline handler (_sys_schedule_reminder).

async def execute(title, message, trigger_at, recurring=False):
    """Schedule a reminder. Requires pipeline context for database access."""
    return {
        "error": "schedule_reminder requires database access through the pipeline. "
                 "This skill must be executed through the pipeline handler."
    }
