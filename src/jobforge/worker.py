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
) -> int:
    """Run a resilient single-process worker until stopped or max_jobs is reached.

    Handler exceptions mark the job failed; Queue decides whether it is retried or
    moved to the dead-letter state. Successfully handled jobs are acknowledged.
    """
    if poll_interval < 0:
        raise ValueError("poll_interval must be >= 0")
    processed = 0
    while max_jobs is None or processed < max_jobs:
        job = queue.claim(lease_seconds=lease_seconds)
        if job is None:
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
