import xml.etree.ElementTree as ET
import json

def _elem_to_dict(elem):
    result = {}
    if elem.attrib:
        result["@attributes"] = dict(elem.attrib)
    if elem.text and elem.text.strip():
        if not list(elem):
            return elem.text.strip()
        result["#text"] = elem.text.strip()
    for child in elem:
        child_data = _elem_to_dict(child)
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag in result:
            if not isinstance(result[tag], list):
                result[tag] = [result[tag]]
            result[tag].append(child_data)
        else:
            result[tag] = child_data
    return result or (elem.text.strip() if elem.text else "")

def execute(text=None, file_path=None, xpath=None, output_format="json"):
    """Parse XML data, optionally query with XPath."""
    if not text and not file_path:
        return {"error": "Either text or file_path is required"}
    if file_path and not text:
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        return {"error": f"XML parse error: {e}"}
    if xpath:
        elements = root.findall(xpath)
        results = [_elem_to_dict(el) for el in elements]
        return {"results": results, "count": len(results), "xpath": xpath}
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag
    return {"root_tag": tag, "data": _elem_to_dict(root)}
