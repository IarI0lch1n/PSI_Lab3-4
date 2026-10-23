"""Initial test verifying FastAPI app initialization."""

from app.main import app


def test_app_instance() -> None:
    """Verify that the FastAPI app instance is configured."""
    assert app is not None
    assert app.title == "CurrencyHub API"
