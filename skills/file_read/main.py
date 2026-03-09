async def execute(path):
    with open(path) as f:
        return {'content': f.read()}