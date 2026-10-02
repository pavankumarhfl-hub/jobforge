from __future__ import annotations

import argparse
import gc
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from jobforge import Queue


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((p / 100) * (len(ordered) - 1)))))
    return ordered[index]


def run(workers: int, jobs: int, payload_size: int) -> dict[str, float | int]:
    payload = {"task": "benchmark", "data": "x" * payload_size}
    with tempfile.TemporaryDirectory(prefix="jobforge-benchmark-") as tmp:
        db = Path(tmp) / "jobs.db"
        queue = Queue(db)
        try:
            gc.collect()
            start = time.perf_counter()
            for _ in range(jobs):
                queue.enqueue(payload)
            enqueue_seconds = time.perf_counter() - start
        finally:
            queue.close()

        def worker() -> list[float]:
            local: list[float] = []
            worker_queue = Queue(db)
            try:
                while True:
                    claimed_at = time.perf_counter()
                    job = worker_queue.claim(lease_seconds=120)
                    if job is None:
                        return local
                    local.append(time.perf_counter() - claimed_at)
                    worker_queue.complete(job.id)
            finally:
                worker_queue.close()

        start = time.perf_counter()
        latencies: list[float] = []
        processed = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for values in pool.map(lambda _: worker(), range(workers)):
                latencies.extend(values)
                processed += len(values)
        process_seconds = time.perf_counter() - start

        if processed != jobs:
            raise RuntimeError(f"processed {processed} jobs, expected {jobs}")

        verification = Queue(db)
        try:
            stats = verification.stats()
        finally:
            verification.close()
        if stats["completed"] != jobs or stats["queued"] != 0 or stats["running"] != 0:
            raise RuntimeError(f"unexpected final queue state: {stats}")

        return {
            "workers": workers,
            "jobs": jobs,
            "enqueue_jobs_per_sec": jobs / enqueue_seconds if enqueue_seconds else 0.0,
            "complete_jobs_per_sec": jobs / process_seconds if process_seconds else 0.0,
            "claim_p50_ms": percentile([x * 1000 for x in latencies], 50),
            "claim_p95_ms": percentile([x * 1000 for x in latencies], 95),
            "claim_p99_ms": percentile([x * 1000 for x in latencies], 99),
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark JobForge queue throughput and claim latency.")
    parser.add_argument("--jobs", type=int, default=10_000)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--payload-size", type=int, default=128)
    args = parser.parse_args()

    if args.jobs < 1 or args.workers < 1 or args.payload_size < 0:
        raise SystemExit("jobs and workers must be >= 1; payload-size must be >= 0")

    result = run(args.workers, args.jobs, args.payload_size)
    print(f"JobForge benchmark | jobs={result['jobs']} workers={result['workers']}")
    print(f"enqueue: {result['enqueue_jobs_per_sec']:.2f} jobs/s")
    print(f"complete: {result['complete_jobs_per_sec']:.2f} jobs/s")
    print(f"claim p50: {result['claim_p50_ms']:.3f} ms")
    print(f"claim p95: {result['claim_p95_ms']:.3f} ms")
    print(f"claim p99: {result['claim_p99_ms']:.3f} ms")


if __name__ == "__main__":
    main()
