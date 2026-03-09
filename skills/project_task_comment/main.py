from pathlib import Path
import os, json, uuid
from datetime import datetime, timezone
async def execute(project_slug, task_id, content, author='agent'):
    base = Path(os.environ.get('PROJECTS_DIR', './data/projects')).resolve()
    tasks_path = base / project_slug / 'tasks.json'
    if not tasks_path.exists():
        return {'error': f'Project {project_slug} tasks not found'}
    tasks = json.loads(tasks_path.read_text(encoding='utf-8'))
    for t in tasks:
        if t.get('id') == task_id or t.get('key') == task_id:
            if 'comments' not in t:
                t['comments'] = []
            comment = {
                'id': uuid.uuid4().hex[:12],
                'content': content,
                'author': author,
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
            t['comments'].append(comment)
            t['updated_at'] = datetime.now(timezone.utc).isoformat()
            tasks_path.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding='utf-8')
            return {'added': True, 'comment_id': comment['id'], 'task_key': t.get('key')}
    return {'error': f'Task {task_id} not found in project {project_slug}'}
