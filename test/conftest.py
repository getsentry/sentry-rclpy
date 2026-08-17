from dataclasses import dataclass

import pytest
import sentry_sdk
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport


@pytest.fixture
def sentry_init():
    def inner(*a, **kw):
        kw.setdefault("transport", TestTransport())
        client = sentry_sdk.Client(*a, **kw)
        sentry_sdk.get_global_scope().set_client(client)

    old_client = sentry_sdk.get_global_scope().client
    try:
        sentry_sdk.get_current_scope().set_client(None)
        yield inner
    finally:
        sentry_sdk.get_global_scope().set_client(old_client)


class TestTransport(Transport):
    def __init__(self):
        Transport.__init__(self)

    def capture_envelope(self, _: Envelope) -> None:
        """No-op capture_envelope for tests"""
        pass


@dataclass
class UnwrappedItem:
    type: str
    payload: dict


@pytest.fixture
def capture_items(monkeypatch):
    """
    Capture envelope payload, unfurling individual items.

    Makes it easier to work with both events and attribute-based telemetry in
    one test.
    """

    def inner(*types):
        telemetry = []
        test_client = sentry_sdk.get_client()
        old_capture_envelope = test_client.transport.capture_envelope

        def append_envelope(envelope):
            for item in envelope:
                if types and item.type not in types:
                    continue

                if item.type in ("trace_metric", "log", "span"):
                    for i in item.payload.json["items"]:
                        t = {k: v for k, v in i.items() if k != "attributes"}
                        t["attributes"] = {
                            k: v["value"] for k, v in i["attributes"].items()
                        }
                        telemetry.append(UnwrappedItem(type=item.type, payload=t))
                else:
                    telemetry.append(
                        UnwrappedItem(type=item.type, payload=item.payload.json)
                    )

            return old_capture_envelope(envelope)

        monkeypatch.setattr(test_client.transport, "capture_envelope", append_envelope)

        return telemetry

    return inner
