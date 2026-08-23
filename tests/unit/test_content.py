"""The stakeholder copy is verbatim-locked (Sakura note 04-content-inbox).

These tests pin the approved Brazilian-Portuguese source text so it cannot be
silently normalized, translated, or rewritten. If a string here needs to
change, that is a stakeholder decision — not a refactor.
"""
from app.content import site_content as c


def test_company_headings_are_verbatim():
    assert c.QUEM_SOMOS.title == "Quem Somos"
    assert c.MISSAO.title == "Missão"
    assert c.VISAO.title == "Visão"
    assert c.PROPOSITO.title == "Propósito"


def test_quem_somos_opening_paragraph_is_verbatim():
    assert c.QUEM_SOMOS.paragraphs[0] == (
        "Somos uma empresa de tecnologia focada no desenvolvimento de sistemas, "
        "soluções digitais, automações e processos personalizados para empresas "
        "que buscam mais eficiência, controle e inovação."
    )


def test_proposito_has_three_paragraphs_verbatim_final():
    assert len(c.PROPOSITO.paragraphs) == 3
    assert c.PROPOSITO.paragraphs[2].startswith(
        "Acreditamos que a tecnologia deve estar a serviço do negócio"
    )


def test_contact_intro_and_success_verbatim():
    assert c.CONTATO_INTRO.title == "Entre em Contato"
    assert c.SUCCESS_TITLE == "Solicitação enviada com sucesso!"
    assert c.SUBMIT_LABEL == "Enviar solicitação"


def test_solution_options_are_the_ten_approved_choices():
    assert c.SOLUTION_OPTIONS == (
        "Desenvolvimento de sistema web",
        "Desenvolvimento de aplicativo",
        "Automação de processos",
        "Integração entre sistemas",
        "Dashboard e análise de dados",
        "Otimização de processos",
        "Consultoria em tecnologia",
        "Manutenção ou evolução de sistema existente",
        "Ainda não sei qual solução preciso",
        "Outro",
    )


def test_priority_and_contact_preference_options_verbatim():
    assert c.PRIORITY_OPTIONS[3] == "Urgente — existe uma necessidade imediata"
    assert c.CONTACT_PREFERENCE_OPTIONS == (
        "WhatsApp",
        "E-mail",
        "Ligação",
        "Reunião on-line",
    )
    assert c.BEST_TIME_OPTIONS[0] == "Manhã"


def test_products_are_not_invented():
    # Content for the ~3 products was never supplied; Stage 1 must not fabricate
    # product names or claims. The section must be an explicit open-decision.
    assert c.PRODUCTS == ()
    assert "aguard" in c.PRODUCTS_PLACEHOLDER.lower() or "prepar" in c.PRODUCTS_PLACEHOLDER.lower()
