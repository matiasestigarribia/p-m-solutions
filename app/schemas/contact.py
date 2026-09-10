"""Contact form submission schema with server-side validation.

Stage 1 uses no external validation/anti-spam service. Option fields are
constrained to the approved verbatim choices from ``site_content`` so the form
cannot be tampered into carrying arbitrary values.
"""
from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.content import site_content as c


def _blank_to_none(v):
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


def _normalize_brazilian_phone(value):
    """Normalize Brazilian landline/mobile numbers to their display format."""
    if not isinstance(value, str):
        return value
    digits = re.sub(r"\D", "", value)
    if len(digits) not in {10, 11}:
        raise ValueError(
            "Informe um telefone brasileiro com DDD, com 10 dígitos (fixo) "
            "ou 11 dígitos (celular)."
        )
    if len(digits) == 10 and digits[2] == "9":
        raise ValueError(
            "O telefone brasileiro celular precisa do nono dígito 9."
        )
    if len(digits) == 11 and digits[2] != "9":
        raise ValueError("O telefone celular deve conter o nono dígito 9.")
    ddd = digits[:2]
    local = digits[2:]
    if len(local) == 9:
        return f"({ddd}) {local[:5]}-{local[5:]}"
    return f"({ddd}) {local[:4]}-{local[4:]}"


class ContactSubmission(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    company: str = ""
    email: EmailStr
    phone: str = Field(min_length=5, max_length=50)
    location: str = ""
    solution: str
    project_stage: Optional[str] = None
    need: str = Field(min_length=10, max_length=5000)
    priority: Optional[str] = None
    deadline: str = ""
    contact_preference: Optional[str] = None
    best_time: Optional[str] = None
    consent: bool

    @field_validator("full_name", "need", mode="before")
    @classmethod
    def _strip_required(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("phone", mode="before")
    @classmethod
    def _phone_brazilian_format(cls, v):
        return _normalize_brazilian_phone(v)

    @field_validator("project_stage", "priority", "contact_preference", "best_time", mode="before")
    @classmethod
    def _optional_blank(cls, v):
        return _blank_to_none(v)

    @field_validator("solution")
    @classmethod
    def _solution_known(cls, v):
        if v not in c.SOLUTION_OPTIONS:
            raise ValueError("Opção de solução inválida.")
        return v

    @field_validator("project_stage")
    @classmethod
    def _stage_known(cls, v):
        if v is not None and v not in c.STAGE_OPTIONS:
            raise ValueError("Opção de etapa inválida.")
        return v

    @field_validator("priority")
    @classmethod
    def _priority_known(cls, v):
        if v is not None and v not in c.PRIORITY_OPTIONS:
            raise ValueError("Opção de prioridade inválida.")
        return v

    @field_validator("contact_preference")
    @classmethod
    def _pref_known(cls, v):
        if v is not None and v not in c.CONTACT_PREFERENCE_OPTIONS:
            raise ValueError("Opção de preferência de contato inválida.")
        return v

    @field_validator("best_time")
    @classmethod
    def _time_known(cls, v):
        if v is not None and v not in c.BEST_TIME_OPTIONS:
            raise ValueError("Opção de horário inválida.")
        return v

    @field_validator("consent")
    @classmethod
    def _consent_true(cls, v):
        if v is not True:
            raise ValueError("É necessário aceitar a Política de Privacidade.")
        return v
