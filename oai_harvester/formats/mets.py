import xml.etree.ElementTree as ET

SCHEMA = "mets"
LABEL = "METS  [DSpace]"

METS_NS = "http://www.loc.gov/METS/"
XLINK_NS = "http://www.w3.org/1999/xlink"
DIM_NS = "http://www.dspace.org/xmlns/dspace/dim"
DC_NS = "http://purl.org/dc/elements/1.1/"


def parse_metadata(metadata_el: ET.Element) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}

    # --- Descriptive metadata (dmdSec) ---

    # DSpace METS embeds DIM — try that first
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

    # Fallback: plain DC elements
    if not fields:
        for el in metadata_el.iter():
            ns, _, local = el.tag.partition("}")
            if ns.lstrip("{") == DC_NS and el.text:
                fields.setdefault(local, []).append(el.text.strip())

    # --- File section (fileSec) — bitstream URLs and MIME types ---
    for file_grp in metadata_el.iter(f"{{{METS_NS}}}fileGrp"):
        group = file_grp.get("USE", "").strip()
        for file_el in file_grp.iter(f"{{{METS_NS}}}file"):
            mimetype = file_el.get("MIMETYPE", "").strip()
            size = file_el.get("SIZE", "").strip()
            for flocat in file_el.iter(f"{{{METS_NS}}}FLocat"):
                href = flocat.get(f"{{{XLINK_NS}}}href", "").strip()
                if href:
                    fields.setdefault("bitstream.url", []).append(href)
                if mimetype:
                    fields.setdefault("bitstream.mimetype", []).append(mimetype)
                if size:
                    fields.setdefault("bitstream.size", []).append(size)
                if group:
                    fields.setdefault("bitstream.group", []).append(group)

    return fields
