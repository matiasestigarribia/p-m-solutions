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
    monkeypatch.setattr(settings, "enable_database", False, raising=False)
    monkeypatch.setattr(settings, "enable_object_storage", False, raising=False)
    monkeypatch.setattr(settings, "enable_chatbot", False, raising=False)


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


# --- Design-system CSS contract -------------------------------------------
# These tests assert the actual CSS values, not just class presence.
# They fail if someone bumps the grid alpha back to .18/.09/.028 or removes
# the mask, and if the navbar logo workaround (PNG crop offsets) is reintroduced.

_ROOT = Path(__file__).resolve().parents[2]
_CSS = (_ROOT / "static/css/pm.css").read_text()
_BASE = (_ROOT / "templates/base.html").read_text()


def test_grid_line_alpha_is_design_system_compliant():
    """Grid line rgba alpha must equal .04 (DS spec). .18 or any value > .04
    makes the grid noisy and competes with text."""
    # Match the two grid line declarations: rgba(255,255,255,ALPHA) 1px
    alphas = re.findall(r"rgba\(255,255,255,([0-9.]+)\)\s+1px", _CSS)
    assert alphas, "No grid-line rgba declarations found in pm.css"
    for raw in alphas:
        alpha = float(raw)
        assert alpha <= 0.04, (
            f"Grid line alpha {alpha!r} exceeds design-system max (0.04). "
            "Revert to rgba(255,255,255,.04)."
        )


def test_grid_uses_design_system_cell_size():
    """Grid background-size must be 56px 56px per design-system token."""
    assert "background-size: var(--grid-size) var(--grid-size)" in _CSS or \
           "background-size: 56px 56px" in _CSS, \
        "Grid background-size must reference the 56px design-system token."


def test_grid_has_radial_mask():
    """Grid must have the DS radial mask so it fades from the top band.
    Without the mask, the grid covers the full viewport and competes with body text."""
    assert "mask-image: radial-gradient" in _CSS, (
        "site-grid is missing mask-image. Add the DS radial gradient mask."
    )
    assert "-webkit-mask-image: radial-gradient" in _CSS, (
        "site-grid is missing -webkit-mask-image for WebKit browsers."
    )


def test_no_stale_grid_ambient_token():
    """The old --grid-ambient variable (.028 or .18) must not exist.
    Grid alpha is now declared inline in .site-grid per DS source."""
    assert "--grid-ambient" not in _CSS, (
        "--grid-ambient token must be removed; alpha is declared inline in .site-grid."
    )


def test_navbar_uses_actual_brand_asset():
    """Navbar must render the approved P&M logo asset, not a substitute icon.
    The crop box itself begins on the shared 1200px/24px rail."""
    assert 'class="nav__brand-crop"' in _BASE, "logo crop box missing from base.html"
    assert 'class="nav__brand-logo"' in _BASE, "logo image missing from base.html"
    assert 'brand/pm-solutions-logo-dark.png' in _BASE, "approved logo asset missing"


def test_logo_crop_is_deterministic_and_rail_aligned():
    """The source asset's visible artwork is aligned by fixed canvas geometry,
    not browser-dependent object fitting or an arbitrary route offset."""
    assert "width: 120px" in _CSS and "height: 32px" in _CSS
    assert "width: 174px" in _CSS and "height: 87px" in _CSS
    assert "left: -27px" in _CSS and "top: -29px" in _CSS
    assert "object-fit" not in _CSS
    assert "object-position" not in _CSS


@pytest.mark.parametrize("path", ["/", "/quem-somos", "/produtos", "/contato"])
def test_brand_lockup_rendered_on_all_routes(client, path):
    """Every public route must render the approved logo asset in the navbar."""
    r = client.get(path)
    assert r.status_code == 200
    assert 'class="nav__brand-crop"' in r.text
    assert 'class="nav__brand-logo"' in r.text
    assert "brand/pm-solutions-logo-dark.png" in r.text


# --- Home-hero depth fields + signal line ---------------------------------

def test_home_hero_signal_line_present(client):
    """Home hero renders the mission-led signal and project story."""
    r = client.get("/")
    assert r.status_code == 200
    assert "PROBLEMA → PROCESSO → SOLUÇÃO" in r.text
    assert 'class="hero__signal"' in r.text
    assert 'class="hero__badge"' not in r.text
    assert "Tecnologia para empresas" not in r.text
    assert "Você traz o desafio. A gente transforma complexidade em solução." in r.text
    assert 'class="project-console"' in r.text
    assert "import</span> <span class=\"code-variable\">Projeto" in r.text
    assert "simplificar" in r.text


