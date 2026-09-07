from __future__ import annotations

import argparse
import json

from .queue import Queue


def main() -> int:
    parser = argparse.ArgumentParser(prog="jobforge")
    sub = parser.add_subparsers(dest="command", required=True)

    enqueue = sub.add_parser("enqueue")
    enqueue.add_argument("payload")
    enqueue.add_argument("--db", default="jobforge.db")
    enqueue.add_argument("--delay", type=float, default=0)

    claim = sub.add_parser("claim")
    claim.add_argument("--db", default="jobforge.db")
    claim.add_argument("--lease", type=float, default=60)

    stats = sub.add_parser("stats")
    stats.add_argument("--db", default="jobforge.db")

    args = parser.parse_args()
    queue = Queue(args.db)
    try:
        if args.command == "enqueue":
            print(queue.enqueue(json.loads(args.payload), args.delay))
        elif args.command == "claim":
            job = queue.claim(args.lease)
            print(json.dumps(job.__dict__ if job else None, sort_keys=True, default=str))
        else:
            print(json.dumps(queue.stats(), sort_keys=True))
    finally:
        queue.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
