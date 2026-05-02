import textwrap
import responses as resp_mock
import pytest
from oai_harvester import OAIHarvester
from oai_harvester.harvester import OAIError

BASE = "https://example.org/oai"

IDENTIFY_XML = textwrap.dedent("""\
    <?xml version="1.0"?>
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
      <Identify>
        <repositoryName>Test Repo</repositoryName>
        <baseURL>https://example.org/oai</baseURL>
        <protocolVersion>2.0</protocolVersion>
        <adminEmail>admin@example.org</adminEmail>
      </Identify>
    </OAI-PMH>
""")

LIST_RECORDS_XML = textwrap.dedent("""\
    <?xml version="1.0"?>
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
      <ListRecords>
        <record>
          <header>
            <identifier>oai:example.org:1</identifier>
            <datestamp>2024-01-01</datestamp>
          </header>
          <metadata>
            <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
                       xmlns:dc="http://purl.org/dc/elements/1.1/">
              <dc:title>A Test Record</dc:title>
              <dc:creator>Smith, J</dc:creator>
              <dc:date>2024</dc:date>
              <dc:identifier>https://example.org/item/1</dc:identifier>
            </oai_dc:dc>
          </metadata>
        </record>
        <record>
          <header status="deleted">
            <identifier>oai:example.org:2</identifier>
            <datestamp>2024-01-02</datestamp>
          </header>
        </record>
      </ListRecords>
    </OAI-PMH>
""")

DIM_RECORDS_XML = textwrap.dedent("""\
    <?xml version="1.0"?>
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
      <ListRecords>
        <record>
          <header>
            <identifier>oai:example.org:3</identifier>
            <datestamp>2024-01-03</datestamp>
          </header>
          <metadata>
            <dim:dim xmlns:dim="http://www.dspace.org/xmlns/dspace/dim">
              <dim:field schema="dc" element="title">DIM Title</dim:field>
              <dim:field schema="dc" element="contributor" qualifier="author">Jones, A</dim:field>
              <dim:field schema="dc" element="date" qualifier="issued">2024-03</dim:field>
            </dim:dim>
          </metadata>
        </record>
      </ListRecords>
    </OAI-PMH>
""")


@resp_mock.activate
def test_identify():
    resp_mock.add(resp_mock.GET, BASE, body=IDENTIFY_XML)
    h = OAIHarvester(BASE)
    info = h.identify()
    assert info["repositoryName"] == "Test Repo"
    assert info["protocolVersion"] == "2.0"


@resp_mock.activate
def test_harvest_oai_dc():
    resp_mock.add(resp_mock.GET, BASE, body=LIST_RECORDS_XML)
    h = OAIHarvester(BASE, delay=0)
    records = list(h.harvest())
    assert len(records) == 2

    live = records[0]
    assert live.oai_identifier == "oai:example.org:1"
    assert live.metadata_format == "oai_dc"
    assert live.fields["title"] == ["A Test Record"]
    assert live.fields["creator"] == ["Smith, J"]
    assert live.fields["identifier"] == ["https://example.org/item/1"]
    assert not live.deleted

    deleted = records[1]
    assert deleted.deleted
    assert deleted.fields == {}


@resp_mock.activate
def test_harvest_dim():
    resp_mock.add(resp_mock.GET, BASE, body=DIM_RECORDS_XML)
    h = OAIHarvester(BASE, delay=0)
    records = list(h.harvest(metadata_prefix="dim"))
    assert len(records) == 1

    rec = records[0]
    assert rec.metadata_format == "dim"
    assert rec.fields["dc.title"] == ["DIM Title"]
    assert rec.fields["dc.contributor.author"] == ["Jones, A"]
    assert rec.fields["dc.date.issued"] == ["2024-03"]


@resp_mock.activate
def test_harvest_skip_deleted():
    resp_mock.add(resp_mock.GET, BASE, body=LIST_RECORDS_XML)
    h = OAIHarvester(BASE, delay=0)
    records = [r for r in h.harvest() if not r.deleted]
    assert len(records) == 1


@resp_mock.activate
def test_oai_error_raises():
    error_xml = textwrap.dedent("""\
        <?xml version="1.0"?>
        <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
          <error code="badVerb">Illegal OAI verb</error>
        </OAI-PMH>
    """)
    resp_mock.add(resp_mock.GET, BASE, body=error_xml)
    h = OAIHarvester(BASE, delay=0)
    with pytest.raises(OAIError) as exc_info:
        list(h.harvest())
    assert exc_info.value.code == "badVerb"
