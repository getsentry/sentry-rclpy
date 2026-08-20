import rclpy
import sentry_sdk
from rclpy.node import Node
from std_msgs.msg import String

from sentry_rclpy.rclpy_integration import RCLPyIntegration


class TelemetryDemoNode(Node):
    def __init__(self) -> None:
        super().__init__("telemetry_demo")

        self.declare_parameter(
            "sentry_dsn", "https://examplePublicKey@o0.ingest.sentry.io/0"
        )

        self._publisher = self.create_publisher(String, "/telemetry_demo", 10)
        self.create_subscription(String, "/telemetry_demo", self._on_message, 10)

        self._tick = 0
        self.create_timer(1.0, self._on_timer)

        self.get_logger().info("TelemetryDemoNode started")

    def _on_timer(self) -> None:
        self._tick += 1
        msg = String(data=f"tick {self._tick}")
        self._publisher.publish(msg)

        self.get_logger().info(f"Published: {msg.data}.")

        if self._tick % 3 == 0:
            self.get_logger().warning(f"Tick {self._tick} is divisible by 3.")

        if self._tick % 5 == 0:
            self.get_logger().error(
                f"Tick {self._tick} is divisible by 5 (simulated error log)."
            )

    def _on_message(self, msg: String) -> None:
        self.get_logger().info(f"Received: {msg.data}")

        if self._tick > 0 and self._tick % 7 == 0:
            raise RuntimeError(f"Simulated failure on tick {self._tick}.")


def main() -> None:
    rclpy.init()
    node = TelemetryDemoNode()

    dsn = node.get_parameter("sentry_dsn").get_parameter_value().string_value
    sentry_sdk.init(
        dsn=dsn,
        integrations=[RCLPyIntegration()],
        traces_sample_rate=1.0,
        trace_lifecycle="stream",
    )
    node.get_logger().info("Sentry initialised.")

    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
