#!/usr/bin/env python3
"""qa_gate.py의 backup/restore 안전장치 — 2026-11-09 근접사고(백업이 /tmp 샌드박스 제한으로
조용히 실패했는데 아무도 몰랐던 것)를 재현하고, 지금 코드가 그걸 잡는지 확인한다.

실제 저장소의 state.json/metrics.json 등은 절대 건드리지 않는다 — qa_gate.HERE를 임시
디렉터리로 몽키패치해서 가짜 원장을 쓴다."""
import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_gate


class BackupVerifiesByteForByte(unittest.TestCase):
    def setUp(self):
        self.repo = pathlib.Path(tempfile.mkdtemp(prefix="qa_gate_test_repo_"))
        self.orig_here = qa_gate.HERE
        qa_gate.HERE = self.repo
        (self.repo / "state.json").write_text(json.dumps({"used_verses": ["요한복음 3:16"]}))
        (self.repo / "metrics.json").write_text(json.dumps({"a": 1}))
        # watch.json deliberately absent — backup must skip missing ledgers, not crash.

    def tearDown(self):
        qa_gate.HERE = self.orig_here
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_backup_copies_every_existing_ledger(self):
        tmp, saved = qa_gate.backup_ledgers()
        self.assertEqual(set(saved), {"state.json", "metrics.json"})
        self.assertTrue(all(p.exists() for p in saved.values()))
        shutil.rmtree(tmp, ignore_errors=True)

    def test_backup_skips_missing_ledgers_without_crashing(self):
        # watch.json is in LEDGERS but was never created in setUp — must not raise.
        tmp, saved = qa_gate.backup_ledgers()
        self.assertNotIn("watch.json", saved)
        shutil.rmtree(tmp, ignore_errors=True)

    def test_a_restore_that_does_not_actually_land_is_caught(self):
        """2026-11-09의 근접사고 모양 그대로: copy2가 "성공"해도 그 디스크 쓰기가 실제로는
        안 먹혔을 수 있다(그때는 /tmp 샌드박스 제한이었다). restore_ledgers는 copy2의 반환값을
        믿지 않고 copy 후의 내용을 다시 비교하는데, 그 비교 자체가 거짓을 말하면(디스크가
        거짓말하는 극단적 경우) 조용히 넘어가지 않고 즉시 멈춰야 한다."""
        import unittest.mock as mock
        tmp, saved = qa_gate.backup_ledgers()
        with mock.patch.object(qa_gate.filecmp, "cmp", return_value=False):
            with self.assertRaises(qa_gate.GateError) as ctx:
                qa_gate.restore_ledgers(saved)
        self.assertIn("state.json", str(ctx.exception))
        shutil.rmtree(tmp, ignore_errors=True)

    def test_reverse_an_unverified_backup_would_lie(self):
        """역테스트: filecmp 검증 없이 shutil.copy2만 했다면 이 결함을 절대 못 잡는다는 것을
        먼저 확인 — copy2 자체는 손상된 내용도 '성공'으로 보고한다."""
        tmp = pathlib.Path(tempfile.mkdtemp())
        dst = tmp / "state.json"
        shutil.copy2(self.repo / "state.json", dst)
        dst.write_text("{}")  # corrupt it after the "successful" copy
        self.assertTrue(dst.exists(), "copy2는 이 손상을 전혀 보지 못한다 — 검증이 필요한 이유")
        shutil.rmtree(tmp, ignore_errors=True)

    def test_restore_writes_back_exactly_what_was_backed_up(self):
        tmp, saved = qa_gate.backup_ledgers()
        # mutate the "live" ledger as a real pipeline run would
        (self.repo / "state.json").write_text(json.dumps({"used_verses": ["요한복음 3:16", "시편 23:1"]}))
        qa_gate.restore_ledgers(saved)
        restored = json.loads((self.repo / "state.json").read_text())
        self.assertEqual(restored["used_verses"], ["요한복음 3:16"],
                          "복원 후에도 파이프라인이 추가한 구절이 남아있다 — 복원이 실패했다")
        shutil.rmtree(tmp, ignore_errors=True)

    def test_backup_failure_raises_before_any_pipeline_run(self):
        """백업이 검증에 실패하면 예외가 나야 한다 — 호출자가 그걸 무시하고 계속 진행할 길이
        없어야 2026-11-09와 같은 사고가 구조적으로 막힌다."""
        import unittest.mock as mock
        with mock.patch.object(qa_gate.filecmp, "cmp", return_value=False):
            with self.assertRaises(qa_gate.GateError):
                qa_gate.backup_ledgers()

    def test_a_failed_backup_leaves_no_temp_directory_behind(self):
        """code-review 발견: 백업이 실패해도 생성했던 임시 디렉터리를 지우지 않았다 — 안전장치가
        실제로 발동하는 바로 그 경로에서 디스크에 부분 백업이 영구히 남는 모양이었다."""
        import unittest.mock as mock
        with mock.patch.object(qa_gate.filecmp, "cmp", return_value=False):
            before = set(pathlib.Path(tempfile.gettempdir()).glob("qa_gate_*"))
            with self.assertRaises(qa_gate.GateError):
                qa_gate.backup_ledgers()
            after = set(pathlib.Path(tempfile.gettempdir()).glob("qa_gate_*"))
        self.assertEqual(before, after, "실패한 백업의 임시 디렉터리가 지워지지 않고 남아있다")

    def test_restore_deletes_a_ledger_the_run_newly_created(self):
        """code-review 발견: LEDGERS에 있지만 실행 전에는 없던 파일(파이프라인이 새로 만든 것)은
        restore_ledgers가 복원할 대상(`saved`)에 아예 없어서 그대로 남아있었다 — 드라이런은
        흔적을 안 남겨야 하는데 '전에 없던 파일'은 그 약속에서 빠져 있었다."""
        tmp, saved = qa_gate.backup_ledgers()   # watch.json does not exist yet
        self.assertNotIn("watch.json", saved)
        (self.repo / "watch.json").write_text(json.dumps({"alerted": True}))  # the "run" creates it
        qa_gate.restore_ledgers(saved)
        self.assertFalse((self.repo / "watch.json").exists(),
                          "파이프라인이 새로 만든 watch.json이 복원 후에도 남아있다")
        shutil.rmtree(tmp, ignore_errors=True)


