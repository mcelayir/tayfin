from sqlalchemy import text
from decimal import Decimal


def _dec(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        try:
            return float(v)
        except Exception:
            return str(v)
    return v


class FundamentalsRepository:
    def __init__(self, engine):
        self.engine = engine

    def resolve_instrument(self, ticker: str, country: str):
        stmt = text("SELECT id, ticker, country FROM tayfin_ingestor.instruments WHERE ticker = :ticker AND country = :country LIMIT 1")
        params = {"ticker": ticker, "country": country}
        with self.engine.connect() as conn:
            res = conn.execute(stmt, params)
            row = res.fetchone()
            if not row:
                return None
            return {"id": str(row[0]), "ticker": row[1], "country": row[2]}

    def get_latest_snapshot(self, instrument_id: str, source: str):
        stmt = text(
            "SELECT as_of_date, price, eps_ttm, bvps, standard_bvps, total_debt, total_equity, net_income_ttm, total_revenue, pe_ratio, pb_ratio, standard_pb_ratio, debt_equity, roe, net_margin, revenue_growth_yoy, earnings_growth_yoy FROM tayfin_ingestor.fundamentals_snapshots WHERE instrument_id = :instrument_id AND source = :source ORDER BY as_of_date DESC LIMIT 1"
        )
        params = {"instrument_id": instrument_id, "source": source}
        with self.engine.connect() as conn:
            res = conn.execute(stmt, params)
            row = res.fetchone()
            if not row:
                return None
            as_of = row[0]
            metrics = {
                "price": _dec(row[1]),
                "eps_ttm": _dec(row[2]),
                "bvps": _dec(row[3]),
                "standard_bvps": _dec(row[4]),
                "total_debt": _dec(row[5]),
                "total_equity": _dec(row[6]),
                "net_income_ttm": _dec(row[7]),
                "total_revenue": _dec(row[8]),
                "pe_ratio": _dec(row[9]),
                "pb_ratio": _dec(row[10]),
                "standard_pb_ratio": _dec(row[11]),
                "debt_equity": _dec(row[12]),
                "roe": _dec(row[13]),
                "net_margin": _dec(row[14]),
                "revenue_growth_yoy": _dec(row[15]),
                "earnings_growth_yoy": _dec(row[16]),
            }
            return {"as_of_date": as_of, "metrics": metrics}

    def get_snapshots_range(self, instrument_id: str, source: str, fr, to, limit: int, order: str):
        sql = "SELECT as_of_date, price, eps_ttm, bvps, standard_bvps, total_debt, total_equity, net_income_ttm, total_revenue, pe_ratio, pb_ratio, standard_pb_ratio, debt_equity, roe, net_margin, revenue_growth_yoy, earnings_growth_yoy FROM tayfin_ingestor.fundamentals_snapshots WHERE instrument_id = :instrument_id AND source = :source"
        if fr:
            sql += " AND as_of_date >= :fr"
        if to:
            sql += " AND as_of_date <= :to"
        sql += f" ORDER BY as_of_date { 'ASC' if order=='asc' else 'DESC' } LIMIT :limit"

        stmt = text(sql)
        params = {"instrument_id": instrument_id, "source": source, "limit": limit}
        if fr:
            params["fr"] = fr
        if to:
            params["to"] = to

        items = []
        with self.engine.connect() as conn:
            res = conn.execute(stmt, params)
            for row in res:
                items.append({
                    "as_of_date": row[0].isoformat(),
                    "price": _dec(row[1]),
                    "eps_ttm": _dec(row[2]),
                    "bvps": _dec(row[3]),
                    "standard_bvps": _dec(row[4]),
                    "total_debt": _dec(row[5]),
                    "total_equity": _dec(row[6]),
                    "net_income_ttm": _dec(row[7]),
                    "total_revenue": _dec(row[8]),
                    "pe_ratio": _dec(row[9]),
                    "pb_ratio": _dec(row[10]),
                    "standard_pb_ratio": _dec(row[11]),
                    "debt_equity": _dec(row[12]),
                    "roe": _dec(row[13]),
                    "net_margin": _dec(row[14]),
                    "revenue_growth_yoy": _dec(row[15]),
                    "earnings_growth_yoy": _dec(row[16]),
                })
        return items
