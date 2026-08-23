"""Server-side validation for the contact form (Stage 1, no external service)."""
import pytest
from pydantic import ValidationError

from app.schemas.contact import ContactSubmission


def _valid(**overrides):
    data = dict(
        full_name="João da Silva",
        email="contato@empresa.com.br",
        phone="(11) 99999-0000",
        solution="Automação de processos",
        need="Precisamos automatizar o faturamento mensal que hoje é manual.",
        consent=True,
    )
    data.update(overrides)
    return data


def test_valid_submission_parses():
    sub = ContactSubmission(**_valid())
    assert sub.full_name == "João da Silva"
    assert sub.consent is True


def test_optional_fields_default_empty():
    sub = ContactSubmission(**_valid())
    assert sub.company == ""
    assert sub.project_stage is None


@pytest.mark.parametrize("missing", ["full_name", "email", "phone", "solution", "need"])
def test_required_fields_rejected_when_blank(missing):
    with pytest.raises(ValidationError):
        ContactSubmission(**_valid(**{missing: ""}))


def test_invalid_email_rejected():
    with pytest.raises(ValidationError):
        ContactSubmission(**_valid(email="not-an-email"))


def test_solution_must_be_an_approved_option():
    with pytest.raises(ValidationError):
        ContactSubmission(**_valid(solution="Something invented"))


def test_consent_must_be_true():
    with pytest.raises(ValidationError):
        ContactSubmission(**_valid(consent=False))


def test_optional_select_rejects_unknown_value():
    with pytest.raises(ValidationError):
        ContactSubmission(**_valid(priority="Instantâneo"))


def test_optional_select_accepts_known_value():
    sub = ContactSubmission(**_valid(priority="Alta — preciso iniciar o quanto antes"))
    assert sub.priority == "Alta — preciso iniciar o quanto antes"
