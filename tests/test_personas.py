from typing import Any

import httpx
import pytest

from app.modules.webhook.conversation.contracts import FeatureTurn
from app.modules.webhook.features.personas import messages
from app.modules.webhook.features.personas.enums import PersonStatus, ReportType
from app.modules.webhook.features.personas.feature import PersonasFeature
from app.modules.webhook.features.personas.mapper import to_person_dto
from app.modules.webhook.features.personas.presenter import render_people
from app.modules.webhook.features.personas.repository import (
    PersonSearchUnavailable,
    ReportsPersonRepository,
    StubPersonRepository,
)

_MISSING_ROW = {
    "id": "u-1",
    "name": "Jose Gonzalez",
    "status": PersonStatus.LOOKING_FOR_SOMEONE.value,
    "city": "La Guaira",
    "source": "socio-x",
    "source_url": "https://socio-x/r/1",
}
_CHECKIN_SAFE = {
    "id": "u-2",
    "name": "Maria Perez",
    "status": PersonStatus.SAFE.value,
    "place_name": "Refugio Norte",
}
_CHECKIN_OTHER = {"id": "u-3", "name": "Pedro Lopez", "status": PersonStatus.SAFE.value}


def _client(routes: dict[str, Any]) -> httpx.Client:
    """Construye un httpx.Client que responde según `routes[type] -> [páginas]`."""

    def handler(request: httpx.Request) -> httpx.Response:
        report_type = request.url.params["type"]
        since = request.url.params.get("since")
        pages = routes.get(report_type, [{"reports": [], "next_cursor": None}])
        page = pages[0] if since is None else pages[1]
        return httpx.Response(200, json=page)

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="https://hub.test")


# ── Stub ────────────────────────────────────────────────────────────────────

def test_stub_search_by_name():
    results = StubPersonRepository().search("maria")
    assert len(results) == 1
    assert results[0].full_name == "Maria Perez"
    assert results[0].status == PersonStatus.SAFE


def test_stub_search_empty_query():
    assert StubPersonRepository().search("   ") == []


# ── Mapper ────────────────────────────────────────────────────────────────────

def test_mapper_maps_status_and_prefers_place_name():
    dto = to_person_dto(_MISSING_ROW)
    assert dto.status == PersonStatus.LOOKING_FOR_SOMEONE
    assert dto.location == "La Guaira"
    assert dto.report_id == "u-1"
    assert dto.source_url == "https://socio-x/r/1"


def test_mapper_unknown_status_and_empty_fields():
    dto = to_person_dto({"name": "Sin Estado", "status": "raro"})
    assert dto.status == PersonStatus.UNKNOWN
    assert dto.location is None
    assert dto.source is None


# ── Repositorio real (hub) ────────────────────────────────────────────────────

def test_reports_repo_combines_types_and_filters_by_name():
    routes = {
        ReportType.MISSING_PERSON.value: [{"reports": [_MISSING_ROW], "next_cursor": None}],
        ReportType.CHECKIN.value: [
            {"reports": [_CHECKIN_SAFE, _CHECKIN_OTHER], "next_cursor": None}
        ],
    }
    repo = ReportsPersonRepository(client=_client(routes))
    results = repo.search("o")  # coincide con Jose Gonzalez y Pedro Lopez
    names = sorted(p.full_name for p in results)
    assert names == ["Jose Gonzalez", "Pedro Lopez"]


def test_reports_repo_follows_cursor_until_exhausted():
    routes = {
        ReportType.MISSING_PERSON.value: [
            {"reports": [_MISSING_ROW], "next_cursor": "created|u-1"},
            {"reports": [{"id": "u-9", "name": "Jose Mata", "status": "SAFE"}],
             "next_cursor": None},
        ],
        ReportType.CHECKIN.value: [{"reports": [], "next_cursor": None}],
    }
    repo = ReportsPersonRepository(client=_client(routes), max_pages=3)
    results = repo.search("jose")
    assert sorted(p.full_name for p in results) == ["Jose Gonzalez", "Jose Mata"]


def test_reports_repo_empty_query_skips_http():
    repo = ReportsPersonRepository(client=_client({}))
    assert repo.search("  ") == []


def test_reports_repo_raises_on_http_error():
    def handler(_request):
        return httpx.Response(503, json={"error": "down"})

    client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://hub.test"
    )
    repo = ReportsPersonRepository(client=client)
    with pytest.raises(PersonSearchUnavailable):
        repo.search("maria")


# ── Presenter ─────────────────────────────────────────────────────────────────

def test_render_people_with_results():
    text = render_people([to_person_dto(_MISSING_ROW)])
    assert "Jose Gonzalez" in text
    assert messages.STATUS_LOOKING_FOR_SOMEONE in text
    assert "La Guaira" in text
    assert "socio-x" in text


def test_render_people_no_results():
    assert render_people([]) == messages.NO_RESULTS


# ── Feature ───────────────────────────────────────────────────────────────────

def test_feature_handle_renders_results():
    repo = ReportsPersonRepository(
        client=_client(
            {ReportType.MISSING_PERSON.value: [{"reports": [_MISSING_ROW], "next_cursor": None}]}
        )
    )
    reply = PersonasFeature(repositories=(repo,)).handle(FeatureTurn(text="jose"))
    assert reply.done is True
    assert "Jose Gonzalez" in reply.text


def test_feature_handle_reports_unavailable_source():
    class _Down:
        source = "down"

        def search(self, query):
            raise PersonSearchUnavailable("boom")

    reply = PersonasFeature(repositories=(_Down(),)).handle(FeatureTurn(text="x"))
    assert reply.text == messages.SERVICE_UNAVAILABLE
    assert reply.done is True
