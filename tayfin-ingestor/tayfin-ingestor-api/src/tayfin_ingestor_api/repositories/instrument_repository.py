from sqlalchemy import text


class InstrumentRepository:
    def __init__(self, engine):
        self.engine = engine

    def resolve(self, ticker: str, country: str):
        stmt = text("SELECT id, ticker, country FROM tayfin_ingestor.instruments WHERE ticker = :ticker AND country = :country LIMIT 1")
        params = {"ticker": ticker, "country": country}
        with self.engine.connect() as conn:
            res = conn.execute(stmt, params)
            row = res.fetchone()
            if not row:
                return None
            return {"id": str(row[0]), "ticker": row[1], "country": row[2]}
