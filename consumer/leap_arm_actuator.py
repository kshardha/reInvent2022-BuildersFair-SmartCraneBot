
from awscrt import io, mqtt
from awsiot import mqtt_connection_builder
import sys
import threading
import configparser
from pathlib import Path
import json
from Arm_Lib import Arm_Device
import logging
import boto3

home_dir = str(Path.home())

config = configparser.ConfigParser()
config.read('leap_arm_actuator.ini')

# Define ENDPOINT, CLIENT_ID, PATH_TO_CERT, PATH_TO_KEY, PATH_TO_ROOT, MESSAGE, TOPIC, and RANGE
ENDPOINT        = config['DEFAULT']['iot_endpoint']
CLIENT_ID       = config['DEFAULT']['client_id']
PATH_TO_CERT    = home_dir + config['DEFAULT']['certificate_pem_crt_path']
PATH_TO_KEY     = home_dir + config['DEFAULT']['private_pem_key_path']
PATH_TO_ROOT    = home_dir + config['DEFAULT']['root_path']
TOPIC           = config['DEFAULT']['topic']
MSG_SUB_COUNT   = config['DEFAULT']['message_subscribe_count']
grab_dict = {
    "old_grab": False,
    "grab_count": 0
    }

AWS_ACCESS_KEY = config['DEFAULT']['aws_access_key']
AWS_SECRET_KEY = config['DEFAULT']['aws_secret_key']

# AWS clients
ps_client = boto3.client('ssm', aws_access_key_id = AWS_ACCESS_KEY, aws_secret_access_key = AWS_SECRET_KEY )
dynamodb_client = boto3.client('dynamodb', aws_access_key_id = AWS_ACCESS_KEY, aws_secret_access_key = AWS_SECRET_KEY )

# DDB Leaderboard table name
leaderboard_ddb_table_name_parameter = ps_client.get_parameter(
        Name='LeaderBoard_DDB_Table_Name'
    )

ddb_table_name = str(leaderboard_ddb_table_name_parameter.get("Parameter").get("Value"))
print("LeaderBoard Table Name: " + ddb_table_name)

# Session ID of the current game in DDB table
ddb_session_id = "" 
attemptNumber = 1

received_count = 0
received_all_event = threading.Event()

# Get DOFBOT object
Arm = Arm_Device()

# Arm lock/unlock state.
arm_state = False # By default arm is in lock state

# Update DynamoDB Table
def update_ddb_table(isCurrentGame, updateScore):
    # Update DynamoDB table with Goal timestamp
    global ddb_session_id
    global attemptNumber

    print("Attempt number: " + str(attemptNumber))
    print("Current Game: " + str(isCurrentGame))
    print("Update Attempt Score: " + str(updateScore))

    response = dynamodb_client.update_item(
        TableName=ddb_table_name,
        Key={
            'id': {'S': ddb_session_id} # 'id': {'S': 'AKn5Sve456caOFTt6REl5OUnU'} 
        },
        AttributeUpdates={
            'attemptNumber': {'Value': {'N': str(attemptNumber)}},
            'isCurrentGame': {'Value': {'S': str(isCurrentGame)}}
        }
    )
    # Award score for each attempt
    if(updateScore):
        response = dynamodb_client.update_item(
            TableName=ddb_table_name,
            Key={
                'id': {'S': ddb_session_id} # 'id': {'S': 'AKn5Sve456caOFTt6REl5OUnU'}
            },
            UpdateExpression='ADD score :newscore',
            ExpressionAttributeValues={
                ':newscore': {'N': str(5)}
            }
        )
# Move arm to the some position
def move_arm(left_right, up_down, fwd_back_1, fwd_back_2, grab, speed):
    Arm.Arm_serial_servo_write6(left_right, up_down, fwd_back_1, fwd_back_2, 90, grab, speed)

