from pathlib import Path
import os, json
from datetime import datetime, timezone
async def execute(project_slug, task_id, status=None, assignee=None):
    base = Path(os.environ.get('PROJECTS_DIR', './data/projects')).resolve()
    tasks_path = base / project_slug / 'tasks.json'
    if not tasks_path.exists():
        return {'error': f'Project {project_slug} tasks not found'}
    tasks = json.loads(tasks_path.read_text(encoding='utf-8'))
    valid_statuses = ['backlog', 'todo', 'in_progress', 'review', 'done', 'cancelled']
    for t in tasks:
        if t.get('id') == task_id or t.get('key') == task_id:
            old_status = t.get('status')
            if status:
                if status not in valid_statuses:
                    return {'error': f'Invalid status: {status}. Valid: {valid_statuses}'}
                t['status'] = status
            if assignee is not None:
                t['assignee'] = assignee
            t['updated_at'] = datetime.now(timezone.utc).isoformat()
            tasks_path.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding='utf-8')
            # Write to project log
            log_path = base / project_slug / 'log.jsonl'
            entry = json.dumps({'ts': datetime.now(timezone.utc).isoformat(), 'level': 'info', 'message': f"Task {t.get('key')} moved: {old_status} → {status or old_status}", 'source': 'agent'})
            with open(log_path, 'a') as f:
                f.write(entry + '\n')
            return {'updated': True, 'task_key': t.get('key'), 'old_status': old_status, 'new_status': t.get('status')}
    return {'error': f'Task {task_id} not found in project {project_slug}'}
