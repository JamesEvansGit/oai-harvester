import xml.etree.ElementTree as ET

SCHEMA = "qdc"
LABEL = "Qualified Dublin Core  [DSpace / EPrints]"

DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"


def parse_metadata(metadata_el: ET.Element) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for el in metadata_el.iter():
        if not el.text:
            continue
        ns, _, local = el.tag.partition("}")
        if ns.lstrip("{") in (DC_NS, DCTERMS_NS) and local:
            fields.setdefault(local, []).append(el.text.strip())
    return fields
