import json
import logging
import sys
from datetime import UTC, datetime


class RequestIDFilter(logging.Filter):
    """Injecte request_id depuis le contextvar dans chaque LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Import local pour éviter la circularité au moment du chargement du module.
        try:
            from app.middleware.request_id import request_id_ctx

            record.request_id = request_id_ctx.get() or "-"
        except Exception:  # noqa: BLE001
            record.request_id = "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIDFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
