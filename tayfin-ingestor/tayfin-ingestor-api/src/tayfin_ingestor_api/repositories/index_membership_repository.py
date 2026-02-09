from sqlalchemy import text


class IndexMembershipRepository:
    def __init__(self, engine):
        self.engine = engine

    def get_members(self, index_code: str, country: str | None, limit: int, order: str):
        sql = "SELECT im.instrument_id, i.ticker, i.country FROM tayfin_ingestor.index_memberships im JOIN tayfin_ingestor.instruments i ON im.instrument_id = i.id WHERE im.index_code = :index_code"
        params = {"index_code": index_code}
        if country:
            sql += " AND i.country = :country"
            params["country"] = country
        sql += f" ORDER BY i.ticker {'ASC' if order=='asc' else 'DESC'} LIMIT :limit"
        params["limit"] = limit

        items = []
        stmt = text(sql)
        with self.engine.connect() as conn:
            res = conn.execute(stmt, params)
            for row in res:
                items.append({"instrument_id": str(row[0]), "symbol": row[1], "country": row[2]})
        return items

    def get_indices_for_instrument(self, instrument_id: str, limit: int):
        sql = "SELECT index_code FROM tayfin_ingestor.index_memberships WHERE instrument_id = :instrument_id LIMIT :limit"
        params = {"instrument_id": instrument_id, "limit": limit}
        items = []
        stmt = text(sql)
        with self.engine.connect() as conn:
            res = conn.execute(stmt, params)
            for row in res:
                items.append({"index_code": row[0]})
        return items
