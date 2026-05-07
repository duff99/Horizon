"""D1 guard — Phase 2 : vérifier l'ABSENCE après suppression."""
import pytest


def test_forecast_entry_module_deleted():
    with pytest.raises(ModuleNotFoundError):
        import app.models.forecast_entry  # noqa: F401


def test_forecast_entry_not_in_models_init():
    import app.models as m
    assert not hasattr(m, "ForecastEntry")
    assert not hasattr(m, "ForecastRecurrence")


def test_entry_schemas_deleted():
    from app.schemas import forecast as f
    assert not hasattr(f, "ForecastEntryCreate")
    assert not hasattr(f, "ForecastEntryRead")
    assert not hasattr(f, "ForecastEntryUpdate")


def test_counterparty_preview_no_forecast_entry_count():
    from app.schemas.counterparty import CounterpartyMergePreview
    assert "forecast_entry_count" not in CounterpartyMergePreview.model_fields
