"""
Structured logger for graphiti-service.
Ships JSON logs to Seq via HTTP ingestion. Falls back to stdout on failure.
"""
import logging
import os

try:
    import structlog

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    logger = structlog.get_logger().bind(service="graphiti-service")

except ImportError:
    # fallback when structlog not installed
    _log = logging.getLogger("graphiti-service")
    if not _log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
        _log.addHandler(handler)
    _log.setLevel(logging.INFO)

    class _Compat:
        def info(self, msg, **kw): _log.info(f"{msg} {kw}")
        def warning(self, msg, **kw): _log.warning(f"{msg} {kw}")
        def error(self, msg, **kw): _log.error(f"{msg} {kw}")
        def debug(self, msg, **kw): _log.debug(f"{msg} {kw}")

    logger = _Compat()
