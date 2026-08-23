"""End-to-end HTTP tests for the Stage 1 content site + contact form."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.settings import settings
from app.main import app


@pytest.fixture(autouse=True)
def _local_sink(tmp_path, monkeypatch):
    # Keep persistence local + isolated; never touch the repo's ./data dir.
    monkeypatch.setattr(settings, "contact_sink", "sqlite", raising=False)
    monkeypatch.setattr(settings, "contact_db_path", str(tmp_path / "contact.sqlite3"), raising=False)


@pytest.fixture
def client():
    return TestClient(app)


def _get_form(client):
    """GET contact, return the CSRF token (cookies stay on the client)."""
    r = client.get("/contato")
    assert r.status_code == 200
    m = re.search(r'name="csrf_token" value="([^"]+)"', r.text)
    assert m, "CSRF token not found in rendered form"
    return m.group(1)


def _valid_payload(token):
    return {
        "csrf_token": token,
        "full_name": "João da Silva",
        "company": "Empresa Exemplo Ltda.",
        "email": "contato@empresa.com.br",
        "phone": "(11) 99999-0000",
        "location": "São Paulo – SP",
        "solution": "Automação de processos",
        "project_stage": "Tenho apenas uma ideia",
        "need": "Precisamos automatizar o faturamento mensal, hoje feito à mão.",
        "priority": "Alta — preciso iniciar o quanto antes",
        "deadline": "Gostaria de iniciar em até 30 dias.",
        "contact_preference": "WhatsApp",
        "best_time": "Manhã",
        "consent": "on",
    }


# --- Content rendering ----------------------------------------------------
def test_home_renders_verbatim_company_copy(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'id="home"' in r.text
    assert "Somos uma empresa de tecnologia focada no desenvolvimento de sistemas" in r.text
    assert 'id="quem-somos"' not in r.text


def test_company_is_a_separate_full_page(client):
    r = client.get("/quem-somos")
    assert r.status_code == 200
    assert 'id="quem-somos"' in r.text
    assert "Missão" in r.text and "Visão" in r.text and "Propósito" in r.text
    assert "<!DOCTYPE html>" in r.text


@pytest.mark.parametrize("path, marker", [
    ("/", 'id="home"'),
    ("/quem-somos", 'id="quem-somos"'),
    ("/produtos", 'id="produtos"'),
    ("/contato", 'id="contato"'),
])
def test_htmx_routes_return_only_their_fragment(client, path, marker):
    r = client.get(path, headers={"hx-request": "true"})
    assert r.status_code == 200
    assert marker in r.text
    assert "<!DOCTYPE html>" not in r.text


def test_products_section_is_empty_state_not_invented(client):
    r = client.get("/produtos")
    assert "Conteúdo em preparação" in r.text


@pytest.mark.parametrize("path", ["/", "/quem-somos", "/produtos", "/contato"])
def test_public_pages_share_one_grid_layer(client, path):
    r = client.get(path)
    assert r.status_code == 200
    assert 'class="site-grid"' in r.text
    assert 'class="nav__brand-crop"' in r.text


def test_shared_grid_is_intentionally_visible():
    css = Path("static/css/pm.css").read_text(encoding="utf-8")
    assert "--grid-ambient:      rgba(255,255,255,.18);" in css
    assert ".section--alt { background: rgba(6,6,6,.5); }" in css
    assert 'background-size: 174px 87px;' in css
    assert 'background-position: -27px -29px;' in css


def test_contact_form_lists_all_solution_options(client):
    r = client.get("/contato")
    for opt in ("Desenvolvimento de sistema web", "Consultoria em tecnologia",
                "Ainda não sei qual solução preciso"):
        assert opt in r.text


# --- Health ---------------------------------------------------------------
def test_health_ok_without_database(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["integrations"] == {
        "database": False, "object_storage": False, "chatbot": False,
    }


# --- Contact: happy path --------------------------------------------------
def test_contact_success_persists_and_shows_confirmation(client, tmp_path):
    token = _get_form(client)
    r = client.post("/contato", data=_valid_payload(token))
    assert r.status_code == 200
    assert "Solicitação enviada com sucesso!" in r.text

    from app.services.contact_sink import SqliteSink
    sink = SqliteSink(settings.contact_db_path)
    assert sink.count() == 1
    assert sink.latest()["full_name"] == "João da Silva"


def test_contact_htmx_returns_success_partial(client):
    token = _get_form(client)
    r = client.post("/contato", data=_valid_payload(token),
                    headers={"hx-request": "true"})
    assert r.status_code == 200
    assert "Solicitação enviada com sucesso!" in r.text
    assert "<!DOCTYPE html>" not in r.text  # partial only


# --- Contact: validation --------------------------------------------------
def test_contact_missing_required_shows_errors(client):
    token = _get_form(client)
    payload = _valid_payload(token)
    payload["full_name"] = ""
    payload["email"] = "nope"
    r = client.post("/contato", data=payload)
    assert r.status_code == 422
    assert "Campo obrigatório." in r.text
    from app.services.contact_sink import SqliteSink
    assert SqliteSink(settings.contact_db_path).count() == 0


def test_contact_rejected_without_consent(client):
    token = _get_form(client)
    payload = _valid_payload(token)
    del payload["consent"]
    r = client.post("/contato", data=payload)
    assert r.status_code == 422


def test_contact_invalid_solution_rejected(client):
    token = _get_form(client)
    payload = _valid_payload(token)
    payload["solution"] = "Serviço inventado"
    r = client.post("/contato", data=payload)
    assert r.status_code == 422


# --- Contact: security ----------------------------------------------------
def test_contact_rejects_missing_csrf(client):
    _get_form(client)
    payload = _valid_payload("forged-token")
    r = client.post("/contato", data=payload)
    assert r.status_code == 400
    assert "Sessão expirada" in r.text


def test_contact_honeypot_silently_drops(client):
    token = _get_form(client)
    payload = _valid_payload(token)
    payload["website"] = "http://spam.example"
    r = client.post("/contato", data=payload)
    assert r.status_code == 200
    from app.services.contact_sink import SqliteSink
    assert SqliteSink(settings.contact_db_path).count() == 0


# --- Visual-consistency hooks ---------------------------------------------
# These tests pin the CSS class hooks that carry the shared grid treatment.
# If someone accidentally drops the section--alt class from a template, the
# body-level grid texture will stop showing through those sections without
# any runtime error — these tests catch that silent regression.

@pytest.mark.parametrize("path,expected_class", [
    ("/quem-somos", "section--alt"),
    ("/contato",    "section--alt"),
])
def test_visual_section_alt_hook_is_rendered(client, path, expected_class):
    r = client.get(path)
    assert r.status_code == 200
    assert expected_class in r.text


def test_shared_grid_hook_is_rendered_on_home(client):
    """The home page uses the same shared grid layer as every public route."""
    r = client.get("/")
    assert r.status_code == 200
    assert 'class="site-grid"' in r.text


def test_body_grid_not_blocked_on_products_page(client):
    """Products page uses plain .section (no section--alt), letting the body
    grid show through at full opacity — verify no opaque background class."""
    r = client.get("/produtos")
    assert r.status_code == 200
    assert 'id="produtos"' in r.text
    assert "section--alt" not in r.text
