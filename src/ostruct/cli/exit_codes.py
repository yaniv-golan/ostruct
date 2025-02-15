"""Exit codes for CLI operations."""

from enum import IntEnum


class ExitCode(IntEnum):
    """Exit codes for CLI operations."""

    SUCCESS = 0
    INTERNAL_ERROR = 1
    USAGE_ERROR = 2
    DATA_ERROR = 3
    VALIDATION_ERROR = 4
    API_ERROR = 5
    SCHEMA_ERROR = 6
    UNKNOWN_ERROR = 7
    SECURITY_ERROR = 8
    FILE_ERROR = 9
