import time

from jobforge import Queue


def test_lifecycle_and_retry(tmp_path):
    q = Queue(tmp_path / "jobs.db", max_attempts=2)
    job_id = q.enqueue({"task": "demo"})
    job = q.claim(lease_seconds=30)
    assert job and job.id == job_id and job.attempts == 1
    q.fail(job_id)
    job = q.claim(lease_seconds=30)
    assert job and job.attempts == 2
    q.fail(job_id)
    assert q.stats()["dead"] == 1
    q.close()


def test_completed_job_is_not_claimed(tmp_path):
    q = Queue(tmp_path / "jobs.db")
    job_id = q.enqueue({"ok": True})
    job = q.claim()
    q.complete(job.id)
    assert q.claim() is None
    assert q.stats()["completed"] == 1
    q.close()


def test_expired_lease_is_recovered(tmp_path):
    q = Queue(tmp_path / "jobs.db")
    job_id = q.enqueue({"recover": True})
    job = q.claim(lease_seconds=0.01)
    assert job and job.id == job_id
    time.sleep(0.03)
    assert q.recover_expired() == 1
    recovered = q.claim()
    assert recovered and recovered.id == job_id
    q.close()


def test_delayed_job_is_not_ready(tmp_path):
    q = Queue(tmp_path / "jobs.db")
    q.enqueue({"later": True}, delay=60)
    assert q.claim() is None
    q.close()
