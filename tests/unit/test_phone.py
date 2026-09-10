from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.contact import ContactSubmission


def _valid(**overrides):
    data = {
        "full_name": "João da Silva",
        "email": "contato@empresa.com.br",
        "phone": "(11) 98888-7777",
        "solution": "Automação de processos",
        "need": "Precisamos automatizar o faturamento mensal que hoje é manual.",
        "consent": True,
    }
    data.update(overrides)
    return data


def test_mobile_phone_is_normalized_to_brazilian_format():
    submission = ContactSubmission(**_valid(phone="11988887777"))

    assert submission.phone == "(11) 98888-7777"


def test_landline_phone_is_normalized_to_brazilian_format():
    submission = ContactSubmission(**_valid(phone="1133334444"))

    assert submission.phone == "(11) 3333-4444"


@pytest.mark.parametrize("phone", ["1198888777", "113333444", "119888877788"])
def test_phone_rejects_invalid_brazilian_lengths(phone):
    with pytest.raises(ValidationError, match="telefone brasileiro"):
        ContactSubmission(**_valid(phone=phone))


def test_mobile_phone_requires_the_ninth_digit():
    with pytest.raises(ValidationError, match="nono dígito"):
        ContactSubmission(**_valid(phone="11888887777"))
