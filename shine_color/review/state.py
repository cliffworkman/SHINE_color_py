"""Transactional, versioned local human judgments, bound to exact image pairs."""

import json
import sqlite3
from contextlib import contextmanager
from .project import STATUSES, now


class ConflictError(ValueError):
    pass


class ReviewState:
    def __init__(self, report):
        self.report = report
        self.path = report.root / "review.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (sequence INTEGER PRIMARY KEY, payload TEXT NOT NULL);
            """)
            existing = db.execute(
                "SELECT value FROM metadata WHERE key='project_id'"
            ).fetchone()
            if existing and existing[0] != report.data["project_id"]:
                raise ValueError("Review database belongs to different report")
            db.execute(
                "INSERT OR IGNORE INTO metadata VALUES ('project_id',?)",
                (report.data["project_id"],),
            )

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db
        finally:
            db.close()

    def snapshot(self):
        with self.connect() as db:
            db.execute("BEGIN")
            decisions = {
                k: json.loads(v)
                for k, v in db.execute("SELECT id,payload FROM decisions")
            }
            events = [
                json.loads(v)
                for (v,) in db.execute("SELECT payload FROM events ORDER BY sequence")
            ]
        return dict(
            schema_version=1,
            project_id=self.report.data["project_id"],
            decisions=decisions,
            events=events,
        )

    def save(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Expected review object")
        if payload.get("project_id") != self.report.data["project_id"]:
            raise ValueError("Wrong project")
        sid = payload.get("stimulus_id")
        item = next(
            (x for x in self.report.data["stimuli"] if x["stimulus_id"] == sid), None
        )
        if not item or payload.get("pair_id") != item["pair_id"]:
            raise ValueError("Unknown or changed image pair")
        if payload.get("status") not in STATUSES:
            raise ValueError("Invalid status")
        if not isinstance(payload.get("note"), str) or len(payload["note"]) > 20000:
            raise ValueError("Invalid note")
        if (
            not isinstance(payload.get("reviewer"), str)
            or len(payload["reviewer"]) > 200
        ):
            raise ValueError("Invalid reviewer")
        if type(payload.get("revision")) is not int or payload["revision"] < 0:
            raise ValueError("Invalid revision")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT payload FROM decisions WHERE id=?", (sid,)
            ).fetchone()
            previous = json.loads(old[0]) if old else None
            revision = previous["revision"] if previous else 0
            if payload["revision"] != revision:
                raise ConflictError(
                    "Another tab changed this decision; reload before editing"
                )
            result = {
                key: payload[key] for key in ("status", "note", "reviewer", "pair_id")
            }
            result.update(revision=revision + 1, updated_at=now())
            db.execute(
                "INSERT OR REPLACE INTO decisions VALUES (?,?)",
                (sid, json.dumps(result)),
            )
            event = dict(stimulus_id=sid, previous=previous, decision=result)
            db.execute("INSERT INTO events(payload) VALUES (?)", (json.dumps(event),))
        return result
