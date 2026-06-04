"""JSONL append/read store for inert Mission Control records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
        if not isinstance(record_data, dict):
            raise RecordDecodeError("record must be a JSON object", line_number)
        try:
            return RECORD_TYPES[record_type].from_dict(record_data)
        except (KeyError, TypeError, ValueError) as exc:
            raise RecordDecodeError(str(exc), line_number) from exc
