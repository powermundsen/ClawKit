from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

from clawkit.paths import (
    ClawKitPaths,
    PathConfigurationError,
    ensure_private_directories,
)


class TestClawKitPaths(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.home = Path(self.tempdir.name) / "home"
        self.home.mkdir()

    def test_defaults_are_portable_and_side_effect_free(self) -> None:
        paths = ClawKitPaths.from_environ({"HOME": str(self.home)})

        self.assertEqual(paths.config_dir, self.home / ".config" / "clawkit")
        self.assertEqual(
            paths.data_dir, self.home / ".local" / "share" / "clawkit"
        )
        self.assertEqual(
            paths.state_dir, self.home / ".local" / "state" / "clawkit"
        )
        self.assertEqual(paths.instance_dir, self.home / "ClawKitInstance")
        self.assertFalse(paths.config_dir.exists())
        self.assertFalse(paths.state_dir.exists())

    def test_xdg_and_clawkit_overrides_are_respected(self) -> None:
        config_root = self.home / "xdg-config"
        custom_instance = self.home / "instance"
        paths = ClawKitPaths.from_environ(
            {
                "HOME": str(self.home),
                "XDG_CONFIG_HOME": str(config_root),
                "CLAWKIT_INSTANCE_DIR": str(custom_instance),
            }
        )

        self.assertEqual(paths.config_dir, config_root / "clawkit")
        self.assertEqual(paths.instance_dir, custom_instance)

    def test_portable_root_keeps_owned_paths_below_root(self) -> None:
        paths = ClawKitPaths.from_root("/opt/example-assistant")

        self.assertEqual(paths.instance_dir, Path("/opt/example-assistant/instance"))
        self.assertEqual(
            paths.provider_bin_dir,
            Path("/opt/example-assistant/providers/bin"),
        )
        self.assertEqual(
            paths.codex_home,
            Path("/opt/example-assistant/providers/codex"),
        )
        self.assertEqual(
            paths.releases_dir,
            Path("/opt/example-assistant/releases"),
        )
        self.assertEqual(
            paths.current_release,
            Path("/opt/example-assistant/current"),
        )
        for path in paths.private_runtime_directories():
            self.assertTrue(path.is_relative_to(paths.home))

    def test_relative_override_is_rejected(self) -> None:
        with self.assertRaises(PathConfigurationError):
            ClawKitPaths.from_environ(
                {"HOME": str(self.home), "CLAWKIT_STATE_DIR": "relative/state"}
            )

    def test_explicit_bootstrap_creates_private_directories(self) -> None:
        paths = ClawKitPaths.from_environ({"HOME": str(self.home)})
        ensure_private_directories(paths.private_runtime_directories())

        for path in paths.private_runtime_directories():
            self.assertTrue(path.is_dir())
            mode = stat.S_IMODE(path.stat().st_mode)
            self.assertEqual(mode, 0o700)

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_symlink_directory_is_rejected(self) -> None:
        real = self.home / "real"
        real.mkdir()
        linked = self.home / "linked"
        linked.symlink_to(real, target_is_directory=True)

        with self.assertRaises(PathConfigurationError):
            ensure_private_directories((linked,))


if __name__ == "__main__":
    unittest.main()
