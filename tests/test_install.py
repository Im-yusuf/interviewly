"""Tests for the cross-platform installer (install.py) on macOS, Linux and Windows."""
import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import install  # noqa: E402


class InstallTest(unittest.TestCase):
    def test_install_upgrade_and_uninstall_antigravity(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugins = Path(tmp) / "plugins"
            out = io.StringIO()
            with redirect_stdout(out):
                rc = install.install_antigravity(dest=str(plugins))
            self.assertEqual(rc, 0)
            target = plugins / "interviewly"
            self.assertTrue(install.is_interviewly(target))
            self.assertTrue((target / "hooks.json").is_file())
            self.assertIn("loads it automatically", out.getvalue())

            # Re-installing replaces an earlier Interviewly install cleanly
            (target / "stale.txt").write_text("old", encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                rc = install.install_antigravity(dest=str(plugins))
            self.assertEqual(rc, 0)
            self.assertFalse((target / "stale.txt").exists())
            self.assertTrue(install.is_interviewly(target))

            # --uninstall removes the Interviewly folder
            with redirect_stdout(io.StringIO()):
                rc = install.install_antigravity(dest=str(plugins), uninstall=True)
            self.assertEqual(rc, 0)
            self.assertFalse(target.exists())

            # Uninstalling again is a clean no-op
            with redirect_stdout(io.StringIO()):
                rc = install.install_antigravity(dest=str(plugins), uninstall=True)
            self.assertEqual(rc, 0)

    def test_refuses_to_overwrite_or_delete_unrelated_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugins = Path(tmp) / "plugins"
            unrelated = plugins / "interviewly"
            unrelated.mkdir(parents=True)
            (unrelated / "keep.txt").write_text("mine", encoding="utf-8")
            (unrelated / "plugin.json").write_text('{"name": "other"}', encoding="utf-8")

            err = io.StringIO()
            with redirect_stderr(err):
                rc = install.install_antigravity(dest=str(plugins))
            self.assertEqual(rc, 1)
            self.assertEqual((unrelated / "keep.txt").read_text(encoding="utf-8"), "mine")

            err = io.StringIO()
            with redirect_stderr(err):
                rc = install.install_antigravity(dest=str(plugins), uninstall=True)
            self.assertEqual(rc, 1)
            self.assertEqual((unrelated / "keep.txt").read_text(encoding="utf-8"), "mine")

    def test_failed_swap_restores_previous_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugins = Path(tmp) / "plugins"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(install.install_antigravity(dest=str(plugins)), 0)
            target = plugins / "interviewly"
            (target / "marker.txt").write_text("previous", encoding="utf-8")

            real_move = install.shutil.move
            calls = []

            def fail_second_move(src, dst):
                calls.append((src, dst))
                if len(calls) == 2:
                    raise OSError("simulated failure")
                return real_move(src, dst)

            with mock.patch.object(install.shutil, "move", side_effect=fail_second_move):
                with redirect_stderr(io.StringIO()):
                    rc = install.install_antigravity(dest=str(plugins))
            self.assertEqual(rc, 1)
            self.assertEqual((target / "marker.txt").read_text(encoding="utf-8"), "previous")

    @unittest.skipUnless(os.name == "posix", "symlinks need extra rights on Windows")
    def test_uninstall_removes_a_linked_install_but_not_what_it_points_to(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "clone"
            shutil.copytree(str(ROOT / "dist" / "antigravity" / "interviewly"), str(clone))
            mode = clone.stat().st_mode
            plugins = Path(tmp) / "plugins"
            plugins.mkdir()
            (plugins / "interviewly").symlink_to(clone)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(install.install_antigravity(dest=str(plugins), uninstall=True), 0)
            self.assertFalse(os.path.lexists(plugins / "interviewly"))
            self.assertEqual(clone.stat().st_mode, mode)
            self.assertTrue(install.is_interviewly(clone))

    @unittest.skipUnless(os.name == "posix" and os.geteuid() != 0, "needs a folder this user can't delete from")
    def test_an_uninstall_that_fails_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugins = Path(tmp) / "plugins"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(install.install_antigravity(dest=str(plugins)), 0)
            stuck = plugins / "interviewly" / "stuck"
            (stuck / "inner").mkdir(parents=True)
            stuck.chmod(0o555)
            try:
                err = io.StringIO()
                with redirect_stdout(io.StringIO()), redirect_stderr(err):
                    rc = install.install_antigravity(dest=str(plugins), uninstall=True)
                self.assertEqual(rc, 1)
                self.assertIn("Couldn't remove", err.getvalue())
            finally:
                stuck.chmod(0o755)

    def test_install_stages_beside_the_plugins_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            plugins = Path(tmp) / "a" / "plugins"
            real = tempfile.mkdtemp
            with mock.patch.object(install.tempfile, "mkdtemp", side_effect=real) as made, \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(install.install_antigravity(dest=str(plugins)), 0)
            self.assertEqual(made.call_args[1].get("dir"), str(plugins.parent))
            self.assertEqual(sorted(p.name for p in plugins.parent.iterdir()), ["plugins"])   # staging cleaned up

    def test_uses_agy_cli_when_available_and_no_custom_dest(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTIGRAVITY_PLUGINS_DIR", None)
            with mock.patch.object(install.shutil, "which", return_value="/usr/local/bin/agy"), \
                 mock.patch.object(install.subprocess, "run", return_value=mock.Mock(returncode=0)) as run_mock:
                with redirect_stdout(io.StringIO()):
                    rc = install.install_antigravity()
            self.assertEqual(rc, 0)
            args = run_mock.call_args[0][0]
            self.assertEqual(args[:3], ["/usr/local/bin/agy", "plugin", "install"])

    def test_claude_and_codex_commands(self):
        for platform, expected in (("claude", "/plugin install interviewly@interviewly"),
                                   ("codex", "codex plugin add interviewly@interviewly")):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = install.main([platform])
            self.assertEqual(rc, 0)
            self.assertIn(expected, out.getvalue())


if __name__ == "__main__":
    unittest.main()
