from pathlib import Path
import os
import json

async def execute(project_slug, include_logs=True, include_file_tree=True, max_recent_logs=50):
    """Build complete project context."""
    base = Path(os.environ.get('PROJECTS_DIR', './data/projects')).resolve()
    project_dir = (base / project_slug).resolve()
    
    # Security check
    if not str(project_dir).startswith(str(base)):
        return {'error': 'Invalid project slug'}
    
    if not project_dir.exists():
        return {'error': f'Project not found: {project_slug}'}
    
    # Read project.json
    project_json = project_dir / 'project.json'
    if not project_json.exists():
        return {'error': 'Project config not found'}
    
    try:
        project_data = json.loads(project_json.read_text(encoding='utf-8'))
    except Exception as e:
        return {'error': f'Failed to read project config: {str(e)}'}
    
    # Read tasks.json
    tasks_json = project_dir / 'tasks.json'
    tasks = []
    if tasks_json.exists():
        try:
            tasks = json.loads(tasks_json.read_text(encoding='utf-8'))
        except Exception:
            pass
    
    # Calculate task statistics
    task_stats = {
        'total': len(tasks),
        'backlog': sum(1 for t in tasks if t.get('status') == 'backlog'),
        'todo': sum(1 for t in tasks if t.get('status') == 'todo'),
        'in_progress': sum(1 for t in tasks if t.get('status') == 'in_progress'),
        'review': sum(1 for t in tasks if t.get('status') == 'review'),
        'done': sum(1 for t in tasks if t.get('status') == 'done'),
        'cancelled': sum(1 for t in tasks if t.get('status') == 'cancelled'),
    }
    
    # Build task summaries (without full comments to reduce size)
    task_summaries = []
    for task in tasks:
        task_summaries.append({
            'id': task.get('id'),
            'key': task.get('key'),
            'title': task.get('title'),
            'status': task.get('status'),
            'priority': task.get('priority'),
            'assignee': task.get('assignee'),
            'labels': task.get('labels', []),
            'story_points': task.get('story_points'),
            'comment_count': len(task.get('comments', [])),
            'created_at': task.get('created_at'),
            'updated_at': task.get('updated_at'),
        })
    
    result = {
        'project': {
            'id': project_data.get('id'),
            'slug': project_data.get('slug'),
            'name': project_data.get('name'),
            'description': project_data.get('description', ''),
            'goals': project_data.get('goals', ''),
            'success_criteria': project_data.get('success_criteria', ''),
            'tech_stack': project_data.get('tech_stack', []),
            'status': project_data.get('status'),
            'tags': project_data.get('tags', []),
            'lead_agent_id': project_data.get('lead_agent_id'),
            'created_at': project_data.get('created_at'),
            'updated_at': project_data.get('updated_at'),
        },
        'task_stats': task_stats,
        'tasks': task_summaries,
    }
    
    # Include file tree if requested
    if include_file_tree:
        code_dir = project_dir / 'code'
        if code_dir.exists():
            files = []
            for file_path in sorted(code_dir.rglob('*')):
                if file_path.is_file():
                    files.append(str(file_path.relative_to(code_dir)))
            result['file_tree'] = {
                'total_files': len(files),
                'files': files
            }
        else:
            result['file_tree'] = {'total_files': 0, 'files': []}
    
    # Include recent activity logs if requested
    if include_logs:
        logs_json = project_dir / 'logs.json'
        if logs_json.exists():
            try:
                logs = json.loads(logs_json.read_text(encoding='utf-8'))
                # Get most recent logs
                recent_logs = logs[-max_recent_logs:] if len(logs) > max_recent_logs else logs
                result['recent_activity'] = recent_logs
            except Exception:
                result['recent_activity'] = []
        else:
            result['recent_activity'] = []
    
    return result
