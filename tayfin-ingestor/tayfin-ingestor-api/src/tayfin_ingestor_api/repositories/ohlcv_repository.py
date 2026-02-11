"""OHLCV read-only repository for the ingestor API."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import text


def _dec(v):
    """Convert Decimal to float for JSON serialisation."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        try:
            return float(v)
        except Exception:
            return str(v)
    return v


def _row_to_dict(row) -> dict:
    """Map a (ticker, as_of_date, open, high, low, close, volume, source) row."""
    return {
        "ticker": row[0],
        "as_of_date": row[1].isoformat() if hasattr(row[1], "isoformat") else str(row[1]),
        "open": _dec(row[2]),
        "high": _dec(row[3]),
        "low": _dec(row[4]),
        "close": _dec(row[5]),
        "volume": row[6],
        "source": row[7],
    }


class OhlcvRepository:
    def __init__(self, engine):
        self.engine = engine

    # ------------------------------------------------------------------
    # Instrument resolution (duplicated to keep API context self-contained)
    # ------------------------------------------------------------------

    def _resolve_instrument_id(self, ticker: str, country: str = "US") -> str | None:
        stmt = text(
            "SELECT id FROM tayfin_ingestor.instruments "
            "WHERE ticker = :ticker AND country = :country "
            "LIMIT 1"
        )
        with self.engine.connect() as conn:
            row = conn.execute(stmt, {"ticker": ticker, "country": country}).fetchone()
            return str(row[0]) if row else None

    # ------------------------------------------------------------------
    # 1) Latest candle for a single ticker
    # ------------------------------------------------------------------

    def get_latest_by_ticker(self, ticker: str, country: str = "US") -> dict | None:
        instrument_id = self._resolve_instrument_id(ticker, country)
        if not instrument_id:
            return None

        stmt = text(
            "SELECT i.ticker, o.as_of_date, o.open, o.high, o.low, o.close, o.volume, o.source "
            "FROM tayfin_ingestor.ohlcv_daily o "
            "JOIN tayfin_ingestor.instruments i ON o.instrument_id = i.id "
            "WHERE o.instrument_id = :instrument_id "
            "ORDER BY o.as_of_date DESC "
            "LIMIT 1"
        )
        with self.engine.connect() as conn:
            row = conn.execute(stmt, {"instrument_id": instrument_id}).fetchone()
            if not row:
                return None
            return _row_to_dict(row)

    # ------------------------------------------------------------------
    # 2) Time-range for a single ticker
    # ------------------------------------------------------------------

    def get_range_by_ticker(
        self,
        ticker: str,
        from_date: date | None = None,
        to_date: date | None = None,
        country: str = "US",
    ) -> list[dict] | None:
        """Return candles in ascending date order, or None if instrument not found."""
        instrument_id = self._resolve_instrument_id(ticker, country)
        if not instrument_id:
            return None  # instrument not found

        sql = (
            "SELECT i.ticker, o.as_of_date, o.open, o.high, o.low, o.close, o.volume, o.source "
            "FROM tayfin_ingestor.ohlcv_daily o "
            "JOIN tayfin_ingestor.instruments i ON o.instrument_id = i.id "
            "WHERE o.instrument_id = :instrument_id"
        )
        params: dict = {"instrument_id": instrument_id}

        if from_date:
            sql += " AND o.as_of_date >= :from_date"
            params["from_date"] = from_date
        if to_date:
            sql += " AND o.as_of_date <= :to_date"
            params["to_date"] = to_date

        sql += " ORDER BY o.as_of_date ASC"

        items: list[dict] = []
        with self.engine.connect() as conn:
            for row in conn.execute(text(sql), params):
                items.append(_row_to_dict(row))
        return items

    # ------------------------------------------------------------------
    # 3) Latest candle per member of an index
    # ------------------------------------------------------------------

    def get_latest_by_index(self, index_code: str) -> list[dict]:
        """Per-ticker latest candle for every index member that has OHLCV data.

        Uses Postgres ``DISTINCT ON`` for an efficient single-pass query.
        """
        stmt = text(
            "SELECT DISTINCT ON (o.instrument_id) "
            "  i.ticker, o.as_of_date, o.open, o.high, o.low, o.close, o.volume, o.source "
            "FROM tayfin_ingestor.index_memberships im "
            "JOIN tayfin_ingestor.ohlcv_daily o ON o.instrument_id = im.instrument_id "
            "JOIN tayfin_ingestor.instruments i ON i.id = im.instrument_id "
            "WHERE im.index_code = :index_code "
            "ORDER BY o.instrument_id, o.as_of_date DESC"
        )
        items: list[dict] = []
        with self.engine.connect() as conn:
            for row in conn.execute(stmt, {"index_code": index_code}):
                items.append(_row_to_dict(row))
        return items
