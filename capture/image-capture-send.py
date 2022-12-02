import uuid
from threading import Thread
from queue import Queue
import requests
import base64
import cv2
import datetime
import numpy as np
import boto3
import json
import time
import image_mqtt_sender;


#####Supply Values for these##########
CA_FILE="<ca file>"
CERT_FILE="<cert file>"
KEY_FILE="<key file>"
AWS_ACCESS_KEY_ID="<put values here>"
AWS_SECRET_ACCESS_KEY="<put values here>"
#AWS_SESSION_TOKEN="<put values here>"
AWS_REGION_NAME='<put values here>'

WRITE_FILE_FOR_DEBUG=False

FILE_DIR='<put values here>'
# if you have more than 1 webcam then change values here.
WEBCAM_ID=0
#debugging/local file generation.
shot_tier_bounding_box = {"x1": 195, "y1": 80, "x2": 265, "y2": 160}

#####Default values for parameters (tweak only if needed)#######
UPLOAD_BATCH_SIZE=50 # Number of parallel threads to create to upload the images to mqtt
FRAME_RATE=30 # Approximate capture frame rate
MQTT_TOPIC="cranebot"
IOT_ENDPOINT="<iot endpoint>"
LOCALLY_CALL_DETECTION=False #For debugging by directly calling the detection endpoint
SEND_MQTT_MESSAGE=True # Keep this true to send messages to MQTT topic
DETECTION_THRESHOLD=0.3 # Not used for MQTT. Used only for Local call detection. Dont send images to detection if not meets threshold




def process_image(frame, gameid, counter):
    imagehsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    #attempt 2 for blue ball
    BALL_MIN = np.array([81, 32, 50])
    BALL_MAX = np.array([105, 255, 255])


    #Yellow ball
    #BALL_MIN = np.array([30, 0, 0])
    #BALL_MAX = np.array([60, 255, 255])

    # ping pong ball
    #BALL_MIN = np.array([10, 20, 20])
    #BALL_MAX = np.array([25, 255, 255])


    #ORANGE_MIN = np.array([5, 50, 50])
    #ORANGE_MAX = np.array([15, 255, 255])

    # masking the HSV image to get only black colors
    imagemask = cv2.inRange(imagehsv, BALL_MIN, BALL_MAX)

    filename=FILE_DIR+"\\"+str(gameid)+"_"+str(counter)+".jpg"
    orig_filename = FILE_DIR+"\\"+str(gameid)+"_"+ str(counter) + "_orig.jpg"
    hsv_filename = FILE_DIR+"\\" +str(gameid)+"_"+ str(counter) + "_hsv.jpg"
    
    cv2.rectangle(frame, (shot_tier_bounding_box['x1'],shot_tier_bounding_box['y1']),
                 (shot_tier_bounding_box['x2'], shot_tier_bounding_box['y2']), (0, 0, 255), 2)
	
	if (WRITE_FILE_FOR_DEBUG):
		cv2.imwrite(filename=orig_filename, img=frame)
		cv2.imwrite(filename=filename, img=imagemask)
		cv2.imwrite(filename=hsv_filename, img=imagehsv)
    #Not using HSV at the moment.
	imagemask = frame
    hasFrame, imageBytes = cv2.imencode(".jpg", imagemask)
    return imageBytes

def filter_detections(dets):
    maxScore = 0
    detection = None
    for det in dets:
        (klass, score, x0, y0, x1, y1) = det
        if score > DETECTION_THRESHOLD and score > maxScore:
            detection = det
            maxScore = score
    return detection

def locally_call_endpoint(item):
    runtime = boto3.client(service_name="runtime.sagemaker",
                           aws_access_key_id=AWS_ACCESS_KEY_ID,
                           aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                           #aws_session_token=AWS_SESSION_TOKEN,
                           region_name=AWS_REGION_NAME)
    # ep = "object-detection-2022-10-06-14-28-42-684"
    ep = "jitens-endpoint"
    b = bytearray(item)
    endpoint_response = runtime.invoke_endpoint(EndpointName=ep, ContentType="image/jpeg", Body=b)
    results = endpoint_response["Body"].read()
    detections = json.loads(results)
    dets = detections['prediction']
    detection = filter_detections(dets)
    return detection

def send_mqtt_message(item, imageBytes):

    encoded = base64.b64encode(imageBytes)
    strb64 = encoded.decode('ascii')

    nowstr = str(item['time'])
    message = {
        "image" : strb64,
        "time" : nowstr,
        "counter" : item['counter'],
        "gameid": item['gameid']
    }
    image_mqtt_sender_client.publish_msg(message)

def upload_images(queue):
    print('Consumer: Running')
    # consume work
    while True:
        filename = "x"
        print("uploading")
        # get a unit of work
        item = queue.get()
        imageBytes = process_image(item['image'], item['gameid'], item['counter'])
        if (LOCALLY_CALL_DETECTION):
            #hasFrame, imageBytes = cv2.imencode(".jpg", item['image'])
            detection = locally_call_endpoint(imageBytes)
            print("COUNTER:",str(item['counter']), "time:",str(item['time'])," Detected:", detection)
        if (SEND_MQTT_MESSAGE):
            send_mqtt_message(item, imageBytes)
    # all done
    print('Consumer: Done')


def capture_images(queue):
    webcam = cv2.VideoCapture(WEBCAM_ID, cv2.CAP_DSHOW)
    webcam.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    webcam.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    i = 1
    gameid = str(uuid.uuid1())
    while True:
        try:
            start = datetime.datetime.now()
            print("time is :", start)
            check, frame = webcam.read()
            imageBytes = frame
            #hasFrame, imageBytes = cv2.imencode(".jpg", frame)
            #imagehsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            #hasFrame, imageBytes = cv2.imencode(".jpg", imagehsv)
            queueItem = {
                "image": imageBytes,
                "time": start,
                "counter": i,
                "gameid": gameid
            }
            #queue.put(imageBytes)
            queue.put(queueItem)
            print("current queue size", queue.qsize())
            i = i + 1
            time.sleep(1/FRAME_RATE)
        except Exception as e:
            print(e)
    webcam.release()



##################
image_mqtt_sender_client = image_mqtt_sender.ImageMqttSender(MQTT_TOPIC,IOT_ENDPOINT,CA_FILE,CERT_FILE,KEY_FILE)

image_queue = Queue()
# start the consumer(s)
consumers = []
for i in range (0, UPLOAD_BATCH_SIZE):
    consumer = Thread(target=upload_images, args=(image_queue,))
    consumer.start()
    consumers.append(consumer)
# start the producer
producer = Thread(target=capture_images, args=(image_queue,))
producer.start()
# wait for all threads to finish
producer.join()
consumer.join()
