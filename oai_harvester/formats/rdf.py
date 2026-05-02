import xml.etree.ElementTree as ET

SCHEMA = "rdf"
LABEL = "RDF/XML  [EPrints]"

RDF_NS = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
DC_NS = "http://purl.org/dc/elements/1.1/"
DCTERMS_NS = "http://purl.org/dc/terms/"
EPRINT_NS = "http://purl.org/eprint/terms/"
BIBO_NS = "http://purl.org/ontology/bibo/"


def parse_metadata(metadata_el: ET.Element) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}

    for el in metadata_el.iter():
        ns, _, local = el.tag.partition("}")
        ns = ns.lstrip("{")

        if ns == DC_NS and el.text:
            fields.setdefault(local, []).append(el.text.strip())

        elif ns == DCTERMS_NS:
            if el.text:
                fields.setdefault(f"dcterms.{local}", []).append(el.text.strip())
            # Type is carried as rdf:resource URI — extract the terminal segment
            if local == "type":
                resource = el.get(f"{{{RDF_NS}}}resource", "").strip()
                if resource:
                    type_name = resource.rstrip("/").rsplit("/", 1)[-1]
                    fields.setdefault("dcterms.type", []).append(type_name)

        elif ns == EPRINT_NS and el.text:
            fields.setdefault(f"eprint.{local}", []).append(el.text.strip())

        elif ns == BIBO_NS and el.text:
            fields.setdefault(f"bibo.{local}", []).append(el.text.strip())

    # Bitstream URLs: rdf:Description elements that carry a dc:format are file nodes.
    # Their rdf:about attribute is the file URL.
    for desc in metadata_el.iter(f"{{{RDF_NS}}}Description"):
        about = desc.get(f"{{{RDF_NS}}}about", "").strip()
        fmt_el = desc.find(f"{{{DC_NS}}}format")
        title_el = (
            desc.find(f"{{{DCTERMS_NS}}}title")
            or desc.find(f"{{{DC_NS}}}title")
        )
        if about and fmt_el is not None:
            fields.setdefault("bitstream.url", []).append(about)
            if fmt_el.text:
                fields.setdefault("bitstream.mimetype", []).append(fmt_el.text.strip())
            if title_el is not None and title_el.text:
                fields.setdefault("bitstream.title", []).append(title_el.text.strip())

    return fields
