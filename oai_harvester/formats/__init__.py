from . import dim, etdms, ext_dc, mets, mods, oai_dc, ore, qdc, rdf, uketd_dc, xoai

# Ordered as shown in the CLI numbered list
FORMATS = [oai_dc, dim, qdc, ext_dc, xoai, etdms, mets, ore, rdf, mods, uketd_dc]
REGISTRY = {f.SCHEMA: f for f in FORMATS}
