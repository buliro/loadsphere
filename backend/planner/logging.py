import datetime
import json
import logging
from typing import Any, Dict


class StructuredJsonFormatter(logging.Formatter):
    """Simple JSON formatter to support structured logs without extra deps."""

    _RESERVED = {
        'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
        'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
        'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 'process',
        'processName', 'message', 'asctime', 'stacklevel', 'taskName',
    }

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            'timestamp': datetime.datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self._RESERVED and not key.startswith('_')
        }
        if extras:
            log_entry['extras'] = extras

        if record.exc_info:
            log_entry['exc_info'] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)
