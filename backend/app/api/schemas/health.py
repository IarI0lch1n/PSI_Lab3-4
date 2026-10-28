"""Backend and provider operational health response schema."""

from pydantic import AwareDatetime, BaseModel


class HealthResponse(BaseModel):
    """Operational health without rate-freshness information."""

    status: str
    backend: str
    providers: dict[str, str]
    last_successful_snapshot: AwareDatetime | None
