import xml.etree.ElementTree as ET

SCHEMA = "oai_dc"
LABEL = "Dublin Core  [all platforms]"

DC_NS = "http://purl.org/dc/elements/1.1/"
FIELDS = [
    "title", "creator", "subject", "description", "publisher",
    "contributor", "date", "type", "format", "identifier",
    "source", "language", "relation", "coverage", "rights",
]


def parse_metadata(metadata_el: ET.Element) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for el in metadata_el.iter():
        ns, _, local = el.tag.partition("}")
        if ns.lstrip("{") == DC_NS and local in FIELDS and el.text:
            fields.setdefault(local, []).append(el.text.strip())
    return fields
