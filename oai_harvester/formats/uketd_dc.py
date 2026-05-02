import xml.etree.ElementTree as ET

SCHEMA = "uketd_dc"
LABEL = "UK ETD Dublin Core  [EPrints / EThOS]"

DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
UKETD_NS = "http://naca.central.cranfield.ac.uk/ethos-oai/2.0/"

# uketd-specific fields and their output keys
_UKETD_FIELDS = {
    "institution": "institution",
    "advisor": "advisor",
    "sponsor": "sponsor",
    "qualificationlevel": "qualification.level",
    "qualificationname": "qualification.name",
    "checksum": "checksum",
}


def parse_metadata(metadata_el: ET.Element) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}

    # Standard DC elements
    for el in metadata_el.iter():
        if not el.text:
            continue
        ns, _, local = el.tag.partition("}")
        ns = ns.lstrip("{")
        if ns == DC_NS:
            fields.setdefault(local, []).append(el.text.strip())
        elif ns == DCTERMS_NS:
            fields.setdefault(f"dcterms.{local}", []).append(el.text.strip())

    # UKETD-specific simple fields
    for tag, key in _UKETD_FIELDS.items():
        for el in metadata_el.iter(f"{{{UKETD_NS}}}{tag}"):
            if el.text:
                fields.setdefault(key, []).append(el.text.strip())

    # Embargo date (nested inside freetoread)
    for ftr in metadata_el.iter(f"{{{UKETD_NS}}}freetoread"):
        for ed in ftr.iter(f"{{{UKETD_NS}}}embargodate"):
            if ed.text:
                fields.setdefault("embargo.date", []).append(ed.text.strip())

    return fields
