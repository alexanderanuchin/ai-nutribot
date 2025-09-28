"""Asynchronous client for interacting with the NutriBot backend API."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp


class BackendError(RuntimeError):
    """Base exception for backend communication issues."""


class BackendNetworkError(BackendError):
    """Raised when the backend is temporarily unavailable."""


class BackendAuthError(BackendError):
    """Raised when access token is missing or invalid."""


class BackendValidationError(BackendError):
    """Raised when the backend returns validation errors."""

    def __init__(self, errors: Dict[str, Any]):
        super().__init__("Validation failed")
        self.errors = errors


class BackendClient:
    """Small wrapper around aiohttp with retries and logging."""

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._session: Optional[aiohttp.ClientSession] = None
        self._logger = logging.getLogger("nutribot.backend")

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        headers: Dict[str, str] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        last_error: Optional[BackendError] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                session = await self._get_session()
                async with session.request(method, url, json=json, headers=headers) as resp:
                    try:
                        data: Any = await resp.json()
                    except aiohttp.ContentTypeError:
                        data = await resp.text()

                    if resp.status >= 500:
                        raise BackendNetworkError(f"Server error {resp.status}")
                    if resp.status == 401:
                        raise BackendAuthError("Unauthorized")
                    if resp.status == 400:
                        errors = data if isinstance(data, dict) else {"detail": data}
                        raise BackendValidationError(errors)
                    if resp.status >= 400:
                        raise BackendError(f"Unexpected status {resp.status}: {data}")

                    return data
            except BackendValidationError:
                raise
            except BackendAuthError:
                raise
            except BackendNetworkError as err:
                last_error = err
            except BackendError as err:
                last_error = err
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                last_error = BackendNetworkError(str(err))

            if attempt < self._max_retries:
                wait_time = self._retry_delay * attempt
                self._logger.warning(
                    "Backend request %s %s failed (attempt %s/%s): %s",
                    method,
                    url,
                    attempt,
                    self._max_retries,
                    last_error,
                )
                await asyncio.sleep(wait_time)

        assert last_error is not None
        raise last_error

    async def ping(self) -> bool:
        try:
            await self._request("GET", "/api/nutrition/ping/")
            return True
        except BackendError as err:
            self._logger.debug("Backend ping failed: %s", err)
            return False

    async def tg_exchange(self, init_data: str) -> Dict[str, Any]:
        if not init_data:
            raise BackendError("init_data is required")
        result = await self._request(
            "POST",
            "/api/users/auth/tg_exchange/",
            json={"init_data": init_data},
        )
        if not isinstance(result, dict):
            raise BackendError("Unexpected payload from tg_exchange")
        return result

    async def get_me(self, access_token: str) -> Dict[str, Any]:
        if not access_token:
            raise BackendAuthError("Access token required")
        result = await self._request(
            "GET",
            "/api/users/me/profile/",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if not isinstance(result, dict):
            raise BackendError("Unexpected payload from profile endpoint")
        return result

    async def upsert_profile(self, access_token: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not access_token:
            raise BackendAuthError("Access token required")
        result = await self._request(
            "PATCH",
            "/api/users/me/profile/update/",
            json=payload,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if not isinstance(result, dict):
            raise BackendError("Unexpected payload from profile update")
        return result