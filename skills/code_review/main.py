import os

def execute(code=None, file_path=None, language=None, focus="all"):
    """Review code for bugs, security, style, performance. Returns basic static analysis standalone."""
    if not code and not file_path:
        return {"error": "Either code or file_path is required"}
    if file_path and not code:
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
    if not language:
        if file_path:
            ext = os.path.splitext(file_path)[1]
            lang_map = {".py": "python", ".js": "javascript", ".ts": "typescript", ".go": "go", ".rs": "rust", ".java": "java", ".rb": "ruby", ".php": "php"}
            language = lang_map.get(ext, "unknown")
        else:
            language = "unknown"
    issues = []
    lines = code.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.rstrip()
        if len(stripped) > 120:
            issues.append({"line": i, "type": "style", "message": f"Line too long ({len(stripped)} chars)"})
        if "TODO" in line or "FIXME" in line or "HACK" in line:
            issues.append({"line": i, "type": "info", "message": f"Found marker: {stripped.strip()[:80]}"})
        if language == "python":
            if "eval(" in line and "safe" not in line.lower():
                issues.append({"line": i, "type": "security", "message": "Potential unsafe eval() usage"})
            if "exec(" in line:
                issues.append({"line": i, "type": "security", "message": "Potential unsafe exec() usage"})
            if "import *" in line:
                issues.append({"line": i, "type": "style", "message": "Wildcard import"})
            if "except:" in line and "except Exception" not in line:
                issues.append({"line": i, "type": "bugs", "message": "Bare except clause"})
            if "password" in line.lower() and "=" in line and ("'" in line or '"' in line):
                issues.append({"line": i, "type": "security", "message": "Possible hardcoded password"})
        if language in ("javascript", "typescript"):
            if "eval(" in line:
                issues.append({"line": i, "type": "security", "message": "eval() usage"})
            if "var " in line:
                issues.append({"line": i, "type": "style", "message": "Use let/const instead of var"})
            if "console.log" in line:
                issues.append({"line": i, "type": "info", "message": "console.log found"})
    if focus != "all":
        issues = [iss for iss in issues if iss["type"] == focus]
    return {
        "language": language, "total_lines": len(lines), "issues": issues[:50],
        "issue_count": len(issues),
        "note": "Basic static analysis only. For deeper LLM-powered review, execute through the pipeline handler."
    }
