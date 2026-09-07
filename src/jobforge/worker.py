from __future__ import annotations

import time
from collections.abc import Callable

from .queue import Job, Queue

Handler = Callable[[Job], None]


def run_worker(
    queue: Queue,
    handler: Handler,
    *,
    lease_seconds: float = 60,
    poll_interval: float = 0.5,
    retry_delay: float = 1,
    max_jobs: int | None = None,
    stop_when_empty: bool = False,
) -> int:
    """Run a resilient worker.

    Handler exceptions mark the job failed; Queue decides whether it is retried or
    moved to the dead-letter state. Successful handlers are acknowledged.
    Set ``stop_when_empty=True`` for batch/CI workers; the default is a long-running
    polling loop suitable for a service process.
    """
    if poll_interval < 0:
        raise ValueError("poll_interval must be >= 0")
    if max_jobs is not None and max_jobs < 1:
        raise ValueError("max_jobs must be >= 1")

    processed = 0
    while max_jobs is None or processed < max_jobs:
        job = queue.claim(lease_seconds=lease_seconds)
        if job is None:
            if stop_when_empty:
                break
            if poll_interval:
                time.sleep(poll_interval)
            continue
        try:
            handler(job)
        except Exception:
            queue.fail(job.id, retry_delay=retry_delay)
        else:
            queue.complete(job.id)
        processed += 1
    return processed
