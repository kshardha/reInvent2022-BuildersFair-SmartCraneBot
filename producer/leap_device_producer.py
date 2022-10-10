# taken from - https://aws.amazon.com/premiumsupport/knowledge-center/iot-core-publish-mqtt-messages-python/
# using updated device sdk - https://github.com/aws/aws-iot-device-sdk-python-v2

# NOTE: place certificates in home_dir/certificates, e.g. /Users/jlamadri/certificates

from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
import time as time
import json
import os, inspect
import sys
import configparser
from pathlib import Path

home_dir = str(Path.home())

config = configparser.ConfigParser()
config.read('leap_device_producer.ini')
leap_dir = home_dir + config['DEFAULT']['leap_libs_dir']
sys.path.insert(0,leap_dir )
import Leap

# Define ENDPOINT, CLIENT_ID, PATH_TO_CERT, PATH_TO_KEY, PATH_TO_ROOT, TOPIC, and RANGE
ENDPOINT        = config['DEFAULT']['iot_endpoint']
CLIENT_ID       = config['DEFAULT']['client_id']
PATH_TO_CERT    = home_dir + config['DEFAULT']['certificate_pem_crt_path']
PATH_TO_KEY     = home_dir + config['DEFAULT']['private_pem_key_path']
PATH_TO_ROOT    = home_dir + config['DEFAULT']['root_path']
TOPIC           = config['DEFAULT']['topic']
SEND_DELAY      = int(config['DEFAULT']['send_delay_ms'])
CHANGE_TOLERANCE= int(config['DEFAULT']['change_tolerance_percentage'])

# Spin up resources
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=ENDPOINT,
            cert_filepath=PATH_TO_CERT,
            pri_key_filepath=PATH_TO_KEY,
            client_bootstrap=client_bootstrap,
            ca_filepath=PATH_TO_ROOT,
            client_id=CLIENT_ID,
            clean_session=False,
            keep_alive_secs=6
            )
print("Connecting to {} with client ID '{}'...".format(ENDPOINT, CLIENT_ID))

class AWSIoTListener(Leap.Listener):

    def __init__(self) -> None:
        super().__init__()
        
        self.leftright_prev = 0.1
        self.updown_prev = 1
        self.forward_backward_prev = 1

    def get_abs_percentage_change(self, current, previous):
        if current == previous: # maybe more effecient if we first round
            return 0
        try:
            return abs((abs(current - previous) / previous) * 100.0)
        except ZeroDivisionError:
            return 0

    def on_connect(client, userdata, flags, rc):
        print("AWSIoTListener::Connected with result code " + str(rc))
        client.subscribe(TOPIC)

    def on_message(client, userdata, msg):
        print(msg.topic+" "+str(msg.payload))

    def on_init(self, controller):
        print("AWSIoTListener::Initialized")

    def on_connect(self, controller):
        print("AWSIoTListener::Connected")

    def on_disconnect(self, controller):
        print("AWSIoTListener::Disconnected")

    def on_exit(self, controller):
        print("AWSIoTListener::Exited")

    def on_frame(self, controller):
        # Get the most recent frame and report some basic information
        frame = controller.frame()
        if not (frame.hands.is_empty and frame.gestures().is_empty):
            hands = frame.hands
            numHands = len(hands)
            if numHands >= 1:
                # Get the first hand
                hand = hands[0]

                # LEFT RIGHT
                leftright = round(hand.direction[0], 2)
                #print(leftright)
                # leftright_curr = round(hand.direction[0], 2)
                # percentage_change = self.get_abs_percentage_change(leftright_curr,self.leftright_prev)

                # print("LR_CURR: " + str(leftright_curr) + " LR_PREV: " + str(self.leftright_prev) + " LR PERCENT CHANGE: " + str(percentage_change))

                # if percentage_change > CHANGE_TOLERANCE:
                #     # print("LR_CHANGE exceeded tolerance : " + str(CHANGE_TOLERANCE))
                #     leftright = leftright_curr
                #     self.leftright_prev = leftright_curr
                # else:
                #     leftright = self.leftright_prev

                # UP DOWN
                updown_curr = round(hand.arm.wrist_position[1], 2)
                percentage_change = self.get_abs_percentage_change(updown_curr,self.updown_prev)
                
                # print("UD_CURR: " + str(updown_curr) + " UD_PREV: " + str(self.updown_prev) + " UD PERCENT CHANGE: " + str(percentage_change))
                
                if percentage_change > CHANGE_TOLERANCE:
                    print("UD_CURR: " + str(updown_curr) + " UD_PREV: " + str(self.updown_prev) + " UD PERCENT CHANGE: " + str(percentage_change) + "UD_CHANGE exceeded tolerance : " + str(CHANGE_TOLERANCE))
                    updown = updown_curr
                    self.updown_prev = updown_curr
                else:
                    updown = self.updown_prev

                # FORWARD BACKWARD
                forwardbackword_curr = round(hand.arm.wrist_position[2], 2)
                
                percentage_change = self.get_abs_percentage_change(forwardbackword_curr,self.forward_backward_prev)

                #print("FB_CURR: " + str(forwardbackword_curr) + " FB_PREV: " + str(self.forward_backward_prev) + " FB PERCENT CHANGE: " + str(percentage_change))
                
                if percentage_change > CHANGE_TOLERANCE:
                    #print("FB_CHANGE exceeded tolerance : " + str(CHANGE_TOLERANCE))
                    forwardbackword = forwardbackword_curr
                    self.forward_backward_prev = forwardbackword_curr
                else:
                    forwardbackword = self.forward_backward_prev               

                # GRAB
                grab = int(round(hand.grab_strength, 2))

                # print("----------------")
                # print("leftright:" + str(leftright)) # left(-0.5)..........(0.5)right
                # print("updown: " + str(updown)) # down(90)......(300)up
                # print("forwardbackword:" + str(forwardbackword)) #forward(-20)......(210)backward
                # print("grab : " + str(grab)) # fist open=0, fist closed=1
                # print("----------------")

                tev_json_obj = json.dumps(
                    {
                        'type': 'LEAP',
                        'frameId': frame.id, 
                        'coordinates':
                            {
                                'leftright': leftright,
                                'updown': updown, 
                                'forwardbackword': forwardbackword, 
                                'grab': grab
                            }
                    })

                mqtt_connection.publish(topic=TOPIC, payload=tev_json_obj, qos=mqtt.QoS.AT_LEAST_ONCE)

                time.sleep(SEND_DELAY/1000) # Sleep for SEND_DELAY milli seconds; 500ms = 1/2 second

                #print("res:" + str(response))


if __name__ == "__main__":
    # Create LEAP listener and controller
    listener = AWSIoTListener()
    controller = Leap.Controller()

    # Have the sample listener receive events from the controller
    controller.add_listener(listener)

    # Make the connect() call
    connect_future = mqtt_connection.connect()

    # Future.result() waits until a result is available
    connect_future.result()
    print("Connected!")

    # Keep this process running until Enter is pressed
    print("Press Enter to quit...")
    sys.stdin.readline()

    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()

    # Remove the sample listener when done
    print("Removing listener from Leap Controller ...")
    controller.remove_listener(listener)