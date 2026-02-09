from sqlalchemy import text


class FundamentalsSnapshotRepository:
    def __init__(self, engine):
        self.engine = engine

    def upsert(self, instrument_id: str, as_of_date, source: str, metrics: dict, created_by_job_run_id: str, updated_by_job_run_id: str | None = None) -> str:
        # Build the insert statement with explicit metric columns
        stmt = text(
            """
            INSERT INTO tayfin_ingestor.fundamentals_snapshots (
              instrument_id, as_of_date, source,
              price, eps_ttm, bvps, standard_bvps, total_debt, total_equity, net_income_ttm, total_revenue,
              pe_ratio, pb_ratio, standard_pb_ratio, debt_equity, roe, net_margin, revenue_growth_yoy, earnings_growth_yoy,
              created_at, updated_at, created_by_job_run_id, updated_by_job_run_id
            ) VALUES (
              :instrument_id, :as_of_date, :source,
              :price, :eps_ttm, :bvps, :standard_bvps, :total_debt, :total_equity, :net_income_ttm, :total_revenue,
              :pe_ratio, :pb_ratio, :standard_pb_ratio, :debt_equity, :roe, :net_margin, :revenue_growth_yoy, :earnings_growth_yoy,
              now(), now(), :created_by_job_run_id, :updated_by_job_run_id
            )
            ON CONFLICT (instrument_id, as_of_date, source) DO UPDATE SET
              price = EXCLUDED.price,
              eps_ttm = EXCLUDED.eps_ttm,
              bvps = EXCLUDED.bvps,
              standard_bvps = EXCLUDED.standard_bvps,
              total_debt = EXCLUDED.total_debt,
              total_equity = EXCLUDED.total_equity,
              net_income_ttm = EXCLUDED.net_income_ttm,
              total_revenue = EXCLUDED.total_revenue,
              pe_ratio = EXCLUDED.pe_ratio,
              pb_ratio = EXCLUDED.pb_ratio,
              standard_pb_ratio = EXCLUDED.standard_pb_ratio,
              debt_equity = EXCLUDED.debt_equity,
              roe = EXCLUDED.roe,
              net_margin = EXCLUDED.net_margin,
              revenue_growth_yoy = EXCLUDED.revenue_growth_yoy,
              earnings_growth_yoy = EXCLUDED.earnings_growth_yoy,
              updated_at = now(),
              updated_by_job_run_id = EXCLUDED.updated_by_job_run_id
            RETURNING id
            """
        )

        params = {
            "instrument_id": instrument_id,
            "as_of_date": as_of_date,
            "source": source,
            "price": metrics.get("price"),
            "eps_ttm": metrics.get("eps_ttm"),
            "bvps": metrics.get("bvps"),
            "standard_bvps": metrics.get("standard_bvps"),
            "total_debt": metrics.get("total_debt"),
            "total_equity": metrics.get("total_equity"),
            "net_income_ttm": metrics.get("net_income_ttm"),
            "total_revenue": metrics.get("total_revenue"),
            "pe_ratio": metrics.get("pe_ratio"),
            "pb_ratio": metrics.get("pb_ratio"),
            "standard_pb_ratio": metrics.get("standard_pb_ratio"),
            "debt_equity": metrics.get("debt_equity"),
            "roe": metrics.get("roe"),
            "net_margin": metrics.get("net_margin"),
            "revenue_growth_yoy": metrics.get("revenue_growth_yoy"),
            "earnings_growth_yoy": metrics.get("earnings_growth_yoy"),
            "created_by_job_run_id": created_by_job_run_id,
            "updated_by_job_run_id": updated_by_job_run_id,
        }

        with self.engine.begin() as conn:
            res = conn.execute(stmt, params)
            row = res.fetchone()
            return str(row[0])
