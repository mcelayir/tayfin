from sqlalchemy import text


class InstrumentQueryRepository:
    def __init__(self, engine):
        self.engine = engine

    def get_instruments_for_index(self, index_code: str, country: str) -> list[dict]:
        stmt = text(
            """
            SELECT i.id, i.ticker, i.country, i.exchange
            FROM tayfin_ingestor.index_memberships m
            JOIN tayfin_ingestor.instruments i ON i.id = m.instrument_id
            WHERE m.index_code = :index_code AND i.country = :country
            ORDER BY i.ticker
            """
        )
        with self.engine.connect() as conn:
            res = conn.execute(stmt, {"index_code": index_code, "country": country})
            rows = [dict(r._mapping) for r in res.fetchall()]
            return rows

    def get_instrument_by_ticker(self, ticker: str, country: str) -> dict | None:
        stmt = text(
            """
            SELECT id, ticker, country, exchange FROM tayfin_ingestor.instruments WHERE ticker = :ticker AND country = :country
            """
        )
        with self.engine.connect() as conn:
            res = conn.execute(stmt, {"ticker": ticker, "country": country})
            row = res.fetchone()
            return dict(row._mapping) if row else None
