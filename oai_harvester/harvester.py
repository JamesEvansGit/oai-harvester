import time
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from typing import Optional

import requests

from .formats import REGISTRY
from .models import Record

OAI_NS = "http://www.openarchives.org/OAI/2.0/"


def _oai(tag: str) -> str:
    return f"{{{OAI_NS}}}{tag}"


def _text(el: ET.Element, tag: str) -> str:
    found = el.find(tag)
    return (found.text or "").strip() if found is not None else ""


class OAIError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"[{code}] {message}")


class OAIHarvester:
    def __init__(
        self,
        base_url: str,
        delay: float = 10,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.base_url = base_url.rstrip("?")
        self.delay = delay
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "oai-harvester/0.1"
        adapter = requests.adapters.HTTPAdapter(max_retries=max_retries)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self._timeout = timeout

    def _get(self, **params) -> ET.Element:
        resp = self.session.get(self.base_url, params=params, timeout=self._timeout)
        if resp.status_code == 503:
            retry_after = float(resp.headers.get("Retry-After", 60))
            time.sleep(retry_after)
            resp = self.session.get(self.base_url, params=params, timeout=self._timeout)
        resp.raise_for_status()
        return ET.fromstring(resp.content)

    @staticmethod
    def _check_errors(root: ET.Element, ignore: tuple[str, ...] = ()) -> None:
        for err in root.iter(_oai("error")):
            code = err.get("code", "unknown")
            if code in ignore:
                return
            raise OAIError(code, (err.text or "").strip())

    def identify(self) -> dict[str, str]:
        root = self._get(verb="Identify")
        self._check_errors(root)
        result = {}
        el = root.find(_oai("Identify"))
        if el is not None:
            for child in el:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                result[tag] = (child.text or "").strip()
        return result

    def list_sets(self) -> list[dict[str, str]]:
        sets: list[dict[str, str]] = []
        token: Optional[str] = None
        while True:
            params: dict = {"verb": "ListSets"}
            if token:
                params["resumptionToken"] = token
            root = self._get(**params)
            self._check_errors(root, ignore=("noSetHierarchy",))
            for s in root.iter(_oai("set")):
                sets.append({
                    "setSpec": _text(s, _oai("setSpec")),
                    "setName": _text(s, _oai("setName")),
                })
            rt = root.find(f".//{_oai('resumptionToken')}")
            if rt is None or not (rt.text or "").strip():
                break
            token = rt.text.strip()
            time.sleep(self.delay)
        return sets

    def harvest(
        self,
        set_spec: Optional[str] = None,
        from_date: Optional[str] = None,
        until_date: Optional[str] = None,
        metadata_prefix: str = "oai_dc",
    ) -> Iterator[Record]:
        parser = REGISTRY.get(metadata_prefix)
        token: Optional[str] = None

        while True:
            if token:
                params: dict = {"verb": "ListRecords", "resumptionToken": token}
            else:
                params = {
                    "verb": "ListRecords",
                    "metadataPrefix": metadata_prefix,
                    **({"set": set_spec} if set_spec else {}),
                    **({"from": from_date} if from_date else {}),
                    **({"until": until_date} if until_date else {}),
                }

            root = self._get(**params)
            self._check_errors(root, ignore=("noRecordsMatch",))

            list_records = root.find(_oai("ListRecords"))
            if list_records is None:
                break

            for record_el in list_records.findall(_oai("record")):
                yield self._parse_record(record_el, metadata_prefix, parser)

            rt = list_records.find(_oai("resumptionToken"))
            if rt is None or not (rt.text or "").strip():
                break
            token = rt.text.strip()
            time.sleep(self.delay)

    @staticmethod
    def _parse_record(record_el: ET.Element, metadata_prefix: str = "oai_dc", parser=None) -> Record:
        header = record_el.find(_oai("header"))
        assert header is not None

        rec = Record(
            oai_identifier=_text(header, _oai("identifier")),
            datestamp=_text(header, _oai("datestamp")),
            metadata_format=metadata_prefix,
            sets=[s.text.strip() for s in header.findall(_oai("setSpec")) if s.text],
            deleted=header.get("status") == "deleted",
        )

        if not rec.deleted and parser is not None:
            metadata = record_el.find(_oai("metadata"))
            if metadata is not None:
                rec.fields = parser.parse_metadata(metadata)

        return rec
