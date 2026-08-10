"""Contact submissions persist behind a swappable ContactSink interface.

Stage 1 ships a logging sink and a local SQLite sink. The interface is the seam
that Stage 2 will implement with Neon PostgreSQL without touching callers.
"""
from app.core.settings import Settings
from app.schemas.contact import ContactSubmission
from app.services.contact_sink import LoggingSink, SqliteSink, get_contact_sink


def _sub():
    return ContactSubmission(
        full_name="Maria Souza",
        email="maria@exemplo.com.br",
        phone="(11) 98888-7777",
        solution="Consultoria em tecnologia",
        need="Gostaria de organizar os processos internos da empresa.",
        consent=True,
    )


def test_logging_sink_returns_reference(caplog):
    ref = LoggingSink().save(_sub())
    assert isinstance(ref, str) and ref


def test_sqlite_sink_persists_row(tmp_path):
    db = tmp_path / "nested" / "contact.sqlite3"
    sink = SqliteSink(str(db))
    ref = sink.save(_sub())
    assert ref
    assert db.exists()
    assert sink.count() == 1
    row = sink.latest()
    assert row["full_name"] == "Maria Souza"
    assert row["email"] == "maria@exemplo.com.br"
    assert row["solution"] == "Consultoria em tecnologia"


def test_sqlite_sink_appends(tmp_path):
    sink = SqliteSink(str(tmp_path / "c.sqlite3"))
    sink.save(_sub())
    sink.save(_sub())
    assert sink.count() == 2


def test_factory_selects_sqlite(tmp_path):
    s = Settings(_env_file=None, contact_sink="sqlite",
                 contact_db_path=str(tmp_path / "c.sqlite3"))
    assert isinstance(get_contact_sink(s), SqliteSink)


def test_factory_selects_logging():
    s = Settings(_env_file=None, contact_sink="logging")
    assert isinstance(get_contact_sink(s), LoggingSink)
