from pathlib import Path
import os
import json
import re

async def execute(project_slug, task_id, include_comments=True, include_related_files=True, include_activity=True):
    """Build complete task context."""
    base = Path(os.environ.get('PROJECTS_DIR', './data/projects')).resolve()
    project_dir = (base / project_slug).resolve()
    
    # Security check
    if not str(project_dir).startswith(str(base)):
        return {'error': 'Invalid project slug'}
    
    if not project_dir.exists():
        return {'error': f'Project not found: {project_slug}'}
    
    # Read tasks.json
    tasks_json = project_dir / 'tasks.json'
    if not tasks_json.exists():
        return {'error': 'Tasks file not found'}
    
    try:
        tasks = json.loads(tasks_json.read_text(encoding='utf-8'))
    except Exception as e:
        return {'error': f'Failed to read tasks: {str(e)}'}
    
    # Find the task by ID or key
    task = None
    for t in tasks:
        if t.get('id') == task_id or t.get('key') == task_id:
            task = t
            break
    
    if not task:
        return {'error': f'Task not found: {task_id}'}
    
    # Build result
    result = {
        'task': {
            'id': task.get('id'),
            'key': task.get('key'),
            'title': task.get('title'),
            'description': task.get('description', ''),
            'status': task.get('status'),
            'priority': task.get('priority'),
            'assignee': task.get('assignee', ''),
            'labels': task.get('labels', []),
            'story_points': task.get('story_points'),
            'created_at': task.get('created_at'),
            'updated_at': task.get('updated_at'),
        }
    }
    
    # Include comments if requested
    if include_comments:
        result['comments'] = task.get('comments', [])
    
    # Get task key for log filtering
    task_key = task.get('key', '')
    
    # Read logs for activity and related files
    logs_json = project_dir / 'logs.json'
    logs = []
    if logs_json.exists():
        try:
            logs = json.loads(logs_json.read_text(encoding='utf-8'))
        except Exception:
            pass
    
    # Filter logs related to this task (by task key mention in message)
    task_logs = []
    if task_key:
        for log in logs:
            message = log.get('message', '')
            # Check if task key is mentioned in log message
            if task_key in message or task.get('id') in message:
                task_logs.append(log)
    
    # Include activity timeline if requested
    if include_activity:
        result['activity'] = task_logs
    
    # Infer related files from logs if requested
    if include_related_files:
        related_files = set()
        
        # Pattern to match file operations in logs
        # e.g. "File created: main.py", "Execute: `python3 main.py`"
        file_patterns = [
            r'File created: ([^\s]+)',
            r'File modified: ([^\s]+)',
            r'File deleted: ([^\s]+)',
            r'`python3?\s+([^\s`]+)',
            r'Execute:.*?([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)',
        ]
        
        for log in task_logs:
            message = log.get('message', '')
            for pattern in file_patterns:
                matches = re.findall(pattern, message)
                for match in matches:
                    # Clean up the file path
                    file_path = match.strip('`').strip()
                    if file_path and not file_path.startswith('/'):
                        related_files.add(file_path)
        
        result['related_files'] = sorted(list(related_files))
    
    # Check for subtasks (parent_task_id field support - if it exists)
    subtasks = []
    for t in tasks:
        if t.get('parent_task_id') == task.get('id'):
            subtasks.append({
                'id': t.get('id'),
                'key': t.get('key'),
                'title': t.get('title'),
                'status': t.get('status'),
            })
    
    result['subtasks'] = subtasks
    
    # Check for parent task
    parent_task_id = task.get('parent_task_id')
    if parent_task_id:
        for t in tasks:
            if t.get('id') == parent_task_id:
                result['parent_task'] = {
                    'id': t.get('id'),
                    'key': t.get('key'),
                    'title': t.get('title'),
                    'status': t.get('status'),
                }
                break
    else:
        result['parent_task'] = None
    
    return result
