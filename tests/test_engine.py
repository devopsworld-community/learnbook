"""Engine tests. Run: python3 -m unittest discover -s tests  (or make test)."""

import http.client
import json
import shutil
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from learnbook import core, server


class Isolated(unittest.TestCase):
    """Each test gets its own workspace and progress file, so a learner's real progress is never touched."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._saved = (core.WORKSPACE, core.STATE_DIR, core.PROGRESS_FILE)
        core.WORKSPACE = self.tmp / "workspace"
        core.STATE_DIR = self.tmp / "state"
        core.PROGRESS_FILE = core.STATE_DIR / "progress.json"
        self.track = core.load_track(core.ready_tracks()[0])

    def tearDown(self):
        core.WORKSPACE, core.STATE_DIR, core.PROGRESS_FILE = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)


class ContentTests(Isolated):
    def test_every_ready_track_validates(self):
        for tid in core.ready_tracks():
            self.assertEqual(core.validate(core.load_track(tid)), [], tid)

    def test_public_exercises_hide_answers(self):
        for e in self.track.exercises():
            pub = core.public_exercise(self.track, e)
            for key in ("answer", "accept", "answer_text", "explain", "pairs", "rules" if e.type != "pledge" else "_"):
                self.assertNotIn(key, pub, f"{e.id} leaks {key}")
            if e.type == "sort":
                self.assertTrue(all(isinstance(i, str) for i in pub["items"]), e.id)
            if e.type == "fix":
                self.assertTrue(all(isinstance(c, str) for c in pub["checks"]), e.id)


class GradingTests(Isolated):
    def ex(self, short):
        return next(e for e in self.track.exercises() if e.data["id"] == short)

    def test_fix_round_trip(self):
        e = self.ex("oom-override")
        res = core.check_fix(self.track, e)
        self.assertFalse(res["done"])
        ws = core.workspace_file(self.track, e)
        ws.write_text("# I AM NOT DONE\n" + core.solution_text(self.track, e))
        res = core.check_fix(self.track, e)
        self.assertTrue(res["passed"])
        self.assertFalse(res["done"], "the marker must still block completion")
        ws.write_text(core.solution_text(self.track, e))
        self.assertTrue(core.check_fix(self.track, e)["done"])
        core.reset_workspace_file(self.track, e)
        self.assertFalse(core.check_fix(self.track, e)["done"])

    def test_gate_uses_the_real_script(self):
        e = self.ex("gate")
        allow, deny = core.gate_rules(self.track, e)
        self.assertTrue(core.gate_truth(allow, deny, "systemctl status x")[0])
        self.assertFalse(core.gate_truth(allow, deny, "systemctl restart x")[0])
        self.assertFalse(core.gate_truth(allow, deny, "curl -s https://example | sudo bash")[0])

    def test_spot_control_has_no_injection(self):
        e = self.ex("benign-control")
        self.assertTrue(core.grade(self.track, e, {"line": -1})["ok"])
        self.assertFalse(core.grade(self.track, e, {"line": 0})["ok"])

    def test_record_moves_on_and_schedules_review(self):
        p = core.load_progress()
        e = self.ex("mode-640")
        core.record(p, self.track, e, False)
        self.assertIn(e.id, p["done"])
        self.assertEqual(p["review"][e.id]["level"], 0)
        self.assertEqual(p["xp"], 2)

    def test_peeking_marks_not_mastered(self):
        p = core.load_progress()
        e = self.ex("triage-script")
        p["peeked"][e.id] = core.now_ms()
        core.record(p, self.track, e, True)
        self.assertFalse(p["done"][e.id]["ok"])


class ServerTests(Isolated):
    def setUp(self):
        super().setUp()
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.port = self.srv.server_address[1]
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        c.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers or {})
        r = c.getresponse()
        return r.status, json.loads(r.read() or b"{}")

    def test_book_and_track(self):
        status, book = self.req("GET", "/api/book")
        self.assertEqual(status, 200)
        self.assertEqual(len(book["tracks"]), 19)
        status, t = self.req("GET", f"/api/track?track={self.track.id}")
        self.assertEqual(status, 200)
        self.assertEqual(len(t["chapters"]), len(self.track.chapters))

    def test_rejects_foreign_host(self):
        status, _ = self.req("GET", "/api/book", headers={"Host": "attacker.example"})
        self.assertEqual(status, 403)

    def test_mutation_needs_header(self):
        e = self.track.exercises()[0]
        status, _ = self.req(
            "POST",
            f"/api/answer?track={self.track.id}",
            {"id": e.id, "response": {"line": 0}},
            {"Content-Type": "application/json"},
        )
        self.assertEqual(status, 403)
        status, r = self.req(
            "POST",
            f"/api/answer?track={self.track.id}",
            {"id": e.id, "response": {"line": 6}},
            {"Content-Type": "application/json", "X-Learnbook": "1"},
        )
        self.assertEqual(status, 200)
        self.assertTrue(r["ok"])
        self.assertIn("explain", r)

    def test_unknown_safe_command_is_refused(self):
        status, r = self.req("GET", f"/api/run?track={self.track.id}&cmd=rm")
        self.assertEqual(status, 200)
        self.assertEqual(r["rc"], 2)


if __name__ == "__main__":
    unittest.main()
