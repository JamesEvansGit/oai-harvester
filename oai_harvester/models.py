from dataclasses import dataclass, field


@dataclass
class Record:
    oai_identifier: str
    datestamp: str
    metadata_format: str = "oai_dc"
    sets: list[str] = field(default_factory=list)
    deleted: bool = False
    fields: dict[str, list[str]] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "oai_identifier": self.oai_identifier,
            "datestamp": self.datestamp,
            "metadata_format": self.metadata_format,
            "sets": self.sets,
            "deleted": self.deleted,
            "fields": self.fields,
        }

    def as_flat_dict(self, separator: str = " || ") -> dict:
        d: dict = {
            "oai_identifier": self.oai_identifier,
            "datestamp": self.datestamp,
            "metadata_format": self.metadata_format,
            "sets": separator.join(self.sets),
            "deleted": self.deleted,
        }
        for k, v in self.fields.items():
            d[k] = separator.join(v)
        return d
