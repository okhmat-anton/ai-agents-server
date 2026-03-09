import asyncio

async def execute(operation, container=None, tail=50):
    """Manage Docker containers: list, start, stop, restart, logs, status, images."""
    async def run(cmd):
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, err = await proc.communicate()
        return {"stdout": out.decode()[:5000], "stderr": err.decode()[:2000], "returncode": proc.returncode}
    if operation == "list":
        return await run("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}'")
    elif operation == "start":
        if not container:
            return {"error": "container name required"}
        return await run(f"docker start {container}")
    elif operation == "stop":
        if not container:
            return {"error": "container name required"}
        return await run(f"docker stop {container}")
    elif operation == "restart":
        if not container:
            return {"error": "container name required"}
        return await run(f"docker restart {container}")
    elif operation == "logs":
        if not container:
            return {"error": "container name required"}
        return await run(f"docker logs --tail {tail} {container}")
    elif operation == "status":
        if container:
            return await run(f"docker inspect --format '{{{{.State.Status}}}}' {container}")
        return await run("docker ps -a --format 'table {{.Names}}\t{{.Status}}'")
    elif operation == "images":
        return await run("docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}'")
    return {"error": f"Unknown docker operation: {operation}"}
