"""Apify client: runs a tracking actor for a batch of BL numbers and returns one item per BL."""

import httpx

API = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"


class ApifyError(Exception):
    """The actor run failed. The message is Danish and goes in the sheet's Note."""


class Apify:
    def __init__(self, token: str, timeout_seconds: int = 300):
        if not token:
            raise ApifyError("APIFY_TOKEN mangler i .env")
        self._headers = {"Authorization": f"Bearer {token}"}
        self._timeout = timeout_seconds

    def track(self, actor: str, numbers: list[str]) -> dict[str, dict]:
        """One actor run for all numbers. Returns {BL upper case: item}; missing BLs are simply absent."""
        if not numbers:
            return {}
        try:
            response = httpx.post(
                API.format(actor=actor.replace("/", "~")),
                headers=self._headers,
                json={"trackingNumbers": numbers},
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise ApifyError("Apify svarede ikke i tide") from exc
        except httpx.HTTPError as exc:
            raise ApifyError("Ingen forbindelse til Apify") from exc
        if response.status_code == 401:
            raise ApifyError("Apify afviste nøglen (APIFY_TOKEN)")
        if response.status_code >= 400:
            raise ApifyError(f"Apify-fejl (HTTP {response.status_code})")
        try:
            items = response.json()
        except ValueError as exc:
            raise ApifyError("Uventet svar fra Apify") from exc
        return {
            str(item.get("tracking_number", "")).strip().upper(): item
            for item in items if isinstance(item, dict)
        }
