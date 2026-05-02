# OAI Harvester

A command-line tool for harvesting metadata records from [OAI-PMH](https://www.openarchives.org/pmh/) repositories. Compatible with **DSpace**, **EPrints**, and any other OAI-PMH compliant system including arXiv, Europe PubMed Central, and EThOS.

> **Disclaimer:** This software is provided as-is, without warranty of any kind, express or implied. Use at your own risk.

## Requirements

- Python 3.11+
- [Poetry](https://python-poetry.org/)

---

## Setting up Python and Poetry

### Windows

1. **Install Python** from [python.org](https://www.python.org/downloads/). During installation, check **"Add Python to PATH"**.

2. **Verify Python**:
   ```powershell
   python --version
   ```

3. **Install Poetry** using PowerShell:
   ```powershell
   (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
   ```

4. **Add Poetry to your PATH** (if not done automatically). Add the following to your system environment variables:
   ```
   %APPDATA%\Python\Scripts
   ```

5. **Verify Poetry**:
   ```powershell
   poetry --version
   ```

---

### macOS

1. **Install Python**. The recommended way is via [Homebrew](https://brew.sh/):
   ```bash
   brew install python@3.11
   ```
   Or download directly from [python.org](https://www.python.org/downloads/).

2. **Verify Python**:
   ```bash
   python3 --version
   ```

3. **Install Poetry**:
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

4. **Add Poetry to your PATH** by adding this line to your `~/.zshrc` (or `~/.bash_profile` if using bash):
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```
   Then reload your shell:
   ```bash
   source ~/.zshrc
   ```

5. **Verify Poetry**:
   ```bash
   poetry --version
   ```

---

### Linux (Ubuntu / Debian / Kubuntu)

1. **Install Python**:
   ```bash
   sudo apt update
   sudo apt install python3.11 python3.11-venv python3-pip
   ```

2. **Verify Python**:
   ```bash
   python3.11 --version
   ```

3. **Install pipx** (recommended way to install Poetry on Linux):
   ```bash
   sudo apt install pipx
   pipx ensurepath
   ```

4. **Install Poetry via pipx**:
   ```bash
   pipx install poetry
   ```

5. **Verify Poetry**:
   ```bash
   poetry --version
   ```

---

## Installing the harvester

Once Python and Poetry are set up on your system:

```bash
git clone https://github.com/yourusername/oai-harvester.git
cd oai-harvester
poetry install
```

## Usage

### Interactive mode

Run without arguments to be prompted for the base URL, metadata schema, and output format:

```bash
poetry run oai-harvest
```

Example session:

```
OAI-PMH base URL: https://dspace.example.org/oai/request

Metadata schema (compatible with DSpace, EPrints, and other OAI-PMH systems):
   1. oai_dc    — Dublin Core  [all platforms]  (default)
   2. dim       — DSpace Intermediate Metadata  [DSpace]
   3. qdc       — Qualified Dublin Core  [DSpace / EPrints]
   4. ext_dc    — Extended Dublin Core  [DSpace]
   5. xoai      — Extended OAI  [DSpace]
   6. etdms     — ETD Metadata Standard — theses  [DSpace / EPrints]
   7. mets      — METS  [DSpace]
   8. ore       — Object Reuse and Exchange (ORE)  [DSpace / EPrints]
   9. rdf       — RDF/XML  [EPrints]
  10. mods      — MODS — Metadata Object Description Schema  [EPrints / general]
  11. uketd_dc  — UK ETD Dublin Core  [EPrints / EThOS]
Select [1-11] (default: 1): 2

Output format [json/csv] (default: json): csv
```

### Command-line mode

```bash
poetry run oai-harvest <base_url> [options]
```

#### Options

| Option | Description |
|---|---|
| `--schema SCHEMA` | Metadata schema (default: `oai_dc`) |
| `--set SETSPEC` | Restrict harvest to a specific set |
| `--from YYYY-MM-DD` | Harvest records from this date |
| `--until YYYY-MM-DD` | Harvest records until this date |
| `-o`, `--output FILE` | Output file path (default: `OAI_<schema>_<datetime>`) |
| `-f`, `--format` | Output format: `json` or `csv` (default: `json`) |
| `--delay SECS` | Crawl delay between requests in seconds (default: `10`) |
| `--skip-deleted` | Exclude deleted records from output |
| `--identify` | Print repository information and exit |
| `--list-sets` | List available sets and exit |

### Examples

#### DSpace

```bash
# Inspect a DSpace repository
poetry run oai-harvest https://dspace.example.org/oai/request --identify

# List available sets (collections and communities)
poetry run oai-harvest https://dspace.example.org/oai/request --list-sets

# Harvest using DSpace Intermediate Metadata, output as CSV
poetry run oai-harvest https://dspace.example.org/oai/request --schema dim -f csv

# Harvest a specific collection, date range, custom output path
poetry run oai-harvest https://dspace.example.org/oai/request \
  --schema dim \
  --set publications \
  --from 2023-01-01 \
  --until 2023-12-31 \
  -f csv \
  -o my_harvest
```

#### EPrints

```bash
# Inspect an EPrints repository
poetry run oai-harvest https://eprints.example.org/cgi/oai2 --identify

# Harvest using EPrints native RDF format
poetry run oai-harvest https://eprints.example.org/cgi/oai2 --schema rdf -f json

# Harvest UK theses using UK ETD Dublin Core
poetry run oai-harvest https://eprints.example.org/cgi/oai2 --schema uketd_dc -f csv
```

#### General OAI-PMH

```bash
# Harvest from arXiv
poetry run oai-harvest https://export.arxiv.org/oai2 --schema oai_dc -f csv

# Harvest from Europe PubMed Central
poetry run oai-harvest https://europepmc.org/oai.cgi --schema oai_dc -f json
```

## Supported Metadata Schemas

### All platforms

| Schema | Description |
|---|---|
| `oai_dc` | Dublin Core — 15 standard elements, supported by every OAI-PMH repository |

### DSpace

| Schema | Description |
|---|---|
| `dim` | DSpace Intermediate Metadata — full qualified DC in dot notation (e.g. `dc.contributor.author`) |
| `ext_dc` | Extended Dublin Core — DC elements plus DCterms, with `dcterms.` prefix |
| `qdc` | Qualified Dublin Core — DC elements plus DCterms |
| `xoai` | Extended OAI — includes bitstream metadata |
| `mets` | METS — descriptive metadata plus bitstream file paths and MIME types |
| `ore` | Object Reuse and Exchange — Atom-based with bitstream aggregation links |
| `etdms` | ETD Metadata Standard — thesis/dissertation fields including degree information |

### EPrints

| Schema | Description |
|---|---|
| `rdf` | RDF/XML — rich EPrints-native format including BIBO, DCterms, and bitstream URLs |
| `mods` | MODS — full bibliographic detail including journal, volume, issue, and page fields |
| `uketd_dc` | UK ETD Dublin Core — UK thesis format with institution, advisor, qualification, and embargo fields |
| `qdc` | Qualified Dublin Core — also supported by EPrints |
| `ore` | Object Reuse and Exchange — also supported by EPrints 3.3+ |
| `etdms` | ETD Metadata Standard — also supported by EPrints thesis repositories |

## Repository Endpoints

### DSpace

| Version | OAI-PMH endpoint path |
|---|---|
| DSpace 5 / 6 | `https://your-repo.org/oai/request` |
| DSpace 7 | `https://your-repo.org/server/oai/request` |

### EPrints

| Version | OAI-PMH endpoint path |
|---|---|
| EPrints 3.x | `https://your-repo.org/cgi/oai2` |

### Public endpoints

| Repository | Base URL |
|---|---|
| Europe PubMed Central | `https://europepmc.org/oai.cgi` |
| arXiv | `https://export.arxiv.org/oai2` |
| EThOS (British Library) | `https://ethos.bl.uk/OAIHandler` |

## Output

Output files are named `OAI_<schema>_<datetime>.<ext>` by default, for example:

```
OAI_dim_2026-05-02T143022.csv
OAI_rdf_2026-05-02T143022.json
```

### Supported output formats

| Format | Flag | Extension | Notes |
|---|---|---|---|
| JSON | `json` | `.json` | JSON array, one object per record |
| Newline-delimited JSON | `jsonl` | `.jsonl` | One JSON object per line — better for large harvests |
| CSV | `csv` | `.csv` | Multi-value fields separated by ` \|\| ` |
| Excel | `excel` | `.xlsx` | Bold header row, auto-sized columns |
| BibTeX | `bibtex` | `.bib` | Entry type inferred from record type/degree fields |
| MARC21 | `marc21` | `.mrc` | Binary MARC21 — suitable for import into library systems |
| Dublin Core XML | `dcxml` | `.xml` | Structured XML with DC/DCterms namespaces |
| RDF Turtle | `turtle` | `.ttl` | Linked data, DC/DCterms/BIBO predicates |
| JSON-LD | `jsonld` | `.jsonld` | Linked data in JSON format |

Excel requires `openpyxl`, MARC21 requires `pymarc`, and Turtle/JSON-LD require `rdflib` — all installed automatically by `poetry install`.

### JSON example

```json
{
  "oai_identifier": "oai:example.org:123",
  "datestamp": "2024-01-01",
  "metadata_format": "dim",
  "sets": ["publications"],
  "deleted": false,
  "fields": {
    "dc.title": ["My Article"],
    "dc.contributor.author": ["Smith, J.", "Jones, A."],
    "dc.date.issued": ["2024"]
  }
}
```

### CSV

Each row is one record. Multi-value fields are separated by ` || ` within a single cell.

## Running Tests

```bash
poetry run pytest
```
