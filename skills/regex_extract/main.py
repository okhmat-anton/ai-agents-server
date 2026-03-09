import re

def execute(text, pattern, operation="extract", replacement=None, flags=""):
    """Extract data from text using regex patterns."""
    re_flags = 0
    if "i" in flags:
        re_flags |= re.IGNORECASE
    if "m" in flags:
        re_flags |= re.MULTILINE
    if "s" in flags:
        re_flags |= re.DOTALL
    try:
        compiled = re.compile(pattern, re_flags)
    except re.error as e:
        return {"error": f"Invalid regex: {e}"}
    if operation == "match":
        m = compiled.search(text)
        if not m:
            return {"match": False}
        return {"match": True, "full": m.group(0), "groups": list(m.groups()), "groupdict": m.groupdict(), "span": list(m.span())}
    if operation == "replace":
        if replacement is None:
            return {"error": "replacement is required for replace operation"}
        result = compiled.sub(replacement, text)
        return {"result": result, "replacements": len(compiled.findall(text))}
    if operation == "split":
        parts = compiled.split(text)
        return {"parts": parts, "count": len(parts)}
    # default: extract
    matches = []
    for m in compiled.finditer(text):
        entry = {"match": m.group(0), "span": list(m.span())}
        if m.groups():
            entry["groups"] = list(m.groups())
        if m.groupdict():
            entry["named"] = m.groupdict()
        matches.append(entry)
    return {"matches": matches, "total": len(matches)}
