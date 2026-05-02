"""Output format writers."""
import csv
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from typing import Callable, Optional

from .models import Record

try:
    import openpyxl
    from openpyxl.styles import Font
    _HAS_OPENPYXL = True
except ImportError:
    _HAS_OPENPYXL = False

try:
    from pymarc import Field, Record as MarcRecord
    _HAS_PYMARC = True
except ImportError:
    _HAS_PYMARC = False

try:
    import rdflib
    from rdflib import Graph, Literal, Namespace, URIRef
    _HAS_RDFLIB = True
except ImportError:
    _HAS_RDFLIB = False


@dataclass
class WriterSpec:
    name: str
    label: str
    ext: str
    fn: Callable
    requires: Optional[str] = None


_BASE_COLS = ["oai_identifier", "datestamp", "metadata_format", "sets", "deleted"]

# Possible field name variants for common DC concepts across all schemas
_TITLE      = ("title", "dc.title")
_CREATOR    = ("creator", "dc.creator", "dc.contributor.author", "author")
_CONTRIBUTOR= ("contributor", "dc.contributor")
_DESCRIPTION= ("description", "dc.description", "abstract", "dcterms.abstract", "summary")
_PUBLISHER  = ("publisher", "dc.publisher")
_DATE       = ("date", "dc.date", "dc.date.issued", "date.issued", "dcterms.issued")
_TYPE       = ("type", "dc.type", "typeOfResource", "genre", "dcterms.type")
_SUBJECT    = ("subject", "dc.subject", "subject.topic")
_IDENTIFIER = ("identifier", "dc.identifier", "identifier.uri", "identifier.doi", "location.url")
_LANGUAGE   = ("language", "dc.language")
_RIGHTS     = ("rights", "dc.rights", "accessCondition")
_RELATION   = ("relation", "dc.relation")


def _get(rec: Record, *keys: str) -> list[str]:
    result = []
    for k in keys:
        result.extend(rec.fields.get(k, []))
    return result


# --- JSON ---------------------------------------------------------------

def write_json(records: list[Record], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([r.as_dict() for r in records], f, indent=2, ensure_ascii=False)


# --- JSONL --------------------------------------------------------------

def write_jsonl(records: list[Record], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec.as_dict(), ensure_ascii=False) + "\n")


# --- CSV ----------------------------------------------------------------

def write_csv(records: list[Record], path: str) -> None:
    seen: set[str] = set()
    extra: list[str] = []
    for rec in records:
        for k in rec.fields:
            if k not in seen:
                extra.append(k)
                seen.add(k)
    fieldnames = _BASE_COLS + extra
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow(rec.as_flat_dict())


# --- Excel --------------------------------------------------------------

def write_excel(records: list[Record], path: str) -> None:
    if not _HAS_OPENPYXL:
        raise RuntimeError("openpyxl is required for Excel output — run: poetry add openpyxl")
    seen: set[str] = set()
    extra: list[str] = []
    for rec in records:
        for k in rec.fields:
            if k not in seen:
                extra.append(k)
                seen.add(k)
    fieldnames = _BASE_COLS + extra

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Records"
    ws.append(fieldnames)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for rec in records:
        row = rec.as_flat_dict()
        ws.append([row.get(f, "") for f in fieldnames])
    for col in ws.columns:
        width = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(width + 2, 60)
    wb.save(path)


# --- BibTeX -------------------------------------------------------------

def _bibtex_entry_type(rec: Record) -> str:
    types = [v.lower() for v in _get(rec, *_TYPE)]
    qual  = [v.lower() for v in _get(rec, "degree.level", "qualification.level")]
    both  = types + qual
    if any("doctoral" in v or "phd" in v or "doctor" in v for v in both):
        return "phdthesis"
    if any("master" in v for v in both):
        return "mastersthesis"
    if any("thesis" in v or "dissertation" in v for v in types):
        return "phdthesis"
    if rec.fields.get("journal.title") or any("article" in v for v in types):
        return "article"
    if any("conference" in v or "proceeding" in v for v in types):
        return "inproceedings"
    if any("book chapter" in v or "incollection" in v for v in types):
        return "incollection"
    if any(v == "book" for v in types):
        return "book"
    if any("report" in v for v in types):
        return "techreport"
    return "misc"