# Move arm
def actuate_arm(payload):

    def calculate_output_angle(input_angle, input_start, input_end, output_start, output_end) :
        slope = (output_end - output_start) / (input_end - input_start)
        output = output_start + slope * (input_angle - input_start)
        return output

    speed = 800
    grab = payload['coordinates']['grab']
    fwd_bck = payload['coordinates']['forwardbackword']
    up_down = payload['coordinates']['updown']
    left_right = payload['coordinates']['leftright']
    left_right_angle = 0
    up_down_angle = 40
    fwd_bck1_angle = 60
    fwd_bck2_angle = 60

    
    # Fist open/close servo 6
    if grab == 0: # Open Fist
        grab_angle = 40
        grab_dict["old_grab"] = False;
        speed = 800
        # left_right_angle = 175
        # up_down_angle = 35
        # fwd_bck1_angle = 50
        # fwd_bck2_angle = 50
        left_right = round(left_right, 2)
        left_right_input_start = -.50
        left_right_input_end = .50
        left_right_output_start = 175
        left_right_output_end = 5
        left_right_angle = calculate_output_angle(left_right, left_right_input_start, left_right_input_end, left_right_output_start, left_right_output_end)

        if left_right <= left_right_input_start: 
            left_right_angle = left_right_output_start 
        elif left_right >= left_right_input_end:
            left_right_angle = left_right_output_end 

        # Hand forward/backward servos 3 & 4
        fwd_bck_input_start = -110
        fwd_bck_input_end = 200
        
        fwd_bck1_output_start = 90
        fwd_bck1_output_end = 10
        fwd_bck1_angle = calculate_output_angle(fwd_bck, fwd_bck_input_start, fwd_bck_input_end, fwd_bck1_output_start, fwd_bck1_output_end)

        fwd_bck2_output_start = 90
        fwd_bck2_output_end = 10
        fwd_bck2_angle = calculate_output_angle(fwd_bck, fwd_bck_input_start, fwd_bck_input_end, fwd_bck2_output_start, fwd_bck2_output_end)

        if fwd_bck <= fwd_bck_input_start:
            fwd_bck1_angle = fwd_bck1_output_start
            fwd_bck2_angle = fwd_bck2_output_start
        elif fwd_bck >= fwd_bck_input_end:
            fwd_bck1_angle = fwd_bck1_output_end
            fwd_bck2_angle = fwd_bck2_output_end
        
        # Hand up/down servo 2
        up_down_input_start = 170
        up_down_input_end = 400
        up_down_output_start = 40
        up_down_output_end = 90
        up_down_angle = calculate_output_angle(up_down, up_down_input_start, up_down_input_end, up_down_output_start, up_down_output_end)

        if up_down <= up_down_input_start: 
            up_down_angle = up_down_output_start
        elif up_down >= up_down_input_end:
            up_down_angle = up_down_output_end 

        
        print("----------------------------------------------------------------------------------------")
        print("Leap lft-rgh value: " + str(left_right) + " --- lft-rgh angle: " + str(left_right_angle))
        print("Leap up-down value: " + str(up_down) + " --- up-down angle: " + str(up_down_angle))
        print("Leap fwd-bck value: " + str(fwd_bck) + " --- fwd-bck angle: " + str(fwd_bck1_angle))
        print("Leap grab    value: " + str(grab) + " --- grab angle: " + str(grab_angle))
        print("----------------------------------------------------------------------------------------")
        print(grab_dict['old_grab'])
        grab_dict["grab_count"] = 0;
    elif grab == 1: # Closed Fist
        grab_angle = 110
        if grab_dict['old_grab'] is False:
            Arm.Arm_serial_servo_write(6, grab_angle, 400)

            # Update DDB table with attempt details
            global attemptNumber
            attemptNumber =  attemptNumber + 1
            update_ddb_table("Yes", True)
            
            grab_dict["old_grab"] = True
            # Arm.Arm_serial_servo_write6(left_right_angle, up_down_angle, fwd_bck1_angle, fwd_bck2_angle, 90, grab_angle, speed)
            print(grab_dict['old_grab'])
            return;
        elif grab_dict['old_grab'] is True:
            if grab_dict['grab_count'] < 4:
                print(grab_dict['grab_count'])
                Arm.Arm_serial_servo_write(6, grab_angle, 400)
                grab_dict["grab_count"] = grab_dict["grab_count"] + 1
                return
            if grab_dict['grab_count'] < 12:
                speed = 1400
                left_right_angle = 5
                up_down_angle = 40
                fwd_bck1_angle = 60
                fwd_bck2_angle = 60
                print(grab_dict['grab_count'])
                Arm.Arm_serial_servo_write6(left_right_angle, up_down_angle, fwd_bck1_angle, fwd_bck2_angle, 90, grab_angle, speed)
                grab_dict["grab_count"] = grab_dict["grab_count"] + 1
                return
            if grab_dict['grab_count'] < 16:
                speed = 200
                left_right_angle = 175
                up_down_angle = 35
                fwd_bck1_angle = 50
                fwd_bck2_angle = 50
                grab_angle = 40
                print(grab_dict['grab_count'])
                Arm.Arm_serial_servo_write6(left_right_angle, up_down_angle, fwd_bck1_angle, fwd_bck2_angle, 90, grab_angle, speed)
                # Arm.Arm_serial_servo_write(6, grab_angle, 400)
                grab_dict["grab_count"] = grab_dict["grab_count"] + 1
                return

    Arm.Arm_serial_servo_write6(left_right_angle, up_down_angle, fwd_bck1_angle, fwd_bck2_angle, 90, grab_angle, speed)
    
    # # Fist open/close servo 6
    # if grab == 0: # Open Fist
    #     grab_angle = 40
    #     grab_dict["old_grab"] = False;
    #     # Arm.Arm_serial_servo_write(1, .2, 200)
    #     Arm.Arm_serial_servo_write6(.2, 300, 60, 60, 90, grab_angle, speed)
    #     print(grab_dict['old_grab'])
    #     # grab_dict["grab_count"] = 0;
    # elif grab == 1: # Closed Fist
    #     grab_angle = 125
    #     # if grab_dict['old_grab'] is False:
    #     # Arm.Arm_serial_servo_write(6, grab_angle, speed)
    #     # Arm.Arm_serial_servo_write(1, -0.5, 600)
    #     Arm.Arm_serial_servo_write6(-.5, 300, 60, 60, 90, grab_angle, speed)
    #     grab_dict["old_grab"] = True
    #     print(grab_dict['old_grab'])
    #     return;
    #     # elif grab_dict['old_grab'] is True:
    #     #     if grab_dict['grab_count'] < 6:
    #     #         print(grab_dict['grab_count'])
    #     #         grab_dict["grab_count"] = grab_dict["grab_count"] + 1
    #     #         return

