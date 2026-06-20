import contextvars
import logging
import structlog
from typing import Any
from backend.config import settings

# Context var for correlation id
_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")


def set_correlation_id(cid: str) -> None:
    _correlation_id.set(cid)


def get_correlation_id() -> str:
    return _correlation_id.get()


def _add_correlation(logger: Any, method_name: str, event_dict: dict) -> dict:
    event_dict.setdefault("correlation_id", get_correlation_id())
    event_dict.setdefault("service", "backend")
    return event_dict


def configure_logger() -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    processors = [
        _add_correlation,
        structlog.processors.add_log_level,
        timestamper,
        structlog.processors.JSONRenderer()
    ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )


configure_logger()
logger = structlog.get_logger()