def _bibtex_key(rec: Record) -> str:
    creators = _get(rec, *_CREATOR)
    name = "unknown"
    if creators:
        surname = creators[0].split(",")[0].strip()
        name = re.sub(r"[^a-zA-Z]", "", surname) or "unknown"
    dates = _get(rec, *_DATE)
    year = ""
    for d in dates:
        m = re.search(r"\d{4}", d)
        if m:
            year = m.group()
            break
    return f"{name}{year}" if year else name


def _bib_esc(v: str) -> str:
    return v.replace("{", "\\{").replace("}", "\\}")


def write_bibtex(records: list[Record], path: str) -> None:
    lines: list[str] = []
    key_counts: dict[str, int] = {}

    for rec in records:
        if rec.deleted:
            continue
        entry_type = _bibtex_entry_type(rec)
        base_key = _bibtex_key(rec)
        n = key_counts.get(base_key, 0)
        key_counts[base_key] = n + 1
        key = base_key if n == 0 else f"{base_key}{chr(97 + n)}"

        lines.append(f"@{entry_type}{{{key},")

        def field(bib_key: str, *src_keys: str, first_only: bool = True) -> None:
            vals = _get(rec, *src_keys)
            if not vals:
                return
            val = _bib_esc(vals[0]) if first_only else " and ".join(_bib_esc(v) for v in vals)
            lines.append(f"  {bib_key} = {{{val}}},")

        field("title",     *_TITLE)
        # author: join with " and "
        creators = _get(rec, *_CREATOR)
        if creators:
            lines.append(f"  author = {{{' and '.join(_bib_esc(c) for c in creators)}}},")
        field("year",      *_DATE)
        field("publisher", *_PUBLISHER)
        field("abstract",  *_DESCRIPTION)
        field("journal",   "journal.title")
        field("volume",    "journal.volume")
        field("number",    "journal.issue")
        field("pages",     "journal.pages")
        field("school",    "institution", "dc.publisher")
        field("language",  *_LANGUAGE)
        field("rights",    *_RIGHTS)

        urls = [i for i in _get(rec, *_IDENTIFIER) if i.startswith("http")]
        if urls:
            lines.append(f"  url = {{{_bib_esc(urls[0])}}},")
        dois = _get(rec, "identifier.doi", "bibo.doi") or \
               [i for i in _get(rec, *_IDENTIFIER) if i.startswith("10.") or "/doi/" in i]
        if dois:
            lines.append(f"  doi = {{{_bib_esc(dois[0])}}},")

        lines.append("}\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# --- Dublin Core XML ----------------------------------------------------

def write_dcxml(records: list[Record], path: str) -> None:
    DC_URI      = "http://purl.org/dc/elements/1.1/"
    DCTERMS_URI = "http://purl.org/dc/terms/"
    ET.register_namespace("dc",      DC_URI)
    ET.register_namespace("dcterms", DCTERMS_URI)

    root = ET.Element("records")
    for rec in records:
        r = ET.SubElement(root, "record")
        ET.SubElement(r, "oai_identifier").text  = rec.oai_identifier
        ET.SubElement(r, "datestamp").text        = rec.datestamp
        ET.SubElement(r, "metadata_format").text  = rec.metadata_format
        ET.SubElement(r, "sets").text             = " || ".join(rec.sets)
        ET.SubElement(r, "deleted").text          = str(rec.deleted).lower()
        meta = ET.SubElement(r, "metadata")
        for field_key, values in rec.fields.items():
            for val in values:
                if field_key.startswith("dcterms."):
                    el = ET.SubElement(meta, f"{{{DCTERMS_URI}}}{field_key[8:]}")
                elif field_key.startswith("dc."):
                    parts = field_key[3:].split(".", 1)
                    el = ET.SubElement(meta, f"{{{DC_URI}}}{parts[0]}")
                    if len(parts) > 1:
                        el.set("qualifier", parts[1])
                elif "." not in field_key:
                    el = ET.SubElement(meta, f"{{{DC_URI}}}{field_key}")
                else:
                    el = ET.SubElement(meta, re.sub(r"[^a-zA-Z0-9_]", "_", field_key))
                el.text = val

    ET.indent(root, space="  ")
    with open(path, "wb") as f:
        ET.ElementTree(root).write(f, encoding="UTF-8", xml_declaration=True)


# --- MARC21 -------------------------------------------------------------

def _marc_008(rec: Record) -> str:
    today = date.today().strftime("%y%m%d")
    dates = _get(rec, *_DATE)
    year = "    "
    for d in dates:
        m = re.search(r"\d{4}", d)
        if m:
            year = m.group()
            break
    langs = _get(rec, *_LANGUAGE)
    lang = (langs[0][:3] if langs else "   ").ljust(3)
    f = list(" " * 40)
    for i, c in enumerate(today[:6]):
        f[i] = c
    f[6] = "s"
    for i, c in enumerate(year[:4]):
        f[7 + i] = c
    f[15], f[16] = "x", "x"
    for i, c in enumerate(lang[:3]):
        f[35 + i] = c
    f[39] = "d"
    return "".join(f)


def write_marc21(records: list[Record], path: str) -> None:
    if not _HAS_PYMARC:
        raise RuntimeError("pymarc is required for MARC21 output — run: poetry add pymarc")

    with open(path, "wb") as f:
        for rec in records:
            if rec.deleted:
                continue
            marc = MarcRecord()
            marc.leader = "00000nam a2200000 i 4500"
            marc.add_field(Field("008", data=_marc_008(rec)))
            marc.add_field(Field("001", data=rec.oai_identifier))

            titles = _get(rec, *_TITLE)
            if titles:
                marc.add_field(Field("245", ["1", "0"], subfields=["a", titles[0]]))
                for t in titles[1:]:
                    marc.add_field(Field("246", ["1", " "], subfields=["a", t]))

            creators = _get(rec, *_CREATOR)
            for i, c in enumerate(creators):
                marc.add_field(Field("100" if i == 0 else "700", ["1", " "], subfields=["a", c]))

            for c in _get(rec, *_CONTRIBUTOR):
                marc.add_field(Field("700", ["1", " "], subfields=["a", c, "e", "contributor"]))

            for d in _get(rec, *_DESCRIPTION):
                marc.add_field(Field("520", [" ", " "], subfields=["a", d]))

            publishers = _get(rec, *_PUBLISHER)
            dates      = _get(rec, *_DATE)
            if publishers or dates:
                sf: list[str] = []
                if publishers:
                    sf += ["b", publishers[0]]
                if dates:
                    yr = re.search(r"\d{4}", dates[0])
                    if yr:
                        sf += ["c", yr.group()]
                marc.add_field(Field("264", [" ", "1"], subfields=sf))

            for s in _get(rec, *_SUBJECT):
                marc.add_field(Field("650", [" ", "4"], subfields=["a", s]))

            langs = _get(rec, *_LANGUAGE)
            if langs:
                marc.add_field(Field("041", ["0", " "], subfields=["a", langs[0][:3].lower()]))

            for r in _get(rec, *_RIGHTS):
                marc.add_field(Field("540", [" ", " "], subfields=["a", r]))

            for t in _get(rec, *_TYPE):
                marc.add_field(Field("655", [" ", "4"], subfields=["a", t]))

            for ident in _get(rec, *_IDENTIFIER):
                if ident.startswith("http"):
                    marc.add_field(Field("856", ["4", "0"], subfields=["u", ident]))
                elif ident.startswith("10.") or "/doi/" in ident:
                    marc.add_field(Field("024", ["7", " "], subfields=["a", ident, "2", "doi"]))
                else:
                    marc.add_field(Field("035", [" ", " "], subfields=["a", ident]))

            for rel in _get(rec, *_RELATION):
                marc.add_field(Field("787", ["1", " "], subfields=["t", rel]))

            f.write(marc.as_marc())


# --- RDF graph (shared by Turtle and JSON-LD) ---------------------------

def _build_graph(records: list[Record]) -> "Graph":
    DC_NS    = Namespace("http://purl.org/dc/elements/1.1/")
    DCTERMS  = Namespace("http://purl.org/dc/terms/")
    BIBO     = Namespace("http://purl.org/ontology/bibo/")
    LOCAL    = Namespace("http://purl.org/oai-harvester/terms/")
    _DC_SIMPLE = {"title", "creator", "subject", "description", "publisher",
                  "contributor", "date", "type", "format", "identifier",
                  "source", "language", "relation", "coverage", "rights"}

    def predicate(key: str) -> URIRef:
        if key in _DC_SIMPLE:
            return DC_NS[key]
        if key.startswith("dcterms."):
            return DCTERMS[key[8:]]
        if key.startswith("bibo."):
            return BIBO[key[5:]]
        if key.startswith("dc."):
            parts = key[3:].split(".")
            return DC_NS[parts[0]] if len(parts) == 1 else DCTERMS[parts[0]]
        return LOCAL[re.sub(r"[^a-zA-Z0-9]", "_", key)]

    g = Graph()
    g.bind("dc",      DC_NS)
    g.bind("dcterms", DCTERMS)
    g.bind("bibo",    BIBO)
    g.bind("oaih",    LOCAL)

    for rec in records:
        if rec.deleted:
            continue
        url_ids = [v for v in _get(rec, *_IDENTIFIER) if v.startswith("http")]
        subj = URIRef(url_ids[0]) if url_ids else URIRef(f"urn:{rec.oai_identifier}")
        g.add((subj, rdflib.RDF.type,   DCTERMS.BibliographicResource))
        g.add((subj, LOCAL.oaiIdentifier, Literal(rec.oai_identifier)))
        g.add((subj, LOCAL.datestamp,     Literal(rec.datestamp)))
        for field_key, values in rec.fields.items():
            pred = predicate(field_key)
            for val in values:
                g.add((subj, pred, Literal(val)))

    return g


# --- Turtle -------------------------------------------------------------

def write_turtle(records: list[Record], path: str) -> None:
    if not _HAS_RDFLIB:
        raise RuntimeError("rdflib is required for Turtle output — run: poetry add rdflib")
    _build_graph(records).serialize(destination=path, format="turtle")


# --- JSON-LD ------------------------------------------------------------

def write_jsonld(records: list[Record], path: str) -> None:
    if not _HAS_RDFLIB:
        raise RuntimeError("rdflib is required for JSON-LD output — run: poetry add rdflib")
    _build_graph(records).serialize(destination=path, format="json-ld", indent=2)


# --- Registry -----------------------------------------------------------

WRITERS: list[WriterSpec] = [
    WriterSpec("json",   "JSON array",                              ".json",   write_json),
    WriterSpec("jsonl",  "Newline-delimited JSON",                  ".jsonl",  write_jsonl),
    WriterSpec("csv",    "CSV",                                     ".csv",    write_csv),
    WriterSpec("excel",  "Excel workbook",                          ".xlsx",   write_excel,  "openpyxl"),
    WriterSpec("bibtex", "BibTeX",                                  ".bib",    write_bibtex),
    WriterSpec("marc21", "MARC21 binary",                           ".mrc",    write_marc21, "pymarc"),
    WriterSpec("dcxml",  "Dublin Core XML",                         ".xml",    write_dcxml),
    WriterSpec("turtle", "RDF Turtle",                              ".ttl",    write_turtle, "rdflib"),
    WriterSpec("jsonld", "JSON-LD",                                 ".jsonld", write_jsonld, "rdflib"),
]
WRITER_REGISTRY: dict[str, WriterSpec] = {w.name: w for w in WRITERS}
