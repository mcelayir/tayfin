from typing import List
import pandas as pd
from ..db.engine import get_engine
from ..repositories.job_run_repository import JobRunRepository
from ..repositories.job_run_item_repository import JobRunItemRepository
from ..discovery.factory import create_provider
from ..discovery.repositories.instrument_repository import InstrumentRepository
from ..discovery.repositories.index_membership_repository import IndexMembershipRepository


class DiscoveryJob:
    def __init__(self, engine=None, target_cfg: dict | None = None, global_cfg: dict | None = None):
        self.engine = engine or get_engine()
        self.target_cfg = target_cfg or {}
        self.global_cfg = global_cfg or {}
        self.job_run_repo = JobRunRepository(self.engine)
        self.job_run_item_repo = JobRunItemRepository(self.engine)
        self.instrument_repo = InstrumentRepository(self.engine)
        self.index_membership_repo = IndexMembershipRepository(self.engine)

    @classmethod
    def from_config(cls, target_cfg: dict, global_cfg: dict | None = None):
        return cls(target_cfg=target_cfg, global_cfg=global_cfg)

    def run(self) -> List[dict]:
        # Create job run
        job_run_id = self.job_run_repo.create(job_name="discovery", trigger_type="MANUAL_CLI")

        provider = create_provider(self.target_cfg)
        try:
            provider_output = provider.discover(self.target_cfg)
            # Provider may return a pandas.DataFrame (preferred) or an iterable
            if isinstance(provider_output, pd.DataFrame):
                items = provider_output.to_dict(orient="records")
            else:
                items = list(provider_output)
        except Exception as e:
            # Finalize job run as FAILED with error details and re-raise
            self.job_run_repo.finalize(job_run_id=job_run_id, status="FAILED", items_total=0, items_succeeded=0, items_failed=0, error_summary=str(e), error_details=None)
            raise

        results = []
        succeeded = 0
        failed = 0

        for it in items:
            ticker = it.get("ticker")
            country = it.get("country", self.target_cfg.get("country"))
            index_code = it.get("index_code", self.target_cfg.get("index_code"))
            try:
                instrument_id = self.instrument_repo.upsert(ticker=ticker, country=country, instrument_type=it.get("instrument_type"), created_by_job_run_id=job_run_id)
                membership_id = self.index_membership_repo.upsert(index_code=index_code, instrument_id=instrument_id, country=country, effective_date=it.get("effective_date"), created_by_job_run_id=job_run_id)
                self.job_run_item_repo.upsert(job_run_id=job_run_id, item_key=ticker, status="SUCCESS")
                results.append({"ticker": ticker, "country": country, "index_code": index_code, "_status": "SUCCESS"})
                succeeded += 1
            except Exception as e:
                self.job_run_item_repo.upsert(job_run_id=job_run_id, item_key=ticker or "<unknown>", status="FAILED", error_summary=str(e))
                results.append({"ticker": ticker, "country": country, "index_code": index_code, "_status": "FAILED"})
                failed += 1

        total = len(items)
        final_status = "FAILED" if failed > 0 else "SUCCESS"
        self.job_run_repo.finalize(job_run_id=job_run_id, status=final_status, items_total=total, items_succeeded=succeeded, items_failed=failed)

        return results
