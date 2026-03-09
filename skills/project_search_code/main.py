import os
import re
import fnmatch

def execute(project_slug, query, is_regex=False, file_pattern=None, max_results=50):
    """Search through project source files by text or regex pattern."""
    projects_dir = os.environ.get("PROJECTS_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "projects"))
    project_dir = os.path.join(projects_dir, project_slug)
    if not os.path.isdir(project_dir):
        return {"error": f"Project directory not found: {project_slug}"}
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", ".next", "dist", "build", ".idea"}
    if is_regex:
        try:
            pat = re.compile(query, re.IGNORECASE)
        except re.error as e:
            return {"error": f"Invalid regex: {e}"}
    results = []
    for root, dirs, files in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            if file_pattern and not fnmatch.fnmatch(fname, file_pattern):
                continue
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, project_dir)
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        matched = pat.search(line) if is_regex else (query.lower() in line.lower())
                        if matched:
                            results.append({"file": rel_path, "line": line_num, "text": line.rstrip()[:200]})
                            if len(results) >= max_results:
                                return {"results": results, "total": len(results), "truncated": True}
            except (UnicodeDecodeError, PermissionError, IsADirectoryError):
                continue
    return {"results": results, "total": len(results), "truncated": False}