def test_hero_signal_not_on_inner_pages(client):
    """Signal line is home-only; inner pages must not carry it."""
    for path in ("/quem-somos", "/produtos", "/contato"):
        r = client.get(path)
        assert "hero__signal" not in r.text, f"hero__signal found on {path}"


def test_hero_cyan_depth_field_in_css():
    """hero--home::before must define the cyan radial depth field (DS rgba(14,165,233,0.18))."""
    assert ".site-glow--cyan" in _CSS, "shared cyan glow selector missing"
    assert ".site-glow--indigo" in _CSS, "shared indigo glow selector missing"
    assert "rgba(14,165,233,0.18)" in _CSS, \
        "Cyan depth field rgba(14,165,233,0.18) not found in shared glow"
    assert "rgba(129,140,248,0.14)" in _CSS, \
        "Indigo depth field rgba(129,140,248,0.14) not found in shared glow"
    assert 'class="site-glow site-glow--cyan"' in _BASE
    assert 'class="site-glow site-glow--indigo"' in _BASE


def test_hero_indigo_depth_field_in_css():
    """hero--home::after must define the indigo radial depth field (DS rgba(129,140,248,0.14))."""
    assert ".site-glow--indigo" in _CSS, "shared indigo glow selector missing"
    assert "rgba(129,140,248,0.14)" in _CSS, \
        "Indigo depth field rgba(129,140,248,0.14) not found in shared glow"
    assert 'class="site-glow site-glow--cyan"' in _BASE
    assert 'class="site-glow site-glow--indigo"' in _BASE


@pytest.mark.parametrize("path", ["/", "/quem-somos", "/produtos", "/contato"])
def test_shared_glows_render_on_all_routes(client, path):
    """The shared site face must include both depth fields on every route."""
    r = client.get(path)
    assert r.status_code == 200
    assert 'class="site-glow site-glow--cyan"' in r.text
    assert 'class="site-glow site-glow--indigo"' in r.text


def test_hero_inner_sits_above_depth_fields():
    """.hero__inner z-index must be higher than the shared depth fields."""
    inner_match = re.search(r"\.hero__inner\s*\{[^}]+z-index:\s*(\d+)", _CSS)
    assert inner_match, ".hero__inner z-index declaration not found in pm.css"
    assert int(inner_match.group(1)) >= 2, \
        ".hero__inner z-index must be ≥ 2 to sit above shared depth fields"


def test_grid_alpha_and_mask_unaffected_by_depth_fields():
    """Depth field additions must not alter grid alpha (≤0.04) or remove the DS mask."""
    alphas = re.findall(r"rgba\(255,255,255,([0-9.]+)\)\s+1px", _CSS)
    assert alphas, "No grid-line rgba declarations found — grid may have been removed"
    for raw in alphas:
        assert float(raw) <= 0.04, \
            f"Grid alpha {raw!r} exceeds 0.04 — depth field edit must not touch the grid"
    assert "mask-image: radial-gradient" in _CSS, \
        "DS radial mask was removed from site-grid"


def test_navbar_stacking_rule_keeps_nav_above_page_content():
    """The body-child stacking rule must not override the navbar z-index."""
    assert "body > *:not(.site-grid):not(.site-glow):not(.nav)" in _CSS
    nav_match = re.search(r"\.nav\s*\{[^}]+z-index:\s*(\d+)", _CSS)
    assert nav_match, "Navbar z-index declaration not found"
    assert int(nav_match.group(1)) >= 50


def test_select_options_have_dark_native_popup_contrast():
    """Dark form controls must keep native select options readable."""
    assert "select.input-el option" in _CSS
    assert "color-scheme: dark" in _CSS
    assert "color: #18181b" in _CSS
    assert "background-color: #fff" in _CSS


def test_stylesheet_version_changes_when_visual_css_changes():
    """Browser caches must not retain the pre-fix stylesheet indefinitely."""
    assert "pm.css') }}?v=20260903-chatbot-icon" in _BASE


def test_chatbot_launcher_has_chat_icon_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "enable_chatbot", True, raising=False)
    r = TestClient(app).get("/")
    assert r.status_code == 200
    assert 'id="pm-chat-launcher"' in r.text
    assert 'class="chat-launcher__icon"' in r.text
