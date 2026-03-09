import asyncio
import os

async def execute(operation, project_slug=None, repo_url=None, branch=None, message=None, files=None):
    """Perform git operations: clone, status, diff, commit, push, pull, log, branch, checkout."""
    projects_dir = os.environ.get("PROJECTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "projects"))
    cwd = os.path.join(projects_dir, project_slug) if project_slug else projects_dir
    async def run(cmd):
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd
        )
        out, err = await proc.communicate()
        return {"stdout": out.decode()[:5000], "stderr": err.decode()[:2000], "returncode": proc.returncode}
    if operation == "clone":
        if not repo_url:
            return {"error": "repo_url is required for clone"}
        target = os.path.join(projects_dir, project_slug) if project_slug else projects_dir
        return await run(f"git clone {repo_url} {target}")
    elif operation == "status":
        return await run("git status --porcelain")
    elif operation == "diff":
        return await run("git diff")
    elif operation == "commit":
        msg = message or "Auto commit"
        if files:
            await run("git add " + " ".join(files))
        else:
            await run("git add -A")
        return await run(f'git commit -m "{msg}"')
    elif operation == "push":
        cmd = f"git push origin {branch}" if branch else "git push"
        return await run(cmd)
    elif operation == "pull":
        cmd = f"git pull origin {branch}" if branch else "git pull"
        return await run(cmd)
    elif operation == "log":
        return await run("git log --oneline -20")
    elif operation == "branch":
        if branch:
            return await run(f"git checkout -b {branch}")
        return await run("git branch -a")
    elif operation == "checkout":
        if not branch:
            return {"error": "branch is required for checkout"}
        return await run(f"git checkout {branch}")
    return {"error": f"Unknown git operation: {operation}"}
