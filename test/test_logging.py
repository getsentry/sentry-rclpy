"""Tests for the RCLPyIntegration Sentry logging integration."""

from unittest import mock

import rclpy.logging
from sentry_sdk import get_client
from sentry_sdk.consts import VERSION

from sentry_rclpy.rclpy_integration import RCLPyIntegration


def test_sentry_logs_warning(sentry_init, capture_items):
    """
    The rclpy logger should create 'warn' sentry logs by default.
    """
    sentry_init(
        integrations=[RCLPyIntegration()],
        traces_sample_rate=1.0,
        trace_lifecycle="stream",
    )
    items = capture_items("log")

    logger = rclpy.logging.get_logger("test-logger")
    logger.warning("hi")

    get_client().flush()
    logs = [item.payload for item in items]
    attrs = logs[0]["attributes"]
    assert attrs["logger.name"] == "test-logger"
    assert attrs["sentry.environment"] == "production"
    assert attrs["sentry.origin"] == "auto.log.rclpy"
    assert attrs["sentry.severity_number"] == 13
    assert attrs["sentry.severity_text"] == "warn"


def test_sentry_logs_debug(sentry_init, capture_items):
    """
    The rclpy logger should not create 'debug' sentry logs by default.
    """
    sentry_init(
        integrations=[RCLPyIntegration()],
        traces_sample_rate=1.0,
        trace_lifecycle="stream",
    )
    items = capture_items("log")

    logger = rclpy.logging.get_logger("test-logger")
    logger.debug("hi")
    get_client().flush()

    assert not items


def test_logger_with_all_attributes(sentry_init, capture_items):
    """
    The rclpy logger should be able to log all attributes.
    """
    sentry_init(
        integrations=[RCLPyIntegration()],
        traces_sample_rate=1.0,
        trace_lifecycle="stream",
    )
    items = capture_items("log")

    logger = rclpy.logging.get_logger("test-logger")
    logger.warning("log #1")
    get_client().flush()

    logs = [item.payload for item in items]

    attributes = logs[0]["attributes"]

    assert "sentry.release" in attributes
    assert isinstance(attributes["sentry.release"], str)
    del attributes["sentry.release"]

    assert "server.address" in attributes
    assert isinstance(attributes["server.address"], str)
    del attributes["server.address"]

    assert attributes.pop("sentry.sdk.name").startswith("sentry.python")

    assert attributes == {
        "logger.name": "test-logger",
        "sentry.origin": "auto.log.rclpy",
        "sentry.environment": "production",
        "process.runtime.name": mock.ANY,
        "process.runtime.version": mock.ANY,
        "sentry.sdk.version": VERSION,
        "sentry.severity_number": 13,
        "sentry.severity_text": "warn",
    }
