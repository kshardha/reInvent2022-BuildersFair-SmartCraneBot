from awscrt import mqtt
import json
import command_line_utils;
from awsiot import mqtt_connection_builder

class ImageMqttSender:

    def __init__(self,topic):
        self.topic = topic
        self.init_mqtt()

    # Callback when connection is accidentally lost.
    def on_connection_interrupted(connection, error, **kwargs):
        print("Connection interrupted. error: {}".format(error))


    # Callback when an interrupted connection is re-established.
    def on_connection_resumed(connection, return_code, session_present, **kwargs):
        print("Connection resumed. return_code: {} session_present: {}".format(return_code, session_present))

        if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
            print("Session did not persist. Resubscribing to existing topics...")
            resubscribe_future, _ = connection.resubscribe_existing_topics()

            # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
            # evaluate result with a callback instead.
            resubscribe_future.add_done_callback(on_resubscribe_complete)


    def on_resubscribe_complete(resubscribe_future):
            resubscribe_results = resubscribe_future.result()
            print("Resubscribe results: {}".format(resubscribe_results))

            for topic, qos in resubscribe_results['topics']:
                if qos is None:
                    sys.exit("Server rejected resubscribe to topic: {}".format(topic))


    def build_direct_mqtt_connection(self, on_connection_interrupted, on_connection_resumed):
        proxy_options = None
        mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=self.get_command_required(self.m_cmd_endpoint),
            port=self.get_command_required("port"),
            cert_filepath=self.get_command_required(self.m_cmd_cert_file),
            pri_key_filepath=self.get_command_required(self.m_cmd_key_file),
            ca_filepath=self.get_command(self.m_cmd_ca_file),
            on_connection_interrupted=on_connection_interrupted,
            on_connection_resumed=on_connection_resumed,
            client_id=self.get_command_required("client_id"),
            clean_session=False,
            keep_alive_secs=30,
            http_proxy_options=proxy_options)
        return mqtt_connection

    def init_mqtt(self):
        cmdUtils = command_line_utils.CommandLineUtils("PubSub - Send and recieve messages through an MQTT connection.")
        cmdUtils.add_common_mqtt_commands()
        cmdUtils.add_common_topic_message_commands()
        cmdUtils.add_common_proxy_commands()
        cmdUtils.add_common_logging_commands()

        cmdUtils.register_command("key", "<path>", "Path to your key in PEM format.", True, str)
        cmdUtils.register_command("cert", "<path>", "Path to your client certificate in PEM format.", True, str)
        cmdUtils.register_command("client_id", "<str>",
                                  "Client ID to use for MQTT connection (optional, default='test-*').",
                                  default="jitens-laptop")
        # Needs to be called so the command utils parse the commands
        cmdUtils.register_command("port", "<int>",
                                  "Connection port. AWS IoT supports 443 and 8883 (optional, default=auto).", type=int)
        cmdUtils.get_args()

        self.mqtt_connection = cmdUtils.build_mqtt_connection(self.on_connection_interrupted, self.on_connection_resumed)

        connect_future = self.mqtt_connection.connect()
        connect_future.result()

    def publish_msg(self, msg):
        message = msg
        message_topic=self.topic
        print("Publishing message to topic '{}': {}".format(message_topic, message))
        message_json = json.dumps(message)
        self.mqtt_connection.publish(
            topic=message_topic,
            payload=message_json,
            qos=mqtt.QoS.AT_LEAST_ONCE)