class ArtifactCollectionReportsWhatItActuallyFound(unittest.TestCase):
    def setUp(self):
        self.repo = pathlib.Path(tempfile.mkdtemp(prefix="qa_gate_test_repo2_"))
        self.orig_here = qa_gate.HERE
        qa_gate.HERE = self.repo
        (self.repo / "output").mkdir()
        (self.repo / "output" / "posts").mkdir()

    def tearDown(self):
        qa_gate.HERE = self.orig_here
        shutil.rmtree(self.repo, ignore_errors=True)

    def test_a_run_with_no_output_reports_nothing_found(self):
        """결과물이 하나도 없는데 'ok'라고 끝나는 건 통과가 아니라 발견사항이어야 한다 — main()이
        found가 비면 overall을 FAIL로 뒤집는 로직을 이 테스트가 근거로 쓴다."""
        found = qa_gate.collect_artifacts(self.repo / "output" / "qa_gate" / "x")
        self.assertEqual(found, [])

    def test_the_still_and_meta_and_newest_reel_are_all_collected(self):
        (self.repo / "output" / "_bg.png").write_bytes(b"png")
        (self.repo / "output" / "_meta.json").write_text("{}")
        (self.repo / "output" / "posts" / "2026-01-01.mp4").write_bytes(b"old")
        (self.repo / "output" / "posts" / "2026-01-02.mp4").write_bytes(b"new")
        os.utime(self.repo / "output" / "posts" / "2026-01-02.mp4", None)
        dest = self.repo / "output" / "qa_gate" / "x"
        found = qa_gate.collect_artifacts(dest)
        self.assertIn("_bg.png", found)
        self.assertIn("_meta.json", found)
        self.assertTrue(any(f.endswith(".mp4") for f in found))
        self.assertTrue((dest / "_bg.png").exists())

    def test_reverse_a_missing_posts_dir_does_not_crash(self):
        shutil.rmtree(self.repo / "output" / "posts")
        found = qa_gate.collect_artifacts(self.repo / "output" / "qa_gate" / "y")
        self.assertEqual(found, [])  # no crash, just nothing to report


if __name__ == "__main__":
    unittest.main()
