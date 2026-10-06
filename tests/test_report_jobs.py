import tempfile
import unittest
from threading import Event
from report_jobs import ReportJobs

SEARCH = ("jeanpaulboerekamps", "2025-01-01", "2025-01-10", "00:00", "23:59", False, "Reis")


class JobTests(unittest.TestCase):
    def test_fresh_calculation_calls_builder_again_and_old_result_survives(self):
        calls = []
        def builder(search, progress):
            calls.append(search)
            return {"meta": {"species": len(calls)}}
        with tempfile.TemporaryDirectory() as directory:
            jobs = ReportJobs(directory, builder)
            try:
                first = jobs.start(SEARCH)
                jobs.pool.submit(lambda: None).result(timeout=5)
                # Join all submitted tasks, then use a new executor for the next run.
                jobs.pool.shutdown(wait=True)
                from concurrent.futures import ThreadPoolExecutor
                jobs.pool = ThreadPoolExecutor(max_workers=2)
                self.assertEqual(jobs.start(SEARCH), first)
                second = jobs.start(SEARCH, fresh=True)
                jobs.pool.shutdown(wait=True)
                self.assertNotEqual(first, second)
                self.assertEqual(len(calls), 2)
                self.assertEqual(jobs.snapshot(first)["result"]["meta"]["species"], 1)
                self.assertEqual(jobs.snapshot(second)["result"]["meta"]["species"], 2)
                self.assertEqual(jobs.resume(first), first)
                self.assertEqual(jobs.settings(first), SEARCH)
            finally:
                jobs.pool.shutdown(wait=True)

    def test_fresh_reuses_running_job_instead_of_starting_duplicate(self):
        release = Event()
        def builder(search, progress):
            release.wait(5)
            return {"meta": {}}
        with tempfile.TemporaryDirectory() as directory:
            jobs = ReportJobs(directory, builder)
            try:
                first = jobs.start(SEARCH, fresh=True)
                self.assertEqual(jobs.start(SEARCH, fresh=True), first)
            finally:
                release.set()
                jobs.pool.shutdown(wait=True)


if __name__ == "__main__":
    unittest.main()
