from typing import List
from ..db.engine import get_engine
from ..repositories.job_run_repository import JobRunRepository
from ..repositories.job_run_item_repository import JobRunItemRepository
from ..fundamentals.repositories.instrument_query_repository import InstrumentQueryRepository
from ..fundamentals.repositories.fundamentals_snapshot_repository import FundamentalsSnapshotRepository
from ..fundamentals.factory import create_provider
from datetime import date
import pandas as pd


METRIC_KEYS = [
    "price",
    "eps_ttm",
    "bvps",
    "standard_bvps",
    "total_debt",
    "total_equity",
    "net_income_ttm",
    "total_revenue",
    "pe_ratio",
    "pb_ratio",
    "standard_pb_ratio",
    "debt_equity",
    "roe",
    "net_margin",
    "revenue_growth_yoy",
    "earnings_growth_yoy",
]


class FundamentalsJob:
    def __init__(self, engine=None, target_cfg: dict | None = None, global_cfg: dict | None = None):
        self.engine = engine or get_engine()
        self.target_cfg = target_cfg or {}
        self.global_cfg = global_cfg or {}
        self.job_run_repo = JobRunRepository(self.engine)
        self.job_run_item_repo = JobRunItemRepository(self.engine)
        self.instrument_query_repo = InstrumentQueryRepository(self.engine)
        self.snapshot_repo = FundamentalsSnapshotRepository(self.engine)

    @classmethod
    def from_config(cls, target_cfg: dict, global_cfg: dict | None = None):
        return cls(target_cfg=target_cfg, global_cfg=global_cfg)

    def run(self, ticker: str | None = None) -> List[dict]:
        job_run_id = self.job_run_repo.create(job_name="fundamentals", trigger_type="MANUAL_CLI")

        # Resolve instruments list
        instruments = []
        country = self.target_cfg.get("country")
        if ticker:
            # Upsert instrument via existing discovery repository pattern
            from ..discovery.repositories.instrument_repository import InstrumentRepository

            instr_repo = InstrumentRepository(self.engine)
            instrument_id = instr_repo.upsert(ticker=ticker, country=country, instrument_type=None, created_by_job_run_id=job_run_id)
            instruments = [{"id": instrument_id, "ticker": ticker, "country": country}]
        else:
            if self.target_cfg.get("kind") == "index":
                index_code = self.target_cfg.get("index_code")
                instruments = self.instrument_query_repo.get_instruments_for_index(index_code=index_code, country=country)

        provider = create_provider(country=country)

        results = []
        succeeded = 0
        failed = 0

        for inst in instruments:
            t = inst.get("ticker")
            try:
                metrics = provider.compute(t, inst.get("country"))
                if not metrics:
                    raise RuntimeError("provider returned no metrics")

                # If provider produced metrics, persist snapshot
                as_of = metrics.get("as_of_date") or date.today()
                source = metrics.get("source") or "stockdex_yahoo"

                # insert-only: only create if no snapshot for that day+source exists
                if self.snapshot_repo.exists_for(instrument_id=inst.get("id"), as_of_date=as_of, source=source):
                    # Already exists for the day -> mark as skipped (don't update existing)
                    self.job_run_item_repo.upsert(job_run_id=job_run_id, item_key=t, status="SKIPPED")
                    row = {
                        "ticker": t,
                        "as_of_date": as_of,
                        "source": source,
                        "_status": "SKIPPED",
                    }
                    for k in METRIC_KEYS:
                        row[k] = None
                    results.append(row)
                else:
                    inserted_id = self.snapshot_repo.insert(instrument_id=inst.get("id"), as_of_date=as_of, source=source, metrics=metrics, created_by_job_run_id=job_run_id)
                    self.job_run_item_repo.upsert(job_run_id=job_run_id, item_key=t, status="SUCCESS")

                    row = {
                        "ticker": t,
                        "as_of_date": as_of,
                        "source": source,
                        "_status": "SUCCESS",
                    }
                    for k in METRIC_KEYS:
                        row[k] = metrics.get(k) if metrics else None
                    results.append(row)
                succeeded += 1
            except Exception as e:
                # record failure and surface the error to stdout for debugging
                try:
                    self.job_run_item_repo.upsert(job_run_id=job_run_id, item_key=t or "<unknown>", status="FAILED", error_summary=str(e))
                except Exception:
                    pass
                print(f"[fundamentals] ticker={t} failed: {e}", flush=True)
                row = {"ticker": t, "as_of_date": None, "source": None, "_status": "FAILED"}
                for k in METRIC_KEYS:
                    row[k] = None
                results.append(row)
                failed += 1

        # Print summary DataFrame of results
        try:
            df = pd.DataFrame(results)
            print(df)
        except Exception:
            pass

        total = len(instruments)
        final_status = "FAILED" if failed > 0 else "SUCCESS"
        self.job_run_repo.finalize(job_run_id=job_run_id, status=final_status, items_total=total, items_succeeded=succeeded, items_failed=failed)

        return results
