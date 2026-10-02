# JobForge Benchmark Methodology

JobForge does not publish performance numbers until they are measured from the benchmark harness in this repository.

## What is measured

- enqueue throughput
- completion throughput with multiple worker threads
- claim latency at p50, p95, and p99
- final queue-state correctness after concurrent processing

## Running the benchmark

```bash
python benchmarks/queue_benchmark.py --jobs 10000 --workers 4
```

For a worker-scaling experiment:

```bash
for workers in 1 2 4 8 16; do
  python benchmarks/queue_benchmark.py --jobs 10000 --workers "$workers"
done
```

## Reporting rules

Benchmark results must record:

- operating system
- Python version
- CPU model and core count
- RAM
- JobForge commit SHA
- job count
- worker count
- payload size
- enqueue throughput
- completion throughput
- p50/p95/p99 claim latency

Do not compare results from different machines as if they were controlled experiments. Treat results as machine-specific unless the environment is held constant.

## What this benchmark does not prove

The benchmark does not establish production suitability, distributed scalability, durability under hardware failure, or performance against dedicated message brokers. Those are separate engineering questions and require separate experiments.
