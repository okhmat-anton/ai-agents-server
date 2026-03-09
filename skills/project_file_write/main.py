from pathlib import Path
import os
async def execute(project_slug, path, content):
    base = Path(os.environ.get('PROJECTS_DIR', './data/projects')).resolve()
    code_dir = (base / project_slug / 'code').resolve()
    if not str(code_dir).startswith(str(base)):
        return {'error': 'Invalid project slug'}
    file_path = (code_dir / path).resolve()
    if not str(file_path).startswith(str(code_dir)):
        return {'error': 'Path traversal not allowed'}
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')
    return {'written': len(content), 'path': str(file_path.relative_to(code_dir))}
