import xml.etree.ElementTree as ET

SCHEMA = "xoai"
LABEL = "Extended OAI  [DSpace]"

XOAI_NS = "http://www.lyncode.com/xoai"


def parse_metadata(metadata_el: ET.Element) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    root = metadata_el.find(f"{{{XOAI_NS}}}metadata")
    if root is None:
        root = metadata_el
    _walk(root, "", fields)
    return fields


def _walk(el: ET.Element, path: str, fields: dict[str, list[str]]) -> None:
    for child in el:
        local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if local == "element":
            name = child.get("name", "")
            new_path = f"{path}.{name}" if path else name
            _walk(child, new_path, fields)
        elif local == "field":
            fname = child.get("name", "value")
            key = f"{path}.{fname}" if fname != "value" else path
            if child.text:
                fields.setdefault(key, []).append(child.text.strip())
