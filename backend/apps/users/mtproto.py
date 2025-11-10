from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from importlib import import_module
from types import TracebackType
from typing import Any, Awaitable, Callable, Dict, Iterable, TypeVar

logger = logging.getLogger("service.telegram.mtproto")

T = TypeVar("T")

# Lazy Telethon imports to avoid side effects during module import in tests
TelegramClientCls: Any | None = None
StringSessionCls: Any | None = None
MemorySessionCls: Any | None = None
InputPeerSelfCls: Any | None = None
TLObjectCls: Any | None = None
GetStarsStatusRequestCls: Any | None = None
GetStarsTransactionsRequestCls: Any | None = None
GetStarsRevenueStatsRequestCls: Any | None = None
AuthKeyUnregisteredError: Any | None = None
RPCError: Any | None = None


def _ensure_telethon() -> None:
    global TelegramClientCls, StringSessionCls, MemorySessionCls
    global InputPeerSelfCls, TLObjectCls
    global GetStarsStatusRequestCls, GetStarsTransactionsRequestCls, GetStarsRevenueStatsRequestCls
    global AuthKeyUnregisteredError, RPCError

    if TelegramClientCls is not None:
        return

    telethon = import_module("telethon")
    sessions = import_module("telethon.sessions")
    payments_functions = import_module("telethon.tl.functions.payments")
    types_module = import_module("telethon.tl.types")
    tlobject_module = import_module("telethon.tl.tlobject")
    errors_module = import_module("telethon.errors")

    TelegramClientCls = telethon.TelegramClient
    StringSessionCls = sessions.StringSession
    MemorySessionCls = sessions.MemorySession
    GetStarsStatusRequestCls = payments_functions.GetStarsStatusRequest
    GetStarsTransactionsRequestCls = payments_functions.GetStarsTransactionsRequest
    GetStarsRevenueStatsRequestCls = getattr(payments_functions, "GetStarsRevenueStatsRequest", None)
    InputPeerSelfCls = types_module.InputPeerSelf
    TLObjectCls = tlobject_module.TLObject
    AuthKeyUnregisteredError = errors_module.AuthKeyUnregisteredError
    RPCError = errors_module.RPCError


@dataclass(slots=True)
class StarsTransaction:
    transaction_id: str
    stars: int
    occurred_at: datetime | None
    is_refund: bool
    title: str | None
    description: str | None
    peer_type: str | None
    peer_identifier: str | None


@dataclass(slots=True)
class StarsStatus:
    balance: int
    transactions: list[StarsTransaction]
    next_offset: str | None = None


@dataclass(slots=True)
class StarsRevenueStats:
    total_stars: int
    revenue_rub: Decimal
    currency: str
    raw: Dict[str, Any]


