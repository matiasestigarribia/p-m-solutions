"""Approved P&M Solutions website copy — Stage 1.

SOURCE OF TRUTH: /home/hermes/obsidian-vaults/sakura-vault/1-Projects/
p-and-m-solutions/04-content-inbox.md  (section "Raw Website Copy — Verbatim").

INTAKE RULE (note 04): capture the stakeholder copy verbatim. Do NOT normalize,
complete, summarize, translate, or silently rewrite it. Every user-visible
string below is reproduced byte-for-byte from the approved Brazilian-Portuguese
source. UI microcopy that is *not* in the source (button states, placeholders
for undelivered content) is clearly marked as such and kept neutral — no
invented product names, services, claims, legal text, or privacy promises.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Section:
    title: str
    paragraphs: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Quem Somos / Missão / Visão / Propósito  (verbatim)
# ---------------------------------------------------------------------------
QUEM_SOMOS = Section(
    title="Quem Somos",
    paragraphs=(
        "Somos uma empresa de tecnologia focada no desenvolvimento de sistemas, "
        "soluções digitais, automações e processos personalizados para empresas "
        "que buscam mais eficiência, controle e inovação.",
        "Atuamos em todas as etapas de um projeto, desde o levantamento das "
        "necessidades e planejamento da solução até o desenvolvimento front-end, "
        "back-end, banco de dados, implantação e suporte.",
        "Nosso trabalho vai além da criação de sistemas. Buscamos compreender "
        "profundamente a realidade de cada cliente, identificar gargalos, "
        "organizar processos e desenvolver soluções que gerem resultados "
        "práticos, segurança e crescimento sustentável.",
        "Cada projeto é construído de forma personalizada, considerando as "
        "particularidades do negócio, seus objetivos e seus desafios. Combinamos "
        "conhecimento técnico, visão estratégica e proximidade com o cliente "
        "para transformar ideias e necessidades em soluções digitais completas.",
    ),
)

MISSAO = Section(
    title="Missão",
    paragraphs=(
        "Desenvolver sistemas, soluções tecnológicas e processos inteligentes "
        "que simplifiquem operações, aumentem a produtividade e ajudem empresas "
        "a alcançar melhores resultados.",
        "Nossa missão é entregar soluções completas, seguras e personalizadas, "
        "acompanhando cada projeto desde a identificação do problema até sua "
        "implantação, evolução e utilização no dia a dia.",
    ),
)

VISAO = Section(
    title="Visão",
    paragraphs=(
        "Ser reconhecida como uma empresa de tecnologia confiável, inovadora e "
        "estratégica, capaz de transformar desafios empresariais em soluções "
        "digitais eficientes e escaláveis.",
        "Buscamos construir relacionamentos duradouros com nossos clientes, "
        "tornando-nos parceiros na modernização de seus processos, no "
        "crescimento de seus negócios e na evolução contínua de suas operações.",
    ),
)

PROPOSITO = Section(
    title="Propósito",
    paragraphs=(
        "Transformar processos complexos em soluções simples, eficientes e "
        "acessíveis por meio da tecnologia.",
        "Nosso propósito é utilizar o desenvolvimento de sistemas e a inovação "
        "para resolver problemas reais, reduzir trabalhos manuais, melhorar a "
        "tomada de decisão e proporcionar mais controle, agilidade e segurança "
        "para empresas e pessoas.",
        "Acreditamos que a tecnologia deve estar a serviço do negócio, criando "
        "valor, facilitando rotinas e abrindo novas possibilidades de "
        "crescimento.",
    ),
)

COMPANY_SECTIONS = (QUEM_SOMOS, MISSAO, VISAO, PROPOSITO)
# The three-card block rendered under "Quem Somos" in the design system.
MVP_SECTIONS = (MISSAO, VISAO, PROPOSITO)


# ---------------------------------------------------------------------------
# Produtos  (NOT supplied — open decision, must not be invented)
# ---------------------------------------------------------------------------
# Note 04: "Produtos: área com uns 3 produtos pro cliente analisar" and
# "product names and descriptions are not yet supplied." Stage 1 renders the
# section as an explicit empty-state instead of fabricating product content.
PRODUCTS: tuple = ()
PRODUCTS_TITLE = "Produtos"
# Neutral UI microcopy only — no product claims. TODO(stage-1 content): replace
# once Mati supplies the ~3 approved products for client review.
PRODUCTS_PLACEHOLDER = "Conteúdo em preparação. Em breve apresentaremos nossos produtos."


# ---------------------------------------------------------------------------
# Entre em Contato — intro (verbatim)
# ---------------------------------------------------------------------------
CONTATO_INTRO = Section(
    title="Entre em Contato",
    paragraphs=(
        "Tem uma ideia, um processo que precisa ser otimizado ou um projeto que "
        "deseja transformar em realidade?",
        "Conte um pouco sobre sua necessidade. Nossa equipe analisará as "
        "informações e entrará em contato para entender melhor o cenário, "
        "identificar oportunidades e apresentar os próximos passos para o "
        "desenvolvimento da solução.",
    ),
)

CONTACT_INFO_HEADING = "Informações de Contato"
PROJECT_HEADING = "Sobre o Projeto"


# ---------------------------------------------------------------------------
# Contact form — verbatim labels, help text, examples, and options
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Field:
    name: str            # HTML/schema field name (stable, ASCII)
    label: str           # verbatim label
    required: bool = False
    example: str = ""    # verbatim "Exemplo:" text where supplied
    help: str = ""       # verbatim support text
    options: tuple[str, ...] = field(default_factory=tuple)
    kind: str = "text"   # text | email | tel | textarea | select | file
    enabled: bool = True  # False => rendered but inactive (future seam)


SOLUTION_OPTIONS = (
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

STAGE_OPTIONS = (
    "Tenho apenas uma ideia",
    "Já defini algumas necessidades",
    "Tenho um projeto ou documentação pronta",
    "Já possuo um sistema e preciso melhorá-lo",
    "Preciso substituir um processo manual",
    "Preciso integrar sistemas existentes",
    "O projeto já está em desenvolvimento",
)

PRIORITY_OPTIONS = (
    "Baixa — projeto para planejamento futuro",
    "Média — desejo iniciar nos próximos meses",
    "Alta — preciso iniciar o quanto antes",
    "Urgente — existe uma necessidade imediata",
)

CONTACT_PREFERENCE_OPTIONS = (
    "WhatsApp",
    "E-mail",
    "Ligação",
    "Reunião on-line",
)

BEST_TIME_OPTIONS = (
    "Manhã",
    "Tarde",
    "Noite",
    "Horário comercial",
    "Qualquer horário",
)

# Attachment formats (verbatim)
ATTACHMENT_FORMATS = "Formatos sugeridos: PDF, DOCX, XLSX, CSV, PNG, JPG e ZIP."

CONTACT_FIELDS: tuple[Field, ...] = (
    Field("full_name", "Nome completo", required=True,
          example="Exemplo: João da Silva",
          help="Campo para o cliente informar seu nome."),
    Field("company", "Empresa",
          example="Exemplo: Empresa Exemplo Ltda.",
          help="Nome da empresa ou organização que o cliente representa."),
    Field("email", "E-mail", required=True, kind="email",
          example="Exemplo: contato@empresa.com.br",
          help="E-mail principal para retorno e envio de informações."),
    Field("phone", "Telefone ou WhatsApp", required=True, kind="tel",
          example="Exemplo: (00) 00000-0000",
          help="Número para contato direto com o cliente."),
    Field("location", "Cidade e Estado",
          example="Exemplo: São Paulo – SP",
          help="Localização da empresa ou do cliente."),
    Field("solution", "Qual solução você procura?", required=True, kind="select",
          options=SOLUTION_OPTIONS),
    Field("project_stage", "Em qual etapa o projeto está?", kind="select",
          options=STAGE_OPTIONS),
    Field("need", "Conte-nos sobre sua necessidade", required=True, kind="textarea",
          help="Descreva como o processo funciona atualmente, quais "
               "dificuldades estão sendo enfrentadas e qual resultado você "
               "espera alcançar com a solução."),
    Field("priority", "Qual é a prioridade do projeto?", kind="select",
          options=PRIORITY_OPTIONS),
    Field("deadline", "Existe um prazo esperado?",
          example="Exemplo: Gostaria de iniciar em até 30 dias.",
          help="Campo para o cliente informar uma data ou período estimado."),
    Field("attachment", "Anexar arquivo", kind="file", enabled=True,
          help="Campo opcional para o envio de documentos, planilhas, imagens, "
               "fluxos, apresentações ou materiais relacionados ao projeto. "
               + ATTACHMENT_FORMATS),
    Field("contact_preference", "Como prefere ser contatado?", kind="select",
          options=CONTACT_PREFERENCE_OPTIONS),
    Field("best_time", "Melhor horário para contato", kind="select",
          options=BEST_TIME_OPTIONS),
)

# Attachment uploads are processed server-side via Cloudflare R2 when
# enable_object_storage=True; silently ignored in dev when R2 is disabled.
CONTACT_FIELD_MAP = {f.name: f for f in CONTACT_FIELDS}

# Grouping matches the approved layout: "Informações de Contato" then
# "Sobre o Projeto".
CONTACT_INFO_FIELD_NAMES = ("full_name", "company", "email", "phone", "location")
PROJECT_FIELD_NAMES = (
    "solution", "project_stage", "need", "priority", "deadline",
    "attachment", "contact_preference", "best_time",
)
CONTACT_INFO_FIELDS = tuple(CONTACT_FIELD_MAP[n] for n in CONTACT_INFO_FIELD_NAMES)
PROJECT_FIELDS = tuple(CONTACT_FIELD_MAP[n] for n in PROJECT_FIELD_NAMES)

CONSENT_LABEL = (
    "Li e concordo com a Política de Privacidade e autorizo o uso dos dados "
    "informados exclusivamente para análise da solicitação e realização do "
    "contato."
)
# TODO(open-decision): no Política de Privacidade body was supplied. The link
# target is a placeholder until legal copy is approved (note 05, "Legal,
# privacy, cookie, and chatbot disclosures").
PRIVACY_POLICY_HREF = "#politica-de-privacidade"

SUBMIT_LABEL = "Enviar solicitação"

SUCCESS_TITLE = "Solicitação enviada com sucesso!"
SUCCESS_PARAGRAPHS = (
    "Recebemos suas informações. Nossa equipe analisará sua necessidade e "
    "entrará em contato pelos canais informados.",
    "Obrigado pelo interesse em desenvolver seu projeto conosco.",
)
