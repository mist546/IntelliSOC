"""Tails watched log files and yields new lines since the last check,
persisting a byte offset per file so a restart does not resend old lines.

Offsets are only persisted by commit(), which the agent calls once the lines
have been delivered - so if the backend is unreachable the same lines are
read again on the next poll instead of being lost.
"""
import json
import os


class FileCollector:
    def __init__(self, state_file: str) -> None:
        self.state_file = state_file
        self.offsets: dict[str, int] = self._load_state()
        self._pending: dict[str, int] = {}

    def _load_state(self) -> dict[str, int]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_state(self) -> None:
        with open(self.state_file, "w") as f:
            json.dump(self.offsets, f)

    def reset(self, path: str) -> None:
        self.offsets.pop(os.path.abspath(path), None)
        self._pending.pop(os.path.abspath(path), None)
        self._save_state()

    def commit(self, path: str) -> None:
        """Persist the offset reached by the last read_new_lines(path)."""
        abs_path = os.path.abspath(path)
        if abs_path in self._pending:
            self.offsets[abs_path] = self._pending.pop(abs_path)
            self._save_state()

    def read_new_lines(self, path: str, max_lines: int | None = None) -> list[str]:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return []

        size = os.path.getsize(abs_path)
        offset = self.offsets.get(abs_path, 0)

        # File was truncated or rotated: start from the beginning again.
        if offset > size:
            offset = 0

        lines: list[str] = []
        with open(abs_path, encoding="utf-8", errors="replace") as f:
            f.seek(offset)
            while max_lines is None or len(lines) < max_lines:
                # readline() (not iterating the file object) is required so
                # tell() stays valid - CPython disables tell() after using
                # a text-mode file's internal readahead iterator.
                line = f.readline()
                if not line:
                    break
                if line.endswith("\n"):
                    lines.append(line.rstrip("\n"))
                    offset = f.tell()
                # A trailing partial line without a newline yet is left for
                # the next poll so we never forward a half-written line.

        self._pending[abs_path] = offset
        return lines