def _to_dict(obj: Any) -> Any:
    if TLObjectCls is not None and isinstance(obj, TLObjectCls):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {key: _to_dict(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_dict(item) for item in obj]
    return obj


def _coerce_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        # через str, чтобы избежать проблем с float
        return Decimal(str(value))
    except Exception:  # pragma: no cover - defensive
        return Decimal("0")


class TelegramMTProtoClient:
    """Thin synchronous wrapper around Telethon MTProto client for Stars APIs."""

    def __init__(
        self,
        *,
        api_id: int,
        api_hash: str,
        session: str | None = None,
        bot_token: str | None = None,
        test_mode: bool = False,
    ) -> None:
        if not api_id or not api_hash:
            raise RuntimeError("TELEGRAM_MT_API_ID and TELEGRAM_MT_API_HASH must be configured")
        self._api_id: int = api_id
        self._api_hash: str = api_hash
        self._session_string: str = session or ""
        self._bot_token: str | None = bot_token or None
        self._test_mode: bool = test_mode
        self._client: Any | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._previous_loop: asyncio.AbstractEventLoop | None = None
        self._peer: Any | None = None

    def __enter__(self) -> "TelegramMTProtoClient":
        _ensure_telethon()
        assert StringSessionCls is not None and MemorySessionCls is not None
        assert InputPeerSelfCls is not None and TelegramClientCls is not None

        self._loop = asyncio.new_event_loop()
        try:
            self._previous_loop = asyncio.get_event_loop()
        except RuntimeError:  # pragma: no cover - no running loop
            self._previous_loop = None
        asyncio.set_event_loop(self._loop)

        session = StringSessionCls(self._session_string) if self._session_string else MemorySessionCls()
        self._client = TelegramClientCls(
            session=session,
            api_id=self._api_id,
            api_hash=self._api_hash,
            device_model="NutriBot",
            app_version="1.0",
            system_version="Linux",
            lang_code="en",
            system_lang_code="en",
            use_ipv6=False,
            loop=self._loop,
            proxy=None,
            test_mode=self._test_mode,
        )
        self._peer = InputPeerSelfCls()
        self._loop.run_until_complete(self._connect())
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._client is not None and self._loop is not None:
            try:
                self._loop.run_until_complete(self._client.disconnect())
            except Exception:  # pragma: no cover - safety net
                logger.exception("Failed to disconnect MTProto client")
        if self._loop is not None:
            self._loop.close()
        if self._previous_loop is not None:
            asyncio.set_event_loop(self._previous_loop)
        else:
            try:
                asyncio.set_event_loop(asyncio.new_event_loop())
            except Exception:  # pragma: no cover - no support for resetting loop
                pass
        self._client = None
        self._loop = None
        self._previous_loop = None
        self._peer = None

    def get_stars_status(self) -> StarsStatus:
        return self._run(self._fetch_status)

    def get_stars_transactions(self, *, limit: int = 200, offset: str = "0") -> StarsStatus:
        return self._run(self._fetch_transactions, limit=limit, offset=offset)

    def get_stars_revenue_stats(self) -> StarsRevenueStats:
        if GetStarsRevenueStatsRequestCls is None:  # pragma: no cover - depends on Telethon release
            raise RuntimeError("GetStarsRevenueStatsRequest is not available in this Telethon version")
        return self._run(self._fetch_revenue_stats)

    async def _connect(self) -> None:
        assert self._client is not None
        assert AuthKeyUnregisteredError is not None
        try:
            await self._client.connect()
        except AuthKeyUnregisteredError:
            await self._client.disconnect()
            await self._client.connect()
        if not await self._client.is_user_authorized():
            if not self._bot_token:
                raise RuntimeError("MTProto session is not authorised; provide TELEGRAM_MT_SESSION or TELEGRAM_MT_BOT_TOKEN")
            await self._client.sign_in(bot_token=self._bot_token)
            if self._session_string and isinstance(self._client.session, StringSessionCls):
                self._session_string = self._client.session.save()

    def _run(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        if self._client is None or self._loop is None:
            raise RuntimeError("MTProto client is not connected")
        return self._loop.run_until_complete(func(*args, **kwargs))

    async def _fetch_status(self) -> StarsStatus:
        assert self._client is not None
        assert GetStarsStatusRequestCls is not None and self._peer is not None
        try:
            response = await self._client(GetStarsStatusRequestCls(peer=self._peer))
        except RPCError as exc:  # pragma: no cover - network issues
            logger.error("MTProto get_stars_status failed", exc_info=exc)
            raise
        return self._build_status(response)

    async def _fetch_transactions(self, *, limit: int, offset: str) -> StarsStatus:
        assert self._client is not None
        assert GetStarsTransactionsRequestCls is not None and self._peer is not None

        collected: list[StarsTransaction] = []
        balance: int = 0
        next_offset = offset or "0"
        seen_offsets: set[str] = set()
        desired = int(limit) if limit else 0

        while True:
            request_limit = desired if desired and desired < 200 else 200
            if next_offset in seen_offsets:
                break
            seen_offsets.add(next_offset)

            try:
                response = await self._client(
                    GetStarsTransactionsRequestCls(
                        peer=self._peer,
                        offset=next_offset,
                        limit=request_limit,
                        inbound=True,
                        outbound=True,
                    )
                )
            except RPCError as exc:  # pragma: no cover - network issues
                logger.error("MTProto get_stars_transactions failed", exc_info=exc)
                raise

            status = self._build_status(response)
            balance = status.balance
            next_offset = status.next_offset or "0"
            collected.extend(status.transactions)

            if desired and len(collected) >= desired:
                collected = collected[:desired]
                break

            if not status.transactions or not status.next_offset:
                break

            if desired:
                desired = max(desired - len(collected), 0)

        return StarsStatus(balance=balance, transactions=collected, next_offset=next_offset)

    async def _fetch_revenue_stats(self) -> StarsRevenueStats:
        assert self._client is not None and GetStarsRevenueStatsRequestCls is not None
        try:
            response = await self._client(GetStarsRevenueStatsRequestCls())
        except RPCError as exc:  # pragma: no cover
            logger.error("MTProto get_stars_revenue_stats failed", exc_info=exc)
            raise
        return self._build_revenue_stats(response)

    def _build_status(self, payload: Any) -> StarsStatus:
        raw_data = _to_dict(payload)
        data: Dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
        balance = int(data.get("balance") or 0)
        history = data.get("history") or []
        transactions = [self._build_transaction(item) for item in history]
        next_offset = data.get("next_offset")
        return StarsStatus(balance=balance, transactions=transactions, next_offset=next_offset)

    def _build_transaction(self, payload: Any) -> StarsTransaction:
        raw_data = _to_dict(payload)
        data: Dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
        peer = data.get("peer") or {}
        peer_type = peer.get("_") if isinstance(peer, dict) else None
        peer_identifier = peer.get("app_store") or peer.get("bot_id") or peer.get("fragment_id")
        timestamp = data.get("date")
        occurred_at = timestamp if isinstance(timestamp, datetime) else None
        return StarsTransaction(
            transaction_id=str(data.get("id") or ""),
            stars=int(data.get("stars") or 0),
            occurred_at=occurred_at,
            is_refund=bool(data.get("refund")),
            title=data.get("title"),
            description=data.get("description"),
            peer_type=peer_type,
            peer_identifier=str(peer_identifier) if peer_identifier is not None else None,
        )

    def _build_revenue_stats(self, payload: Any) -> StarsRevenueStats:
        raw_data = _to_dict(payload)
        data: Dict[str, Any] = raw_data if isinstance(raw_data, dict) else {}
        stars_sources: Iterable[Any] = []
        if "stars" in data:
            stars_sources = [data["stars"]]
        elif "periods" in data:
            periods = data.get("periods") or []
            stars_sources = [period.get("stars") for period in periods if isinstance(period, dict)]
        total_stars = 0
        for item in stars_sources:
            if isinstance(item, dict) and item.get("amount") is not None:
                total_stars += int(_coerce_decimal(item.get("amount")))
            elif isinstance(item, (int, float)):
                total_stars += int(item)
        revenue_info = data.get("revenue") or data.get("total_revenue") or data.get("revenue_rub") or {}
        if isinstance(revenue_info, dict):
            revenue_amount = _coerce_decimal(revenue_info.get("amount"))
            currency = str(revenue_info.get("currency") or "RUB")
        else:
            revenue_amount = _coerce_decimal(revenue_info)
            currency = "RUB"
        if not total_stars:
            total_stars = int(data.get("total_stars") or data.get("stars_total") or 0)
        if revenue_amount == 0 and data.get("total_revenue_rub"):
            revenue_amount = _coerce_decimal(data.get("total_revenue_rub"))
        return StarsRevenueStats(
            total_stars=total_stars,
            revenue_rub=revenue_amount,
            currency=currency,
            raw=data,
        )


__all__ = [
    "TelegramMTProtoClient",
    "StarsStatus",
    "StarsTransaction",
    "StarsRevenueStats",
]
