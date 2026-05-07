"""Tests Category.kind — D2."""


def test_category_has_kind_attribute(db_session):
    from app.models.category import Category
    cat = db_session.query(Category).first()
    assert hasattr(cat, "kind")
    assert cat.kind in ("in", "out", "both")


def test_encaissements_is_in(db_session):
    from app.models.category import Category
    cat = db_session.query(Category).filter(Category.slug == "encaissements").one()
    assert cat.kind == "in"


def test_personnel_is_out(db_session):
    from app.models.category import Category
    cat = db_session.query(Category).filter(Category.slug == "personnel").one()
    assert cat.kind == "out"


def test_flux_financiers_is_both(db_session):
    from app.models.category import Category
    cat = db_session.query(Category).filter(Category.slug == "flux-financiers").one()
    assert cat.kind == "both"
