"""Errors raised by Mission Control record storage."""


class RecordStoreError(Exception):
    """Base class for Mission Control record store errors."""


class UnknownRecordTypeError(RecordStoreError):
    """Raised when a JSONL entry names a record type this store cannot decode."""

    def __init__(self, record_type: str, line_number: int):
        self.record_type = record_type
        self.line_number = line_number
        super().__init__(f"unknown record type {record_type!r} on line {line_number}")


class RecordDecodeError(RecordStoreError):
    """Raised when a JSONL entry cannot be decoded as a record."""

    def __init__(self, message: str, line_number: int):
        self.line_number = line_number
        super().__init__(f"line {line_number}: {message}")
