import rclpy
import rclpy.executors
from sentry_sdk import get_client
from std_msgs.msg import String

from sentry_rclpy.rclpy_integration import RCLPyIntegration


def subscription_callback(message):
    pass


def test_single_threaded_executor_depth_metrics(sentry_init, capture_items):
    sentry_init(
        integrations=[RCLPyIntegration()],
        traces_sample_rate=1.0,
        trace_lifecycle="stream",
    )
    items = capture_items("trace_metric")

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

    metric_names = {item.payload["name"] for item in items}
    assert "executor.pending_tasks" in metric_names
    assert "executor.ready_tasks" in metric_names
    assert "executor.executing" in metric_names

    for item in items:
        assert "SingleThreadedExecutor-" in item.payload["attributes"]["executor"]


def test_multi_threaded_executor_depth_metrics(sentry_init, capture_items):
    sentry_init(
        integrations=[RCLPyIntegration()],
        traces_sample_rate=1.0,
        trace_lifecycle="stream",
    )
    items = capture_items("trace_metric")

    rclpy.init()
    try:
        node = rclpy.create_node("test_node")
        try:
            node.create_subscription(String, "/test_topic", subscription_callback, 10)
            publisher = node.create_publisher(String, "/test_topic", 10)

            executor = rclpy.executors.MultiThreadedExecutor()
            executor.add_node(node)

            publisher.publish(String(data="hello"))
            executor.spin_once()

            executor.shutdown()
        finally:
            node.destroy_node()
    finally:
        rclpy.shutdown()

    get_client().flush()

    metric_names = {item.payload["name"] for item in items}
    assert "executor.pending_tasks" in metric_names
    assert "executor.ready_tasks" in metric_names
    assert "executor.executing" in metric_names

    for item in items:
        assert "MultiThreadedExecutor-" in item.payload["attributes"]["executor"]
