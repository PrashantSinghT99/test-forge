import json
import sqlite3
import time
import os
from pathlib import Path
from typing import Dict, List, Optional

class FileLock:
    def __init__(self, lock_path: str, timeout: float = 10.0):
        self.lock_path = lock_path
        self.timeout = timeout
        self.locked = False

    def acquire(self):
        start_time = time.time()
        while True:
            try:
                self.fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                self.locked = True
                return True
            except FileExistsError:
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Could not acquire lock on {self.lock_path}")
                time.sleep(0.05)

    def release(self):
        if self.locked:
            try:
                os.close(self.fd)
                os.unlink(self.lock_path)
            except Exception:
                pass
            self.locked = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

class FlakyDetector:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.is_sqlite = self.db_path.suffix in (".db", ".sqlite", ".sqlite3")
        self.schema_version = "1.0"
        
        if self.is_sqlite:
            self._init_sqlite()

    def _init_sqlite(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS flaky_history (
                    test_id TEXT,
                    status TEXT,
                    timestamp REAL,
                    PRIMARY KEY (test_id, timestamp)
                )
            """)
            conn.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', ?)", (self.schema_version,))
            conn.commit()
        finally:
            conn.close()

    def _get_lock_path(self) -> str:
        return str(self.db_path) + ".lock"

    def load_history(self) -> Dict[str, List[str]]:
        if self.is_sqlite:
            history = {}
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT test_id, status FROM flaky_history ORDER BY timestamp ASC")
                for test_id, status in cursor.fetchall():
                    history.setdefault(test_id, []).append(status)
            finally:
                conn.close()
            return history
        else:
            lock_path = self._get_lock_path()
            with FileLock(lock_path):
                if self.db_path.exists():
                    try:
                        with open(self.db_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            return data.get("history", {})
                    except Exception:
                        return {}
                return {}

    def record_result(self, test_id: str, status: str, timestamp: float = None):
        if timestamp is None:
            timestamp = time.time()
        
        if self.is_sqlite:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO flaky_history (test_id, status, timestamp) VALUES (?, ?, ?)",
                    (test_id, status, timestamp)
                )
                conn.commit()
            finally:
                conn.close()
        else:
            lock_path = self._get_lock_path()
            with FileLock(lock_path):
                history = {}
                if self.db_path.exists():
                    try:
                        with open(self.db_path, "r", encoding="utf-8") as f:
                            history = json.load(f).get("history", {})
                    except Exception:
                        pass
                
                history.setdefault(test_id, []).append(status)
                history[test_id] = history[test_id][-20:]
                
                data = {
                    "schema_version": self.schema_version,
                    "history": history
                }
                with open(self.db_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

    def calculate_flaky_score(self, test_id: str) -> float:
        history = self.load_history()
        runs = history.get(test_id, [])
        if len(runs) < 3:
            return 0.0
        
        passes = runs.count("passed")
        failures = runs.count("failed")
        total = passes + failures
        if total == 0:
            return 0.0
        
        return (2.0 * min(passes, failures)) / total

    def is_flaky(self, test_id: str, threshold: float = 0.2) -> bool:
        return self.calculate_flaky_score(test_id) >= threshold

    def suggest_rerun(self, test_id: str, current_status: str) -> bool:
        if current_status != "failed":
            return False
        history = self.load_history()
        runs = history.get(test_id, [])
        if not runs:
            return False
        return "passed" in runs
