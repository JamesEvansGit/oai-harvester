import xml.etree.ElementTree as ET

SCHEMA = "ore"
LABEL = "Object Reuse and Exchange (ORE)  [DSpace / EPrints]"

ATOM_NS = "http://www.w3.org/2005/Atom"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
ORE_AGGREGATES_REL = "http://www.openarchives.org/ore/terms/aggregates"

# Atom elements captured as-is
_ATOM_SCALARS = ("title", "id", "updated", "published", "summary")


def parse_metadata(metadata_el: ET.Element) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}

    # Atom scalar fields (single-value)
    for tag in _ATOM_SCALARS:
        el = metadata_el.find(f".//{{{ATOM_NS}}}{tag}")
        if el is not None and el.text:
            fields[tag] = [el.text.strip()]

    # Authors
    for author_el in metadata_el.iter(f"{{{ATOM_NS}}}author"):
        name_el = author_el.find(f"{{{ATOM_NS}}}name")
        if name_el is not None and name_el.text:
            fields.setdefault("author", []).append(name_el.text.strip())

    # Bitstream / aggregated resource links
    for link_el in metadata_el.iter(f"{{{ATOM_NS}}}link"):
        if link_el.get("rel") != ORE_AGGREGATES_REL:
            continue
        href = link_el.get("href", "").strip()
        title = link_el.get("title", "").strip()
        mimetype = link_el.get("type", "").strip()
        description = link_el.get("description", "").strip()
        if href:
            fields.setdefault("bitstream.url", []).append(href)
        if title:
            fields.setdefault("bitstream.title", []).append(title)
        if mimetype:
            fields.setdefault("bitstream.mimetype", []).append(mimetype)
        if description:
            fields.setdefault("bitstream.description", []).append(description)

    # DC elements (prefixed dc. to avoid collision with Atom fields)
    for el in metadata_el.iter():
        if not el.text:
            continue
        ns, _, local = el.tag.partition("}")
        ns = ns.lstrip("{")
        if ns == DC_NS:
            fields.setdefault(f"dc.{local}", []).append(el.text.strip())
        elif ns == DCTERMS_NS:
            fields.setdefault(f"dcterms.{local}", []).append(el.text.strip())

    return fields
