# JobForge ⚙️

**A durable, SQLite-backed job queue for reliable background work.**

JobForge is a compact queue engine focused on atomic claiming, retries, leases, dead-letter jobs, and observable failure semantics without a network broker.

**Maintainer:** Pavan Kumar BN

## Uses

Use JobForge as a lightweight local queue for email delivery, webhook processing, report generation, AI tasks, file processing, and other background work where durability matters.

## Core capabilities

- Durable SQLite storage
- Atomic worker claiming
- Retry budgets and dead-letter state
- Lease expiry for crashed workers
- JSON payloads
- Queue statistics
- Python API and CLI
- Zero runtime dependencies

## Architecture

```text
Producer → SQLite queue → Worker
              │             ├─ success → completed
              │             └─ failure → retry → dead
              └─ lease expiry → queued
```

## Quick start

```bash
python -m pip install .
jobforge enqueue --db jobs.db '{"task":"send-email","user_id":42}'
jobforge claim --db jobs.db
jobforge stats --db jobs.db
```

Python:

```python
from jobforge import Queue

queue = Queue("jobs.db")
job_id = queue.enqueue({"task": "generate-report"})
job = queue.claim(lease_seconds=60)
if job:
    try:
        # perform the application-specific work here
        queue.complete(job.id)
    except Exception:
        queue.fail(job.id)
queue.close()
```

## Reliability model

`queued → running → completed`

Failures return a job to `queued` until the retry budget is exhausted, after which it becomes `dead`. A lease allows abandoned running jobs to be recovered after a worker crash.

## Optimization

JobForge favors correctness and predictable behavior over pretending to be a high-throughput distributed broker. Queue scans use indexes, claim operations use short SQLite transactions, WAL mode is enabled where supported, and the runtime has no external dependencies.

For large distributed production workloads, benchmark against a purpose-built broker/database before adopting this design.

## Security

JobForge never executes payloads. Applications must validate and authorize payloads before execution. Avoid storing credentials or unnecessary sensitive data in job payloads.

## Development

```bash
python -m pip install pytest
python -m pytest -q
```

CI covers Python 3.10, 3.11 and 3.12.

## Roadmap

- [x] Durable queue
- [x] Atomic claim
- [x] Retries and dead-letter state
- [x] Leases
- [x] CLI
- [x] Tests and CI
- [ ] Worker runtime with graceful shutdown
- [ ] Exponential backoff with jitter
- [ ] Heartbeats
- [ ] Priority and scheduled jobs
- [ ] Metrics and benchmarks
- [ ] Pluggable storage

## License

MIT
