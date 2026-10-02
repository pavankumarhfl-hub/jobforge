# JobForge ⚙️

**A durable, SQLite-backed job queue for reliable background work.**

JobForge is a compact queue engine focused on atomic claiming, retries, leases, dead-letter jobs, delayed work, and explicit failure semantics without requiring a network broker.

**Maintainer:** Pavan Kumar BN

## Why JobForge exists

Many applications need durable background work but do not always need a network message broker. JobForge explores the engineering trade-offs of a small embedded queue: transactional claiming, worker leases, retry budgets, and crash recovery using SQLite.

It is intentionally **not** presented as a replacement for Kafka, RabbitMQ, SQS, or other distributed brokers.

## Core capabilities

- Durable SQLite storage
- Atomic worker claiming
- Retry budgets and dead-letter state
- Lease expiry for crashed workers
- Delayed jobs
- JSON payloads
- Queue statistics
- Python API and CLI
- Zero runtime dependencies
- WAL mode and indexed ready/lease lookups

## Architecture

```text
Producer → SQLite queue → Worker
              │             ├─ success → completed
              │             └─ failure → retry → dead
              └─ lease expiry → queued
```

## Reliability model

```text
queued → running → completed
   ↑        │
   │        ├─ failure → queued → retry
   │        │                    └→ dead
   │        └─ lease expiry → queued
   └─ delayed availability
```

A job is claimed inside a short SQLite write transaction. A lease records ownership for a bounded period. If a worker disappears before completion, an expired lease can return the job to the queue.

The retry budget prevents an endlessly failing job from being retried forever.

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
        # perform application-specific work here
        queue.complete(job.id)
    except Exception:
        queue.fail(job.id)
queue.close()
```

## Engineering trade-offs

### Why SQLite?

SQLite provides transactional semantics, durable local storage, indexing, and a small operational footprint. The trade-off is that write contention and single-node storage impose limits that a distributed broker is designed to avoid.

### Why leases instead of permanent ownership?

A worker can disappear without completing a job. Leases make ownership time-bounded so abandoned work can be recovered.

### Why keep payload execution outside JobForge?

The queue stores and coordinates work; it does not execute arbitrary payloads. Applications remain responsible for validation, authorization, idempotency, and execution safety.

### Why no distributed broker?

That is deliberate. The project is an engineering study of durable local work queues, not an attempt to disguise SQLite as a distributed messaging system.

## Performance and benchmarks

JobForge does not publish fabricated throughput claims. Reproducible benchmark code lives in `benchmarks/queue_benchmark.py` and the methodology is documented in [`docs/benchmarks.md`](docs/benchmarks.md).

Example:

```bash
python benchmarks/queue_benchmark.py --jobs 10000 --workers 4
```

The benchmark measures enqueue throughput, concurrent completion throughput, claim latency at p50/p95/p99, and final queue-state correctness.

Results must be reported with the machine, Python version, payload size, worker count, job count, and commit SHA. Numbers from different environments should not be treated as directly comparable.

## Security

JobForge never executes payloads. Applications must validate and authorize payloads before execution. Avoid storing credentials or unnecessary sensitive data in job payloads.

## Testing

```bash
python -m pip install pytest
python -m pytest -q
```

Tests cover lifecycle transitions, retries, completed-job behavior, delayed jobs, lease recovery, and worker execution.

## Development roadmap

- [x] Durable queue
- [x] Atomic claim
- [x] Retries and dead-letter state
- [x] Leases
- [x] Delayed jobs
- [x] CLI
- [x] Tests and CI
- [x] Reproducible benchmark harness
- [ ] Worker runtime with graceful shutdown
- [ ] Exponential backoff with jitter
- [ ] Heartbeats
- [ ] Priority scheduling
- [ ] Metrics and tracing
- [ ] Failure-injection test suite
- [ ] Pluggable storage interface

## Limitations

JobForge is currently a local SQLite-backed queue. It should not be described as a horizontally scalable distributed broker. Applications with multi-node, high-throughput, or cross-region requirements should benchmark dedicated messaging/storage systems against their workload.

## License

MIT
