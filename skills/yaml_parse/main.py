import yaml
import json

def execute(text=None, file_path=None, operation="parse"):
    """Parse, validate, and convert YAML data."""
    if not text and not file_path:
        return {"error": "Either text or file_path is required"}
    if file_path and not text:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        return {"error": f"YAML parse error: {e}", "valid": False}
    if operation == "validate":
        return {"valid": True, "type": type(data).__name__}
    if operation == "to_json":
        return {"json": json.dumps(data, indent=2, ensure_ascii=False, default=str)}
    return {"data": data, "type": type(data).__name__}
