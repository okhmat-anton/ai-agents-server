"""
Sync TODO list items from agent protocol output to MongoDB tasks.
Extracted from autonomous_runner.py for use in chat.py without PostgreSQL dependency.
"""
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.mongodb.models import MongoTask
from app.mongodb.services import TaskService


_TODO_STATUS_TO_TASK = {
    "pending": "pending",
    "in_progress": "running",
    "done": "completed",
    "skipped": "cancelled",
}


async def sync_todos_to_tasks(
    db: AsyncIOMotorDatabase,
    agent_id: str,
    todo_items: list[dict],
    todo_task_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """
    Synchronise the agent's TODO list (from <<<TODO>>> markers) with
    MongoDB tasks so that every TODO item is visible in the Tasks tab.

    Returns updated todo_task_map dict.
    """
    task_svc = TaskService(db)
    mapping = dict(todo_task_map or {})
    agent_id_str = str(agent_id)
    now = datetime.now(timezone.utc)

    for item in todo_items:
        todo_id = str(item.get("id", ""))
        title = (item.get("task") or item.get("title") or f"Task {todo_id}")[:500]
        status = _TODO_STATUS_TO_TASK.get(item.get("status", "pending"), "pending")

        existing_task_id = mapping.get(todo_id)

        if existing_task_id:
            # Update existing task
            task = await task_svc.get_by_id(existing_task_id)
            if task:
                update_data = {}
                if task.title != title:
                    update_data["title"] = title
                if task.status != status:
                    update_data["status"] = status
                    if status == "completed" and not task.completed_at:
                        update_data["completed_at"] = now.isoformat()
                    elif status == "running" and not task.started_at:
                        update_data["started_at"] = now.isoformat()
                if update_data:
                    update_data["updated_at"] = now.isoformat()
                    await task_svc.update(existing_task_id, update_data)
            else:
                # Task was deleted — re-create
                new_task = MongoTask(
                    agent_id=agent_id_str,
                    title=title,
                    description="Auto-created from agent TODO list",
                    type="one_time",
                    status=status,
                    priority="normal",
                )
                new_task = await task_svc.create(new_task)
                mapping[todo_id] = str(new_task.id)
        else:
            # Create new task
            new_task = MongoTask(
                agent_id=agent_id_str,
                title=title,
                description="Auto-created from agent TODO list",
                type="one_time",
                status=status,
                priority="normal",
            )
            if status == "running":
                new_task.started_at = now
            elif status == "completed":
                new_task.started_at = now
                new_task.completed_at = now
            new_task = await task_svc.create(new_task)
            mapping[todo_id] = str(new_task.id)

    return mapping
