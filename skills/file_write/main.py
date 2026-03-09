async def execute(path, content):
    with open(path, 'w') as f:
        f.write(content)
    return {'written': len(content)}