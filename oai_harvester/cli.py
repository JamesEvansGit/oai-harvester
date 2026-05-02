import argparse
import sys
from datetime import datetime

from .formats import FORMATS, REGISTRY
from .harvester import OAIError, OAIHarvester
from .models import Record
from .writers import WRITER_REGISTRY, WRITERS


def _default_output(schema: str, fmt: str) -> str:
    ts = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    ext = WRITER_REGISTRY[fmt].ext
    return f"OAI_{schema}_{ts}{ext}"


def _prompt_schema() -> str:
    print("\nMetadata schema (compatible with DSpace, EPrints, and other OAI-PMH systems):")
    for i, fmt in enumerate(FORMATS, 1):
        default_tag = "  (default)" if fmt.SCHEMA == "oai_dc" else ""
        print(f"  {i:2}. {fmt.SCHEMA:<10} — {fmt.LABEL}{default_tag}")
    while True:
        try:
            raw = input(f"Select [1-{len(FORMATS)}] (default: 1): ").strip()
        except EOFError:
            return "oai_dc"
        if not raw:
            return "oai_dc"
        if raw.isdigit() and 1 <= int(raw) <= len(FORMATS):
            return FORMATS[int(raw) - 1].SCHEMA
        if raw in REGISTRY:
            return raw
        print(f"  Please enter a number between 1 and {len(FORMATS)}.")


def _prompt_output_format() -> str:
    print("\nOutput format:")
    for i, w in enumerate(WRITERS, 1):
        default_tag = "  (default)" if w.name == "json" else ""
        req = f"  [requires: {w.requires}]" if w.requires else ""
        print(f"  {i:2}. {w.name:<8} — {w.label}{req}{default_tag}")
    while True:
        try:
            raw = input(f"Select [1-{len(WRITERS)}] (default: 1): ").strip()
        except EOFError:
            return "json"
        if not raw:
            return "json"
        if raw.isdigit() and 1 <= int(raw) <= len(WRITERS):
            return WRITERS[int(raw) - 1].name
        if raw in WRITER_REGISTRY:
            return raw
        print(f"  Please enter a number between 1 and {len(WRITERS)}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="oai-harvest",
        description="Harvest OAI-PMH records from DSpace, EPrints, and other OAI-PMH systems.",
    )
    parser.add_argument("base_url", nargs="?", help="OAI-PMH base URL (prompted if omitted)")
    parser.add_argument("--schema", choices=list(REGISTRY), default=None,
                        help="Metadata schema (default: oai_dc)")
    parser.add_argument("--set", dest="set_spec", metavar="SETSPEC", help="Restrict to a set")
    parser.add_argument("--from", dest="from_date", metavar="YYYY-MM-DD")
    parser.add_argument("--until", dest="until_date", metavar="YYYY-MM-DD")
    parser.add_argument("-o", "--output", default=None,
                        help="Output file path (default: OAI_<schema>_<datetime>.<ext>)")
    parser.add_argument("-f", "--format", choices=list(WRITER_REGISTRY), default=None,
                        help="Output format (default: json)")
    parser.add_argument("--delay", type=float, default=10, metavar="SECS")
    parser.add_argument("--skip-deleted", action="store_true")
    parser.add_argument("--identify", action="store_true", help="Print repository info and exit")
    parser.add_argument("--list-sets", action="store_true", help="Print available sets and exit")

    args = parser.parse_args()

    base_url = args.base_url
    schema   = args.schema
    fmt      = args.format

    if not base_url:
        try:
            base_url = input("OAI-PMH base URL: ").strip()
            if not schema:
                schema = _prompt_schema()
            if not fmt:
                fmt = _prompt_output_format()
        except EOFError:
            sys.exit("No URL provided.")

    if not base_url:
        sys.exit("No URL provided.")

    schema = schema or "oai_dc"
    fmt    = fmt    or "json"

    harvester = OAIHarvester(base_url, delay=args.delay)

    if args.identify:
        try:
            info = harvester.identify()
        except OAIError as e:
            sys.exit(f"Error: {e}")
        for k, v in info.items():
            print(f"{k}: {v}")
        return

    if args.list_sets:
        try:
            sets = harvester.list_sets()
        except OAIError as e:
            sys.exit(f"Error: {e}")
        if not sets:
            print("No sets available.")
            return
        for s in sets:
            print(f"{s['setSpec']}\t{s['setName']}")
        return

    print(f"Harvesting {base_url} [{schema}]", file=sys.stderr)

    records: list[Record] = []
    try:
        for rec in harvester.harvest(
            set_spec=args.set_spec,
            from_date=args.from_date,
            until_date=args.until_date,
            metadata_prefix=schema,
        ):
            if args.skip_deleted and rec.deleted:
                continue
            records.append(rec)
            if len(records) % 500 == 0:
                print(f"  {len(records)} records...", file=sys.stderr)
    except OAIError as e:
        sys.exit(f"OAI error: {e}")
    except KeyboardInterrupt:
        print(f"\nInterrupted — saving {len(records)} records.", file=sys.stderr)

    print(f"Total: {len(records)} records", file=sys.stderr)

    writer = WRITER_REGISTRY[fmt]
    out = args.output or _default_output(schema, fmt)
    if "." not in out.rsplit("/", 1)[-1]:
        out += writer.ext

    try:
        writer.fn(records, out)
    except RuntimeError as e:
        sys.exit(str(e))

    print(f"Written to {out}", file=sys.stderr)
