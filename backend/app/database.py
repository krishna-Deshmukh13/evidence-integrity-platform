from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from . import config

_kw = {"connect_args": {"check_same_thread": False, "timeout": 30.0}}
if ":memory:" in config.DATABASE_URL:
    _kw["poolclass"] = StaticPool
engine = create_engine(config.DATABASE_URL, **_kw)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables, then add any column the code has but the file lacks."""
    from . import models  # noqa: F401
    Base.metadata.create_all(engine)
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            have = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name not in have:
                    ddl = col.type.compile(dialect=engine.dialect)
                    conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN {col.name} {ddl}'))
        n_admin = conn.execute(text("SELECT COUNT(*) FROM users WHERE role='admin'")).scalar()
        if n_admin == 0:
            conn.execute(text("UPDATE users SET role='admin' WHERE id=(SELECT MIN(id) FROM users)"))
