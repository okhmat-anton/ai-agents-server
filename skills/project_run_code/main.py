from pathlib import Path
import os
import asyncio
async def execute(project_slug, file_path):
    base = Path(os.environ.get('PROJECTS_DIR', './data/projects')).resolve()
    code_dir = (base / project_slug / 'code').resolve()
    if not str(code_dir).startswith(str(base)):
        return {'error': 'Invalid project slug'}
    target = (code_dir / file_path).resolve()
    if not str(target).startswith(str(code_dir)):
        return {'error': 'Path traversal not allowed'}
    if not target.exists():
        return {'error': f'File {file_path} not found'}
    proc = await asyncio.create_subprocess_exec(
        'python3', target.name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(code_dir)
    )
    stdout, stderr = await proc.communicate()
    return {
        'stdout': stdout.decode('utf-8', errors='replace')[:5000],
        'stderr': stderr.decode('utf-8', errors='replace')[:2000],
        'exit_code': proc.returncode,
        'success': proc.returncode == 0
    }
