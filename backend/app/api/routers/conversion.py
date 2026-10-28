"""Currency conversion API route."""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_convert_currency_use_case
from app.api.schemas.conversion import ConversionRequest, ConversionResponse
from app.application.use_cases.convert_currency import ConvertCurrency

router = APIRouter()


@router.post("/convert", response_model=ConversionResponse)
def convert_currency(
    request: ConversionRequest,
    use_case: ConvertCurrency = Depends(get_convert_currency_use_case),
) -> ConversionResponse:
    """Convert an amount using the application-layer conversion use case."""
    result = use_case.execute(
        amount=request.amount,
        source_currency=request.source_currency,
        target_currency=request.target_currency,
    )
    return ConversionResponse.from_domain(result)
