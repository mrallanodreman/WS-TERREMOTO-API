from app.modules.webhook.features.personas import messages
from app.modules.webhook.features.personas.enums import PersonStatus
from app.modules.webhook.features.personas.mapper import to_person_dto
from app.modules.webhook.features.personas.presenter import render_people
from app.modules.webhook.features.personas.repository import StubPersonRepository


def test_search_by_name():
    results = StubPersonRepository().search("maria")
    assert len(results) == 1
    assert results[0].full_name == "Maria Perez"
    assert results[0].status == PersonStatus.SAFE


def test_search_by_national_id():
    results = StubPersonRepository().search("V87654321")
    assert len(results) == 1
    assert results[0].status == PersonStatus.MISSING


def test_search_empty_query():
    assert StubPersonRepository().search("   ") == []


def test_mapper_unknown_status_and_empty_fields():
    dto = to_person_dto({"name": "Sin Estado", "id": "", "state": "raro", "place": ""}, "api")
    assert dto.status == PersonStatus.UNKNOWN
    assert dto.national_id is None
    assert dto.location is None
    assert dto.source == "api"


def test_render_people_with_results():
    dtos = StubPersonRepository().search("ana")
    text = render_people(dtos)
    assert "Ana Rodriguez" in text
    assert "Albergue Sur" in text


def test_render_people_no_results():
    assert render_people([]) == messages.NO_RESULTS
