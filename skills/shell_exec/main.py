import asyncio
async def execute(command):
    proc = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    return {'stdout': stdout.decode()[:5000], 'stderr': stderr.decode()[:2000], 'returncode': proc.returncode}