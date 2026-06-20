import contextvars
import structlog
import logging

_correlation_id = contextvars.ContextVar("correlation_id", default="")


def set_correlation_id(cid: str) -> None:
    _correlation_id.set(cid)


def get_correlation_id() -> str:
    return _correlation_id.get()


def _add_correlation(logger, method_name, event_dict):
    event_dict.setdefault("correlation_id", get_correlation_id())
    event_dict.setdefault("service", "nas-connector")
    return event_dict


def configure_logger():
    processors = [
        _add_correlation,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
    structlog.configure(processors=processors, logger_factory=structlog.stdlib.LoggerFactory())


configure_logger()
logger = structlog.get_logger()
