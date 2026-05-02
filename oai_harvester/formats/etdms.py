import xml.etree.ElementTree as ET

SCHEMA = "etdms"
LABEL = "ETD Metadata Standard — theses  [DSpace / EPrints]"

NS = "http://www.ndltd.org/standards/metadata/etdms/1.0/"

SIMPLE = [
    "title", "creator", "subject", "description", "publisher",
    "contributor", "date", "type", "format", "identifier",
    "source", "language", "relation", "coverage", "rights",
]
DEGREE = ["name", "level", "discipline", "grantor"]


def parse_metadata(metadata_el: ET.Element) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}
    for tag in SIMPLE:
        for el in metadata_el.iter(f"{{{NS}}}{tag}"):
            if el.text:
                fields.setdefault(tag, []).append(el.text.strip())
    for degree_el in metadata_el.iter(f"{{{NS}}}degree"):
        for tag in DEGREE:
            for el in degree_el.iter(f"{{{NS}}}{tag}"):
                if el.text:
                    fields.setdefault(f"degree.{tag}", []).append(el.text.strip())
    return fields
