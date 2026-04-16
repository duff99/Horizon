"""Tests du modèle Category (arborescence)."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.category import Category


def test_category_basic_fields(db_session) -> None:
    cat = Category(name="Ventes clients", slug="ventes-clients",
                   color="#2ecc71", is_system=True)
    db_session.add(cat)
    db_session.commit()
    db_session.refresh(cat)
    assert cat.id is not None
    assert cat.parent_category_id is None
    assert cat.created_at is not None


def test_category_parent_child(db_session) -> None:
    parent = Category(name="Encaissements", slug="encaissements", is_system=True)
    db_session.add(parent)
    db_session.commit()
    child = Category(name="Ventes", slug="ventes", parent_category_id=parent.id,
                     is_system=True)
    db_session.add(child)
    db_session.commit()
    db_session.refresh(child)
    assert child.parent_category_id == parent.id


def test_category_slug_unique(db_session) -> None:
    db_session.add(Category(name="Ventes", slug="ventes", is_system=False))
    db_session.commit()
    db_session.add(Category(name="Autres", slug="ventes", is_system=False))
    with pytest.raises(IntegrityError):
        db_session.commit()