# # Old Logic
    # Hand left/right servo 1
    # left_right = round(left_right, 2)
    # left_right_input_start = -.50
    # left_right_input_end = .50
    # left_right_output_start = 175
    # left_right_output_end = 5
    # left_right_angle = calculate_output_angle(left_right, left_right_input_start, left_right_input_end, left_right_output_start, left_right_output_end)

    # if left_right <= left_right_input_start: 
    #     left_right_angle = left_right_output_start 
    # elif left_right >= left_right_input_end:
    #     left_right_angle = left_right_output_end 

    # # Hand forward/backward servos 3 & 4
    # fwd_bck_input_start = -110
    # fwd_bck_input_end = 200
    
    # fwd_bck1_output_start = 90
    # fwd_bck1_output_end = 10
    # fwd_bck1_angle = calculate_output_angle(fwd_bck, fwd_bck_input_start, fwd_bck_input_end, fwd_bck1_output_start, fwd_bck1_output_end)

    # fwd_bck2_output_start = 90
    # fwd_bck2_output_end = 10
    # fwd_bck2_angle = calculate_output_angle(fwd_bck, fwd_bck_input_start, fwd_bck_input_end, fwd_bck2_output_start, fwd_bck2_output_end)

    # if fwd_bck <= fwd_bck_input_start:
    #     fwd_bck1_angle = fwd_bck1_output_start
    #     fwd_bck2_angle = fwd_bck2_output_start
    # elif fwd_bck >= fwd_bck_input_end:
    #     fwd_bck1_angle = fwd_bck1_output_end
    #     fwd_bck2_angle = fwd_bck2_output_end
    
    # # Hand up/down servo 2
    # up_down_input_start = 170
    # up_down_input_end = 400
    # up_down_output_start = 20
    # up_down_output_end = 90
    # up_down_angle = calculate_output_angle(up_down, up_down_input_start, up_down_input_end, up_down_output_start, up_down_output_end)

    # if up_down <= up_down_input_start: 
    #     up_down_angle = up_down_output_start
    # elif up_down >= up_down_input_end:
    #     up_down_angle = up_down_output_end 

    
    # print("----------------------------------------------------------------------------------------")
    # print("Leap lft-rgh value: " + str(left_right) + " --- lft-rgh angle: " + str(left_right_angle))
    # print("Leap up-down value: " + str(up_down) + " --- up-down angle: " + str(up_down_angle))
    # print("Leap fwd-bck value: " + str(fwd_bck) + " --- fwd-bck angle: " + str(fwd_bck1_angle))
    # print("Leap grab    value: " + str(grab) + " --- grab angle: " + str(grab_angle))
    # print("----------------------------------------------------------------------------------------")
    # Arm.Arm_serial_servo_write6(left_right_angle, up_down_angle, fwd_bck1_angle, fwd_bck2_angle, 90, grab_angle, speed)
    
   

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
    #print("Received message from topic '{}': {}".format(topic, payload))
    global received_count
    received_count += 1
    if received_count == MSG_SUB_COUNT:
        received_all_event.set()

    payload = json.loads(payload.decode('UTF-8')) # payload comes with b' prepended; converting to UTF-8 string and creating a json object
    print(payload)
    iot_message_type = payload.get('type') # from Leap or from API
    logging.info('Message received is of type: ' + iot_message_type)

    # Actual Logic
    global arm_state
    global ddb_session_id
    global attemptNumber
        
    if(iot_message_type == "API"):
        state = payload.get('state') # LOCK or UNLOCK
        ddb_session_id = payload.get('session_id') # Game session ID
        logging.info("Game session ID: " + ddb_session_id)
        if(state == "UNLOCK"):
            logging.info("Unlocking the arm")
            arm_state = True
            update_ddb_table("Yes", True) # Current game flag
        elif(state == "LOCK"):
            # Move arm to its initial state for the next round
            move_arm(90,45,50,20,90,300)
            logging.info("Locking the arm")
            arm_state = False
            if(ddb_session_id != "" or attemptNumber != 1):
                update_ddb_table("No", False) # Current game flag
                attemptNumber = 1 # Reset it for the next game

    if (iot_message_type == "LEAP"):
        if(arm_state):
            actuate_arm(payload)
        else:
            logging.info("Arm is locked")

    # For testing
    # actuate_arm(payload)
    # move_arm(90,45,50,20,90,300)

