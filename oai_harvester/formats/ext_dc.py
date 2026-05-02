import xml.etree.ElementTree as ET

SCHEMA = "ext_dc"
LABEL = "Extended Dublin Core  [DSpace]"

DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"


def parse_metadata(metadata_el: ET.Element) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for el in metadata_el.iter():
        if not el.text:
            continue
        ns, _, local = el.tag.partition("}")
        ns = ns.lstrip("{")
        if ns == DC_NS:
            fields.setdefault(local, []).append(el.text.strip())
        elif ns == DCTERMS_NS:
            fields.setdefault(f"dcterms.{local}", []).append(el.text.strip())
    return fields
