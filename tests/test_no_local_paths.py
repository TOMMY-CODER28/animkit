"""Guard: no machine-local paths anywhere in tracked files.

Keeps the public repo clean of authoring-machine specifics (usernames, home
directories). Detection is structural: any Windows home-directory path, any
`Users/<name>` segment, plus optional extra tokens from an untracked
`.local_path_tokens` file (one per line) for personal names.
"""

import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PATTERNS = [
    re.compile(r"[A-Za-z]:[/\\]+Users[/\\]+[A-Za-z]"),   # C:\Users\<name>\...
]
EXTRA_TOKENS_FILE = REPO / ".local_path_tokens"       # gitignored, never committed


def _tokens() -> list[str]:
    if EXTRA_TOKENS_FILE.is_file():
        return [ln.strip() for ln in EXTRA_TOKENS_FILE.read_text().splitlines()
                if ln.strip()]
    return []


class TestNoLocalPaths(unittest.TestCase):
    def test_tracked_files_have_no_local_paths(self):
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=REPO, capture_output=True, text=True
        ).stdout.split()
        self.assertTrue(tracked, "must run inside the git checkout")
        extra = _tokens()
        offenders = []
        for rel in tracked:
            p = REPO / rel
            if not p.is_file():
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
            if any(pat.search(text) for pat in PATTERNS):
                offenders.append(f"{rel} (home-dir path pattern)")
            for token in extra:
                if token in text:
                    offenders.append(f"{rel} (local token)")
        self.assertEqual(offenders, [],
                         "machine-local paths leaked into tracked files:\n" +
                         "\n".join(offenders))


if __name__ == "__main__":
    unittest.main()
