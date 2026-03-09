from pathlib import Path
import os
async def execute(project_slug):
    base = Path(os.environ.get('PROJECTS_DIR', './data/projects')).resolve()
    code_dir = (base / project_slug / 'code').resolve()
    if not code_dir.exists():
        return {'files': [], 'error': 'No code directory found'}
    files = []
    for f in sorted(code_dir.rglob('*')):
        if f.is_file():
            files.append(str(f.relative_to(code_dir)))
    return {'files': files, 'total': len(files)}