if __name__ == '__main__':
    # Spin up resources
    event_loop_group = io.EventLoopGroup(1)
    host_resolver = io.DefaultHostResolver(event_loop_group)
    client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)

    mqtt_connection = mqtt_connection_builder.mtls_from_path(
        endpoint=ENDPOINT,
        # port=args.port,
        cert_filepath=PATH_TO_CERT,
        pri_key_filepath=PATH_TO_KEY,
        client_bootstrap=client_bootstrap,
        ca_filepath=PATH_TO_ROOT,
        on_connection_interrupted=on_connection_interrupted,
        on_connection_resumed=on_connection_resumed,
        client_id=CLIENT_ID,
        clean_session=True,
        keep_alive_secs=30
    )

    print("Connecting to {} with client ID '{}'...".format(ENDPOINT, CLIENT_ID))

    connect_future = mqtt_connection.connect()

    # Future.result() waits until a result is available
    connect_future.result()
    print("Connected!")

    # Subscribe
    print("Subscribing to topic '{}'...".format(TOPIC))
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic=TOPIC,
        qos=mqtt.QoS.AT_MOST_ONCE,
        callback=on_message_received)

    subscribe_result = subscribe_future.result()
    print("Subscribed with {}".format(str(subscribe_result['qos'])))

    # Move arm to its initial state to begin with
    move_arm(90,45,50,20,90,300)

    # Keep this process running until Enter is pressed
    print("Press Enter to quit...")
    sys.stdin.readline()

    # Wait for all messages to be received.
    # This waits forever if count was set to 0.
    #if MSG_SUB_COUNT != 0 and not received_all_event.is_set():
    #    print("Waiting for all messages to be received...")

    # received_all_event.wait()
    print("{} message(s) received.".format(received_count))

    # Disconnect
    print("Disconnecting...")
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()
    print("Disconnected!")
