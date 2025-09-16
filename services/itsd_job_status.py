import os
import time
import uuid
from typing import Any, Dict, Optional

import redis


def _redis_client() -> redis.Redis:
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD")
    db = int(os.getenv("REDIS_AUTH_DB", "0"))
    return redis.Redis(host=host, port=port, password=password, db=db, decode_responses=True)


class JobStatusStore:
    """Lightweight job status storage backed by Redis.

    Keys:
      job:{job_id} -> hash
        fields: status, created_at, updated_at, task, filename, error, result_json
    """

    def __init__(self) -> None:
        self.r = _redis_client()

    def _key(self, job_id: str) -> str:
        return f"job:{job_id}"

    def create_job(self, task: str, filename: Optional[str] = None) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex
        now = str(int(time.time()))
        key = self._key(job_id)
        self.r.hset(key, mapping={
            "status": "queued",
            "task": task,
            "filename": filename or "",
            "created_at": now,
            "updated_at": now,
        })
        # Expire after 24h by default
        self.r.expire(key, int(os.getenv("JOB_STATUS_TTL_SECONDS", "86400")))
        return {"job_id": job_id, "status": "queued"}

    def start_job(self, job_id: str) -> None:
        now = str(int(time.time()))
        self.r.hset(self._key(job_id), mapping={"status": "running", "updated_at": now})

    def complete_job(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        import json
        now = str(int(time.time()))
        mapping = {"status": "completed", "updated_at": now}
        if result is not None:
            mapping["result_json"] = json.dumps(result, ensure_ascii=False)
        self.r.hset(self._key(job_id), mapping=mapping)

    def fail_job(self, job_id: str, error: str) -> None:
        now = str(int(time.time()))
        self.r.hset(self._key(job_id), mapping={"status": "failed", "error": error, "updated_at": now})

    def set_progress(self, job_id: str, progress: float | int, stage: Optional[str] = None) -> None:
        """Update progress (0-100) and optional stage text for a job."""
        try:
            p = float(progress)
        except Exception:
            p = 0.0
        p = max(0.0, min(100.0, p))
        now = str(int(time.time()))
        mapping: Dict[str, Any] = {"progress": str(int(p)), "updated_at": now}
        if stage is not None:
            mapping["stage"] = stage
        self.r.hset(self._key(job_id), mapping=mapping)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        import json
        data = self.r.hgetall(self._key(job_id))
        if not data:
            return None
        out: Dict[str, Any] = dict(data)
        if "result_json" in out:
            try:
                out["result"] = json.loads(out["result_json"]) if out.get("result_json") else None
            except Exception:
                out["result"] = None
        return out
