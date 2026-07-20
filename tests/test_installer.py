from __future__ import annotations

import json
import shlex
import tempfile
import unittest
from pathlib import Path

from eightbit_buddy.installer import HOOK_EVENTS, hook_path, install_hooks, uninstall_hooks


class InstallerTests(unittest.TestCase):
    def test_install_is_additive_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            path = hook_path("codex", home)
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "description": "keep me",
                        "hooks": {
                            "Stop": [
                                {
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "/usr/local/bin/existing-hook",
                                        }
                                    ]
                                }
                            ]
                        },
                    }
                )
            )

            changed = install_hooks(["codex"], executable="/opt/homebrew/bin/8bit-buddy", home=home)
            self.assertEqual(changed, [path])
            data = json.loads(path.read_text())
            self.assertEqual(data["description"], "keep me")
            self.assertEqual(len(data["hooks"]["Stop"]), 2)
            for event in HOOK_EVENTS["codex"]:
                self.assertIn(event, data["hooks"])

            self.assertEqual(
                install_hooks(["codex"], executable="/opt/homebrew/bin/8bit-buddy", home=home),
                [],
            )

    def test_uninstall_preserves_unrelated_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            install_hooks(["cursor"], executable="/opt/homebrew/bin/8bit-buddy", home=home)
            path = hook_path("cursor", home)
            data = json.loads(path.read_text())
            data["hooks"]["stop"].append({"command": "/usr/local/bin/keep-this"})
            path.write_text(json.dumps(data))

            self.assertEqual(uninstall_hooks(["cursor"], home=home), [path])
            final = json.loads(path.read_text())
            self.assertEqual(final["hooks"]["stop"], [{"command": "/usr/local/bin/keep-this"}])

    def test_hook_command_safely_quotes_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            executable = "/Applications/8bit Buddy/bin/8bit-buddy"
            config = home / "Config Files" / "buddy's $config.toml"

            install_hooks(
                ["cursor"],
                executable=executable,
                home=home,
                config_path=config,
            )
            data = json.loads(hook_path("cursor", home).read_text())
            command = data["hooks"]["stop"][0]["command"]

            self.assertEqual(
                shlex.split(command),
                [executable, "hook", "cursor", "--config", str(config.resolve())],
            )
            self.assertEqual(
                install_hooks(
                    ["cursor"],
                    executable=executable,
                    home=home,
                    config_path=config,
                ),
                [],
            )


if __name__ == "__main__":
    unittest.main()
