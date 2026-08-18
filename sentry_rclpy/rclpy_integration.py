import sys
import time
from typing import TYPE_CHECKING

import sentry_sdk
from sentry_sdk import traces
from sentry_sdk.consts import SPANDATA
from sentry_sdk.integrations import DidNotEnable, Integration
from sentry_sdk.utils import (
    capture_internal_exceptions,
    event_from_exception,
    qualname_from_function,
    reraise,
)

try:
    import rclpy.executors
    from rclpy.executors import await_or_execute
    from rclpy.impl.logging_severity import LoggingSeverity
    from rclpy.impl.rcutils_logger import RcutilsLogger
except ImportError:
    raise DidNotEnable("RCLPy is not installed")

if TYPE_CHECKING:
    from typing import Optional, Union, Unpack

    from rclpy.impl.rcutils_logger import LoggingFilterArgs

# Map rclpy LoggingSeverity to corresponding OTel severity numbers
_SEVERITY_TO_OTEL_SEVERITY = {
    LoggingSeverity.FATAL: 21,  # fatal
    LoggingSeverity.ERROR: 17,  # error
    LoggingSeverity.WARN: 13,  # warn
    LoggingSeverity.INFO: 9,  # info
    LoggingSeverity.DEBUG: 5,  # debug
}

# Vendored from sentry_sdk.logger
_OTEL_RANGES = [
    # ((severity level range), severity text)
    # https://opentelemetry.io/docs/specs/otel/logs/data-model
    ((1, 4), "trace"),
    ((5, 8), "debug"),
    ((9, 12), "info"),
    ((13, 16), "warn"),
    ((17, 20), "error"),
    ((21, 24), "fatal"),
]


def _otel_severity_text(otel_severity_number):
    for (lower, upper), severity in _OTEL_RANGES:
        if lower <= otel_severity_number <= upper:
            return severity

    return "default"


def _log_level_to_otel(level, mapping):
    for py_level, otel_severity_number in sorted(mapping.items(), reverse=True):
        if level >= py_level:
            return otel_severity_number, _otel_severity_text(otel_severity_number)

    return 0, "default"


class RCLPyIntegration(Integration):
    identifier = "rclpy"
    origin = "auto.rclpy"

    @staticmethod
    def setup_once():
        _patch_rcutils_logger_log()
        _patch_await_or_execute()


def _patch_rcutils_logger_log():
    original_log = RcutilsLogger.log

    def _sentry_log(
        self: "RcutilsLogger",
        message: str,
        severity: "Union[int, LoggingSeverity]",
        name: "Optional[str]" = None,
        **kwargs: "Unpack[LoggingFilterArgs]",
    ) -> bool:
        logged = original_log(self, message, severity, name=name, **kwargs)

        if not logged:
            return logged

        severity = LoggingSeverity(severity)
        if name is None:
            name = self.name

        otel_severity_number, otel_severity_text = _log_level_to_otel(
            severity, _SEVERITY_TO_OTEL_SEVERITY
        )

        sentry_sdk.get_current_scope()._capture_log(
            {
                "severity_text": otel_severity_text,
                "severity_number": otel_severity_number,
                "body": message,
                "attributes": {
                    "sentry.origin": "auto.log.rclpy",
                    "logger.name": name,
                },
                "time_unix_nano": time.time_ns(),
                "trace_id": None,
                "span_id": None,
            }
        )

        return logged

    RcutilsLogger.log = _sentry_log  # type: ignore[assignment]


def _patch_await_or_execute():
    original_await_or_execute = await_or_execute

    async def _sentry_await_or_execute(callback, *args):
        qualname = qualname_from_function(callback)

        with traces.start_span(
            name=f"Executing {qualname}",
            attributes={
                "sentry.origin": RCLPyIntegration.origin,
                SPANDATA.CODE_FUNCTION_NAME: qualname,
            },
        ):
            try:
                return await original_await_or_execute(callback, *args)
            except Exception:
                exc_info = sys.exc_info()
                with capture_internal_exceptions():
                    event, hint = event_from_exception(
                        sys.exc_info(),
                        client_options=sentry_sdk.get_client().options,
                        mechanism={"type": "rclpy", "handled": False},
                    )
                    sentry_sdk.capture_event(event, hint=hint)
                reraise(*exc_info)

    rclpy.executors.await_or_execute = _sentry_await_or_execute  # type: ignore[assignment]
