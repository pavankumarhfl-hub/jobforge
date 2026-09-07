from __future__ import annotations

import argparse
import json

from .queue import Queue
from .worker import run_worker


def main() -> int:
    parser = argparse.ArgumentParser(prog="jobforge")
    sub = parser.add_subparsers(dest="command", required=True)

    enqueue = sub.add_parser("enqueue", help="add a JSON job to the queue")
    enqueue.add_argument("payload")
    enqueue.add_argument("--db", default="jobforge.db")
    enqueue.add_argument("--delay", type=float, default=0)

    claim = sub.add_parser("claim", help="atomically claim one ready job")
    claim.add_argument("--db", default="jobforge.db")
    claim.add_argument("--lease", type=float, default=60)

    complete = sub.add_parser("complete", help="acknowledge a running job")
    complete.add_argument("job_id")
    complete.add_argument("--db", default="jobforge.db")

    fail = sub.add_parser("fail", help="fail a running job and optionally retry")
    fail.add_argument("job_id")
    fail.add_argument("--db", default="jobforge.db")
    fail.add_argument("--retry-delay", type=float, default=0)

    stats = sub.add_parser("stats", help="show queue counts")
    stats.add_argument("--db", default="jobforge.db")

    worker = sub.add_parser("worker", help="process queued jobs in batch mode")
    worker.add_argument("--db", default="jobforge.db")
    worker.add_argument("--max-jobs", type=int, default=1)

    args = parser.parse_args()
    queue = Queue(args.db)
    try:
        if args.command == "enqueue":
            print(queue.enqueue(json.loads(args.payload), args.delay))
        elif args.command == "claim":
            job = queue.claim(args.lease)
            print(json.dumps(job.__dict__ if job else None, sort_keys=True, default=str))
        elif args.command == "complete":
            queue.complete(args.job_id)
        elif args.command == "fail":
            queue.fail(args.job_id, args.retry_delay)
        elif args.command == "worker":
            # The CLI worker demonstrates the queue lifecycle. Applications should
            # use run_worker() with their own handler to execute real work.
            run_worker(
                queue,
                lambda job: print(json.dumps(job.payload, sort_keys=True)),
                max_jobs=args.max_jobs,
                stop_when_empty=True,
            )
        else:
            print(json.dumps(queue.stats(), sort_keys=True))
    finally:
        queue.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
