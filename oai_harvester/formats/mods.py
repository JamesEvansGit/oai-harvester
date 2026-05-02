import xml.etree.ElementTree as ET

SCHEMA = "mods"
LABEL = "MODS — Metadata Object Description Schema  [EPrints / general]"

NS = "http://www.loc.gov/mods/v3"


def _n(tag: str) -> str:
    return f"{{{NS}}}{tag}"


def _text(el: ET.Element, tag: str) -> str:
    found = el.find(_n(tag))
    return (found.text or "").strip() if found is not None else ""


def _assemble_name(name_el: ET.Element) -> str:
    parts: dict[str, str] = {}
    simple: list[str] = []
    for np in name_el.findall(_n("namePart")):
        t = np.get("type", "")
        val = (np.text or "").strip()
        if not val:
            continue
        if t == "family":
            parts["family"] = val
        elif t == "given":
            parts["given"] = val
        elif not t:
            simple.append(val)
    if "family" in parts and "given" in parts:
        return f"{parts['family']}, {parts['given']}"
    if "family" in parts:
        return parts["family"]
    return " ".join(simple)


def parse_metadata(metadata_el: ET.Element) -> dict[str, list[str]]:
    fields: dict[str, list[str]] = {}

    # Titles
    for ti in metadata_el.iter(_n("titleInfo")):
        ti_type = ti.get("type", "")
        title = _text(ti, "title")
        subtitle = _text(ti, "subTitle")
        full = f"{title}: {subtitle}" if subtitle else title
        if full:
            key = "title.alternative" if ti_type == "alternative" else "title"
            fields.setdefault(key, []).append(full)

    # Names (authors / contributors)
    for name_el in metadata_el.iter(_n("name")):
        assembled = _assemble_name(name_el)
        if not assembled:
            continue
        role_terms = [
            rt.text.strip().lower()
            for rt in name_el.iter(_n("roleTerm"))
            if rt.text
        ]
        key = "contributor" if role_terms and "author" not in role_terms else "creator"
        fields.setdefault(key, []).append(assembled)

    # Type and genre
    for tag in ("typeOfResource", "genre"):
        for el in metadata_el.iter(_n(tag)):
            if el.text:
                fields.setdefault(tag, []).append(el.text.strip())

    # Origin info
    for oi in metadata_el.iter(_n("originInfo")):
        for tag, key in (
            ("dateIssued", "date.issued"),
            ("dateCreated", "date.created"),
            ("dateCaptured", "date.captured"),
            ("publisher", "publisher"),
            ("edition", "edition"),
        ):
            for el in oi.findall(_n(tag)):
                if el.text:
                    fields.setdefault(key, []).append(el.text.strip())
        for place in oi.iter(_n("placeTerm")):
            if place.text:
                fields.setdefault("place", []).append(place.text.strip())

    # Language
    for lang in metadata_el.iter(_n("languageTerm")):
        if lang.text:
            fields.setdefault("language", []).append(lang.text.strip())

    # Abstract and notes
    for tag, key in (("abstract", "abstract"), ("note", "note")):
        for el in metadata_el.iter(_n(tag)):
            if el.text:
                fields.setdefault(key, []).append(el.text.strip())

    # Subjects
    for subj in metadata_el.iter(_n("subject")):
        for child in subj:
            local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if child.text:
                fields.setdefault(f"subject.{local}", []).append(child.text.strip())

    # Identifiers (keyed by type attribute)
    for ident in metadata_el.iter(_n("identifier")):
        if ident.text:
            id_type = ident.get("type", "other")
            fields.setdefault(f"identifier.{id_type}", []).append(ident.text.strip())

    # URLs
    for url_el in metadata_el.iter(_n("url")):
        if url_el.text:
            fields.setdefault("location.url", []).append(url_el.text.strip())

    # Related item — journal host details
    for ri in metadata_el.iter(_n("relatedItem")):
        if ri.get("type") != "host":
            continue
        journal_title = ""
        ti = ri.find(_n("titleInfo"))
        if ti is not None:
            journal_title = _text(ti, "title")
        if journal_title:
            fields.setdefault("journal.title", []).append(journal_title)
        for detail in ri.iter(_n("detail")):
            d_type = detail.get("type", "")
            number = _text(detail, "number")
            if d_type and number:
                fields.setdefault(f"journal.{d_type}", []).append(number)
        for extent in ri.iter(_n("extent")):
            start = _text(extent, "start")
            end = _text(extent, "end")
            if start and end:
                fields.setdefault("journal.pages", []).append(f"{start}-{end}")
            elif start:
                fields.setdefault("journal.pages", []).append(start)

    # Access condition and physical description
    for tag, key in (
        ("accessCondition", "accessCondition"),
        ("physicalDescription/extent", "extent"),
        ("physicalDescription/form", "form"),
    ):
        for el in metadata_el.iter(_n(tag.split("/")[-1])):
            if el.text:
                fields.setdefault(key, []).append(el.text.strip())

    # Record dates
    for tag, key in (
        ("recordCreationDate", "record.created"),
        ("recordChangeDate", "record.modified"),
    ):
        for el in metadata_el.iter(_n(tag)):
            if el.text:
                fields.setdefault(key, []).append(el.text.strip())

    return fields
