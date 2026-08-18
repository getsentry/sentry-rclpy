import rclpy
import rclpy.executors
from sentry_sdk import get_client
from sentry_sdk.consts import SPANDATA
from std_msgs.msg import String

from sentry_rclpy.rclpy_integration import RCLPyIntegration


def subscription_callback(message):
    pass


def test_subscription_callback_creates_span(sentry_init, capture_items):
    sentry_init(
        integrations=[RCLPyIntegration()],
        traces_sample_rate=1.0,
        trace_lifecycle="stream",
    )
    items = capture_items("span")

    rclpy.init()
    try:
        node = rclpy.create_node("test_node")
        try:
            node.create_subscription(String, "/test_topic", subscription_callback, 10)
            publisher = node.create_publisher(String, "/test_topic", 10)

            executor = rclpy.executors.SingleThreadedExecutor()
            executor.add_node(node)

            publisher.publish(String(data="hello"))
            executor.spin_once()

            executor.shutdown()
        finally:
            node.destroy_node()
    finally:
        rclpy.shutdown()

    get_client().flush()
    (span,) = (item.payload for item in items if item.type == "span")

    assert span["attributes"]["sentry.origin"] == "auto.rclpy"
    assert (
        span["attributes"][SPANDATA.CODE_FUNCTION_NAME]
        == "test_pubsub.subscription_callback"
    )
