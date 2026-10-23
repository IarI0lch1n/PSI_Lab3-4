"""FastAPI application entry point for CurrencyHub."""

from fastapi import FastAPI

app = FastAPI(
    title="CurrencyHub API",
    description="Currency conversion and exchange-rate analytics platform",
    version="0.1.0",
)


@app.get("/")
def read_root() -> dict[str, str]:
    """Root entry point returning welcome message."""
    return {"message": "Welcome to CurrencyHub API"}
