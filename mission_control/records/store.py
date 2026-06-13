"""JSONL append/read store for inert Mission Control records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from mission_control.records.errors import RecordDecodeError, UnknownRecordTypeError
from mission_control.records.models import RECORD_TYPES


class JsonlRecordStore:
    """Append and read Mission Control records as JSON Lines."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(self, record: Any) -> int:
        record_type = getattr(record, "record_type", type(record).__name__)
        if not hasattr(record, "to_dict"):
            raise TypeError("record must provide to_dict()")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(
            {"record_type": record_type, "record": record.to_dict()},
            sort_keys=True,
            separators=(",", ":"),
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")
        return self._line_count()

    def read_all(self, record_class: type[Any] | None = None) -> tuple[Any, ...]:
        if not self.path.exists():
            return ()

        records = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                entry = self._decode_line(line, line_number)
                decoded = self._decode_record(entry, line_number)
                if record_class is None or isinstance(decoded, record_class):
                    records.append(decoded)
        return tuple(records)

    def read_latest(
        self,
        record_class: type[Any] | None = None,
        limit: int = 10,
    ) -> tuple[tuple[int, Any], ...]:
        """Return latest matching records without materializing the full store.

        The returned indexes are zero-based positions among non-empty record lines,
        matching read_all() order. Results are chronological within the selected
        latest window. Malformed or unknown newest scanned records raise the same
        store errors as read_all(); older unscanned records are not decoded.
        """
        if limit <= 0 or not self.path.exists():
            return ()

        matches: list[tuple[int, Any]] = []
        for record_index, line_number, line in self._iter_nonempty_lines_reverse():
            entry = self._decode_line(line, line_number)
            decoded = self._decode_record(entry, line_number)
            if record_class is None or isinstance(decoded, record_class):
                matches.append((record_index, decoded))
                if len(matches) >= limit:
                    break
        return tuple(reversed(matches))

    def _iter_nonempty_lines_reverse(self) -> Iterator[tuple[int, int, str]]:
        nonempty_count = 0
        physical_count = 0
        with self.path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                physical_count += 1
                if raw_line.strip():
                    nonempty_count += 1

        record_index = nonempty_count - 1
        line_number = physical_count
        with self.path.open("rb") as handle:
            file_size = handle.seek(0, 2)
            position = file_size
            pending = b""
            while position > 0:
                chunk_size = min(8192, position)
                position -= chunk_size
                handle.seek(position)
                data = handle.read(chunk_size) + pending
                parts = data.split(b"\n")
                pending = parts[0]
                for raw_line in reversed(parts[1:]):
                    if raw_line == b"" and position + chunk_size == file_size:
                        continue
                    line = raw_line.strip()
                    if line:
                        yield record_index, line_number, line.decode("utf-8")
                        record_index -= 1
                    line_number -= 1
            if pending:
                line = pending.strip()
                if line:
                    yield record_index, line_number, line.decode("utf-8")

    def _line_count(self) -> int:
        with self.path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())

    @staticmethod
    def _decode_line(line: str, line_number: int) -> dict[str, Any]:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RecordDecodeError(exc.msg, line_number) from exc
        if not isinstance(entry, dict):
            raise RecordDecodeError("entry must be a JSON object", line_number)
        return entry

    @staticmethod
    def _decode_record(entry: dict[str, Any], line_number: int) -> Any:
        record_type = entry.get("record_type")
        if record_type not in RECORD_TYPES:
            raise UnknownRecordTypeError(str(record_type), line_number)
        record_data = entry.get("record")
        if record_data is None and "record" not in entry:
            record_data = {key: value for key, value in entry.items() if key != "record_type"}
        if not isinstance(record_data, dict):
            raise RecordDecodeError("record must be a JSON object", line_number)
        try:
            return RECORD_TYPES[record_type].from_dict(record_data)
        except (KeyError, TypeError, ValueError) as exc:
            raise RecordDecodeError(str(exc), line_number) from exc
