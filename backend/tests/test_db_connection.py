from sqlalchemy import text

from app.db import get_engine


def test_engine_connects() -> None:
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar_one()
    assert result == 1
