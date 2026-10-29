"""BNM XML adapter for normalized current and historical fiat rates."""

from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal, DecimalException
from typing import Final
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import httpx

from app.core.config.settings import Settings, get_settings
from app.domain.entities.currency import SUPPORTED_FIAT_CURRENCIES
from app.domain.enums.currency_type import CurrencyType
from app.domain.interfaces.rate_provider import ProviderRate, RateProvider


_MOLDOVA_TIMEZONE: Final[ZoneInfo] = ZoneInfo("Europe/Chisinau")
_PROVIDER_NAME: Final[str] = "BNM"


class BnmRateProviderError(RuntimeError):
    """Raised when BNM data cannot be fetched or parsed reliably."""


class BnmRateProvider(RateProvider):
    """Fetch and normalize BNM rates without applying freshness policy."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        settings: Settings | None = None,
        today_provider: Callable[[], date] | None = None,
    ) -> None:
        self._client = client
        self._settings = settings or get_settings()
        self._base_url = self._settings.bnm_base_url
        self._today_provider = today_provider or self._moldova_today

    async def fetch_latest_rates(self) -> Sequence[ProviderRate]:
        """Fetch BNM rates for the current Moldova calendar date."""
        requested_date = self._today_provider()
        date_parameter = requested_date.strftime("%d.%m.%Y")
        response = await self._request_rates(date_parameter)

        if not response.content.strip():
            raise BnmRateProviderError("BNM returned an empty XML response.")
        return self._parse_xml(response.text)

    async def fetch_historical_rates(
        self,
        currency_codes: Sequence[str],
        start_at: datetime,
        end_at: datetime,
    ) -> Sequence[ProviderRate]:
        """Fetch available official rates in an inclusive Moldova date window."""
        start_date = self._moldova_date(start_at, "start_at")
        end_date = self._moldova_date(end_at, "end_at")
        if start_date > end_date:
            raise BnmRateProviderError("Historical start_at must not follow end_at.")

        requested_codes = {
            code.strip().upper()
            for code in currency_codes
            if code.strip().upper() in SUPPORTED_FIAT_CURRENCIES
            and code.strip().upper() != "MDL"
        }
        if not requested_codes:
            return ()

        rates_by_date_and_code: dict[tuple[date, str], ProviderRate] = {}
        requested_date = start_date
        while requested_date <= end_date:
            response = await self._request_rates(
                requested_date.strftime("%d.%m.%Y")
            )
            if response.content.strip():
                for rate in self._parse_xml(response.text):
                    effective_date = rate.effective_at.astimezone(
                        _MOLDOVA_TIMEZONE
                    ).date()
                    if (
                        rate.currency in requested_codes
                        and start_date <= effective_date <= end_date
                    ):
                        rates_by_date_and_code.setdefault(
                            (effective_date, rate.currency),
                            rate,
                        )
            requested_date += timedelta(days=1)

        currency_order = {
            code: index for index, code in enumerate(SUPPORTED_FIAT_CURRENCIES)
        }
        return tuple(
            sorted(
                rates_by_date_and_code.values(),
                key=lambda rate: (
                    rate.effective_at,
                    currency_order[rate.currency],
                ),
            )
        )

    async def get_metadata(self) -> Mapping[str, str]:
        """Return non-secret provider identity and endpoint metadata."""
        return {
            "provider_name": _PROVIDER_NAME,
            "provider_type": CurrencyType.FIAT.value,
            "base_url": self._base_url,
        }

    async def _request_rates(self, date_parameter: str) -> httpx.Response:
        params = {"get_xml": "1", "date": date_parameter}
        attempts = max(1, self._settings.bnm_max_retries + 1)

        for attempt in range(attempts):
            try:
                if self._client is not None:
                    response = await self._client.get(self._base_url, params=params)
                else:
                    async with httpx.AsyncClient(
                        timeout=self._settings.bnm_timeout_seconds
                    ) as client:
                        response = await client.get(self._base_url, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                if status_code < 500 or attempt + 1 == attempts:
                    raise BnmRateProviderError(
                        f"BNM request failed with HTTP status {status_code}."
                    ) from exc
            except httpx.RequestError as exc:
                if attempt + 1 == attempts:
                    raise BnmRateProviderError(
                        f"BNM request failed after {attempts} attempt(s)."
                    ) from exc

        raise BnmRateProviderError("BNM request failed without a response.")

    @classmethod
    def _parse_xml(cls, xml_text: str) -> tuple[ProviderRate, ...]:
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as exc:
            raise BnmRateProviderError("BNM returned malformed XML.") from exc

        raw_date = root.attrib.get("Date", "").strip()
        try:
            effective_date = datetime.strptime(raw_date, "%d.%m.%Y").date()
        except ValueError as exc:
            raise BnmRateProviderError(
                "BNM XML is missing a valid root Date in DD.MM.YYYY format."
            ) from exc
        effective_at = datetime.combine(
            effective_date,
            time.min,
            tzinfo=_MOLDOVA_TIMEZONE,
        )

        supported_codes = set(SUPPORTED_FIAT_CURRENCIES)
        rates: list[ProviderRate] = []
        seen_codes: set[str] = set()

        for row in root.iter():
            if cls._local_tag(row.tag) != "Valute":
                continue

            fields = {
                cls._local_tag(child.tag): (child.text or "").strip()
                for child in row
            }
            raw_code = fields.get("CharCode", "")
            if not raw_code:
                raise BnmRateProviderError(
                    "BNM XML contains a currency row without CharCode."
                )
            currency_code = raw_code.upper()
            if currency_code not in supported_codes:
                continue
            if currency_code in seen_codes:
                raise BnmRateProviderError(
                    f"BNM XML contains duplicate supported currency {currency_code}."
                )
            seen_codes.add(currency_code)

            raw_nominal = fields.get("Nominal", "")
            try:
                nominal_unit = int(raw_nominal)
            except ValueError as exc:
                raise BnmRateProviderError(
                    f"BNM XML has an invalid Nominal for {currency_code}."
                ) from exc
            if nominal_unit <= 0:
                raise BnmRateProviderError(
                    f"BNM XML Nominal must be positive for {currency_code}."
                )

            raw_value = fields.get("Value", "")
            if not raw_value:
                raise BnmRateProviderError(
                    f"BNM XML is missing Value for {currency_code}."
                )
            try:
                quoted_value = Decimal(raw_value.replace(",", "."))
            except DecimalException as exc:
                raise BnmRateProviderError(
                    f"BNM XML has a non-numeric Value for {currency_code}."
                ) from exc

            try:
                normalized_rate = quoted_value / Decimal(nominal_unit)
            except DecimalException as exc:
                raise BnmRateProviderError(
                    f"BNM XML has an invalid normalized rate for {currency_code}."
                ) from exc
            if not normalized_rate.is_finite() or normalized_rate <= 0:
                raise BnmRateProviderError(
                    f"BNM XML has a non-positive or invalid normalized rate for {currency_code}."
                )

            rates.append(
                ProviderRate(
                    currency=currency_code,
                    normalized_rate_to_mdl=normalized_rate,
                    nominal_unit=nominal_unit,
                    provider_name=_PROVIDER_NAME,
                    provider_type=CurrencyType.FIAT,
                    effective_at=effective_at,
                )
            )

        if not rates:
            raise BnmRateProviderError(
                "BNM XML contained no supported usable currency rows."
            )
        return tuple(rates)

    @staticmethod
    def _local_tag(tag: str) -> str:
        """Return an XML tag's local name, ignoring an optional namespace."""
        return tag.rsplit("}", 1)[-1]

    @staticmethod
    def _moldova_today() -> date:
        return datetime.now(_MOLDOVA_TIMEZONE).date()

    @staticmethod
    def _moldova_date(value: datetime, field_name: str) -> date:
        if value.tzinfo is None or value.utcoffset() is None:
            raise BnmRateProviderError(
                f"Historical {field_name} must be timezone-aware."
            )
        return value.astimezone(_MOLDOVA_TIMEZONE).date()
