import xml.etree.ElementTree as ET

SCHEMA = "dim"
LABEL = "DSpace Intermediate Metadata  [DSpace]"

DIM_NS = "http://www.dspace.org/xmlns/dspace/dim"


def parse_metadata(metadata_el: ET.Element) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for el in metadata_el.iter(f"{{{DIM_NS}}}field"):
        schema = el.get("schema", "")
        element = el.get("element", "")
        qualifier = el.get("qualifier")
        if not element or not el.text:
            continue
        key = f"{schema}.{element}" if schema else element
        if qualifier:
            key = f"{key}.{qualifier}"
        fields.setdefault(key, []).append(el.text.strip())
    return fields
