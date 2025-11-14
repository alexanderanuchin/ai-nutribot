"""Asynchronous client for interacting with the NutriBot backend API."""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import aiohttp

from bot.logkit import generate_request_id, get_request_id


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


@dataclass(slots=True)
class AuthResult:
    payload: Dict[str, Any]
    access: str | None
    refresh: str | None


class BackendClient:
    """Small wrapper around aiohttp with retries, refresh and logging."""

    def __init__(
            self,
            base_url: str,
            *,
            timeout: float = 10.0,
            max_retries: int = 3,
            retry_delay: float = 1.0,
            bot_key: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._session: Optional[aiohttp.ClientSession] = None
        self._logger = logging.getLogger("audit.http")
        self._bot_key = bot_key or ""

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
            log_requests: bool = True,
    ) -> Any:
        url = f"{self.base_url}{path}"
        base_headers: Dict[str, str] = {**(headers or {})}
        rid = base_headers.get("X-Request-Id") or get_request_id()
        if not rid or rid == "-":
            rid = generate_request_id()
        base_headers["X-Request-Id"] = rid
        header_snapshot = {
            "has_auth": bool(base_headers.get("Authorization")),
            "has_bot_key": bool(base_headers.get("X-Bot-Key")),
            "has_rid": True,
            "idempotency_key": base_headers.get("Idempotency-Key"),
        }
        last_error: Optional[BackendError] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                session = await self._get_session()
                started = time.perf_counter()
                async with session.request(method, url, json=json, headers=base_headers) as resp:
                    try:
                        data: Any = await resp.json()
                    except aiohttp.ContentTypeError:
                        data = await resp.text()

                    duration_ms = (time.perf_counter() - started) * 1000
                    log_extra = {
                        "rid": rid,
                        "method": method,
                        "path": path,
                        "status": resp.status,
                        "duration_ms": duration_ms,
                    }
                    if resp.status >= 500:
                        if log_requests:
                            self._logger.error(
                                "backend request server_error",
                                extra=log_extra,
                            )
                        raise BackendNetworkError(f"Server error {resp.status}")
                    if resp.status == 401:
                        if log_requests:
                            self._logger.warning(
                                "backend request unauthorized",
                                extra=log_extra,
                            )
                        raise BackendAuthError("Unauthorized")
                    is_structured_error = isinstance(data, dict) and data.get("code")
                    if resp.status in {400, 422} or (resp.status in {403, 409} and is_structured_error):
                        if log_requests:
                            self._logger.warning(
                                "backend request validation",
                                extra={**log_extra, "response_payload": data},
                            )
                        errors = data if isinstance(data, dict) else {"detail": data}
                        raise BackendValidationError(errors)
                    if resp.status >= 400:
                        if log_requests:
                            self._logger.error(
                                "backend request error",
                                extra={**log_extra, "response_payload": data},
                            )
                        raise BackendError(f"Unexpected status {resp.status}: {data}")

                    if log_requests:
                        self._logger.info(
                            "backend request ok",
                            extra={
                                **log_extra,
                                "attempt": attempt,
                                "headers": header_snapshot,
                            },
                        )
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
                if log_requests:
                    self._logger.warning(
                        "backend request retry",
                        extra={
                            "rid": rid,
                            "method": method,
                            "path": path,
                            "attempt": attempt,
                            "max_retries": self._max_retries,
                            "error": str(last_error),
                        },
                    )
                await asyncio.sleep(wait_time)

        assert last_error is not None
        if log_requests:
            self._logger.error(
                "backend request failed",
                extra={
                    "rid": rid,
                    "method": method,
                    "path": path,
                    "error": str(last_error),
                },
            )
        raise last_error

    async def _authorized(
            self,
            method: str,
            path: str,
            *,
            access: str | None,
            refresh: str | None,
            json: Any | None = None,
    ) -> AuthResult:
        if not access:
            raise BackendAuthError("Access token required")
        try:
            payload = await self._request(
                method,
                path,
                json=json,
                headers={"Authorization": f"Bearer {access}"},
            )
            return AuthResult(payload=payload, access=access, refresh=refresh)
        except BackendAuthError:
            if not refresh:
                raise
            tokens = await self.refresh_tokens(refresh)
            new_access = tokens.get("access")
            new_refresh = tokens.get("refresh") or refresh
            if not new_access:
                raise BackendAuthError("Failed to refresh token")
            payload = await self._request(
                method,
                path,
                json=json,
                headers={"Authorization": f"Bearer {new_access}"},
            )
            return AuthResult(payload=payload, access=new_access, refresh=new_refresh)

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

    async def refresh_tokens(self, refresh_token: str) -> Dict[str, Any]:
        if not refresh_token:
            raise BackendAuthError("Refresh token required")
        result = await self._request(
            "POST",
            "/api/users/auth/refresh/",
            json={"refresh": refresh_token},
        )
        if not isinstance(result, dict):
            raise BackendError("Unexpected payload from refresh endpoint")
        return result

    async def report_stars_payment(
            self,
            *,
            user_id: int,
            amount: int,
            charge_id: str,
            payment_attempt_id: int | None = None,
    ) -> Dict[str, Any]:
        if not self._bot_key:
            raise BackendError("Bot key is not configured")
        headers = {
            "X-Bot-Key": self._bot_key,
        }
        if charge_id:
            headers["Idempotency-Key"] = f"telegram-stars:{user_id}:{charge_id}"
        body: Dict[str, Any] = {
            "user_id": int(user_id),
            "amount": int(amount),
            "charge_id": str(charge_id),
        }
        if payment_attempt_id is not None:
            body["payment_attempt_id"] = int(payment_attempt_id)

        payload = await self._request(
            "POST",
            "/api/orders/bot/telegram-stars/payment/",
            json=body,
            headers=headers,
        )
        if not isinstance(payload, dict):
            raise BackendError("Unexpected payload from stars payment report")
        return payload

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

    async def generate_plan(
            self,
            access_token: str | None,
            refresh_token: str | None,
            payload: Dict[str, Any],
    ) -> AuthResult:
        return await self._authorized(
            "POST",
            "/api/nutrition/generate_and_save/",
            access=access_token,
            refresh=refresh_token,
            json=payload,
        )

    async def job_status(
            self,
            access_token: str | None,
            refresh_token: str | None,
            job_id: str,
    ) -> AuthResult:
        return await self._authorized(
            "GET",
            f"/api/nutrition/jobs/{job_id}/",
            access=access_token,
            refresh=refresh_token,
        )

    async def get_latest_plan(
            self,
            access_token: str | None,
            refresh_token: str | None,
    ) -> AuthResult:
        return await self._authorized(
            "GET",
            "/api/nutrition/plans/latest/",
            access=access_token,
            refresh=refresh_token,
        )

    async def get_history(
            self,
            access_token: str | None,
            refresh_token: str | None,
            limit: int = 10,
    ) -> AuthResult:
        return await self._authorized(
            "GET",
            f"/api/nutrition/plans/history/?limit={int(limit)}",
            access=access_token,
            refresh=refresh_token,
        )

    async def get_my_stars(
            self,
            access_token: str | None,
            refresh_token: str | None,
    ) -> AuthResult:
        return await self._authorized(
            "GET",
            "/api/me/stars/",
            access=access_token,
            refresh=refresh_token,
        )

    async def get_bot_stars_balance(
            self,
            access_token: str | None,
            refresh_token: str | None,
    ) -> AuthResult:
        return await self._authorized(
            "GET",
            "/api/admin/stars/bot-balance/",
            access=access_token,
            refresh=refresh_token,
        )

    async def manual_stars_topup(
            self,
            access_token: str | None,
            refresh_token: str | None,
            *,
            amount: int,
            idempotency_key: str,
            source: str,
            metadata: Dict[str, Any] | None = None,
    ) -> AuthResult:
        if not access_token:
            raise BackendAuthError("Access token required")

        headers = {"Authorization": f"Bearer {access_token}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        try:
            payload = await self._request(
                "POST",
                "/api/orders/wallet/manual-stars/",
                json={
                    "amount": int(amount),
                    "source": source,
                    "metadata": metadata or {},
                },
                headers=headers,
            )
            return AuthResult(payload=payload, access=access_token, refresh=refresh_token)
        except BackendAuthError:
            if not refresh_token:
                raise
            tokens = await self.refresh_tokens(refresh_token)
            new_access = tokens.get("access")
            new_refresh = tokens.get("refresh") or refresh_token
            if not new_access:
                raise BackendAuthError("Failed to refresh token")
            headers = {"Authorization": f"Bearer {new_access}"}
            if idempotency_key:
                headers["Idempotency-Key"] = idempotency_key
            payload = await self._request(
                "POST",
                "/api/orders/wallet/manual-stars/",
                json={
                    "amount": int(amount),
                    "source": source,
                    "metadata": metadata or {},
                },
                headers=headers,
            )
            return AuthResult(payload=payload, access=new_access, refresh=new_refresh)

    async def accept_plan(
            self,
            access_token: str | None,
            refresh_token: str | None,
            plan_id: int,
    ) -> AuthResult:
        return await self._authorized(
            "POST",
            f"/api/nutrition/plans/{plan_id}/accept/",
            access=access_token,
            refresh=refresh_token,
        )

    async def reject_plan(
            self,
            access_token: str | None,
            refresh_token: str | None,
            plan_id: int,
    ) -> AuthResult:
        return await self._authorized(
            "POST",
            f"/api/nutrition/plans/{plan_id}/reject/",
            access=access_token,
            refresh=refresh_token,
        )

    async def regenerate_plan(
            self,
            access_token: str | None,
            refresh_token: str | None,
            plan_id: int,
            overrides: Dict[str, Any] | None = None,
    ) -> AuthResult:
        return await self._authorized(
            "POST",
            f"/api/nutrition/plans/{plan_id}/regenerate/",
            access=access_token,
            refresh=refresh_token,
            json={"overrides": overrides} if overrides else {},
        )

    async def send_application_log(
            self,
            *,
            level: str,
            message: str,
            request_id: str | None = None,
            logger: str | None = None,
            extra: Dict[str, Any] | None = None,
            group: str | None = None,
    ) -> None:
        """Send a structured log entry to the backend monitoring endpoint."""

        rid = request_id or get_request_id()
        if not rid or rid == "-":
            rid = generate_request_id()

        headers: Dict[str, str] = {"X-Request-Id": rid}
        if self._bot_key:
            headers["X-Bot-Key"] = self._bot_key

        payload = {
            "level": level,
            "message": message,
            "request_id": rid,
            "logger": logger or "bot.monitoring",
            "extra": extra or {},
        }
        payload["level"] = (payload["level"] or "INFO").upper()
        extra_payload = payload.get("extra")
        if isinstance(extra_payload, dict) and "component" not in extra_payload:
            extra_payload["component"] = "bot"
        if group:
            payload["group"] = group

        try:
            await self._request(
                "POST",
                "/api/monitoring/application/logs/",
                json=payload,
                headers=headers,
                log_requests=False,
            )
        except BackendError as err:
            self._logger.debug(
                "monitoring push failed",
                extra={
                    "rid": rid,
                    "error": str(err),
                },
            )
