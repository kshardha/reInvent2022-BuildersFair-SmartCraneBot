from subprocess import Popen, TimeoutExpired
import time
from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
import sys
import threading as th
import time
import json
import os

DISPLAY_DELAY = 10
GOAL_CMD = ["./demo", "--led-rows=32", "--led-cols=64", "-D1", "./goal.ppm"]
WELCOME_CMD = ["./demo", "--led-rows=32", "--led-cols=64", "-D1", "./welcome.ppm"]


received_all_event = th.Event()

target_ep = 'abpraz52fkm0l-ats.iot.us-west-2.amazonaws.com'
thing_name = 'that_thang'
cert_filepath = './iot-certs/537e39a5eac3eaf6e983f59216453ab67926efc41a6d4bcdbb9b277dc1ce07ec-certificate.pem.crt'
private_key_filepath = './iot-certs/537e39a5eac3eaf6e983f59216453ab67926efc41a6d4bcdbb9b277dc1ce07ec-private.pem.key'
ca_filepath = './iot-certs/AmazonRootCA1.pem'

pub_topic = 'device/{}/data'.format(thing_name)
sub_topic = 'app/data'


class TextScroller:
    def __init__(self,command, text_ppm_file, timeout=-1):
        self.text_ppm_file = text_ppm_file
        self.command = command
        self.timeout = timeout

    def start_scroll_text(self):
        try:
            self.process = Popen(self.command)
            if self.timeout>0:
                self.process.wait(self.timeout)
        except TimeoutExpired as exp:
            self.process.kill()
        except Exception as ex:
            print(ex)

    def stop_scroll_text(self):
        try:
            if self.process is not None:
                self.process.kill()
        except Exception as ex:
            print(ex)

    def process(self):
        return self.process

    def run(self):
        th = th.Thread(target=self.start_scroll_text, args=[])
        th.start()


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
                
# Callback when the subscribed topic receives a message
def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    print("Received message from topic '{}': {}".format(topic, payload))
    current_scroller.start_scroll_text()

    goal_scroller = TextScroller(GOAL_CMD, "goal", 5)
    goal_scroller.run()

    current_scroller = TextScroller(WELCOME_CMD, "welcome")
    current_scroller.run()

def init_mqtt():
    # Spin up resources
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    proxy_options = None

    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=target_ep,
        port=8883,
        cert_filepath=cert_filepath,
        pri_key_filepath=private_key_filepath,
        client_bootstrap=client_bootstrap,
        ca_filepath=ca_filepath,
        on_connection_interrupted=on_connection_interrupted,
        on_connection_resumed=on_connection_resumed,
        client_id=thing_name,
        clean_session=True,
        keep_alive_secs=30,
        http_proxy_options=proxy_options)

    print("Connecting to {} with client ID '{}'...".format(
        target_ep, thing_name))

    #Connect to the gateway
    while True:
        try:
            connect_future = mqtt_connection.connect()
        # Future.result() waits until a result is available
            connect_future.result()
        except:
            print("Connection to IoT Core failed...  retrying in 5s.")
            time.sleep(5)
            continue
        else:
            print("Connected!")
            break
    
    # Subscribe
    print("Subscribing to topic " + sub_topic)
    subscribe_future, packet_id = mqtt_connection.subscribe(
    topic=sub_topic,
    qos=mqtt.QoS.AT_LEAST_ONCE,
    callback=on_message_received)

    subscribe_result = subscribe_future.result()
    print("Subscribed with {}".format(str(subscribe_result['qos'])))

if __name__ == '__main__':
    global current_scroller
    current_scroller = TextScroller(WELCOME_CMD, "welcome")
    current_scroller.run()
    init_mqtt()

    
