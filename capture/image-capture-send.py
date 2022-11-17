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
CA_FILE="c:\\test\\cranebot\\iot-certs\\AmazonRootCA1.pem"
CERT_FILE="c:\\test\\cranebot\\iot-certs\\dffe0feda088baf048a5a2da3bf26ddbaa52e72416f0a69f5b1a3d37fd19e03f-certificate.pem.crt"
KEY_FILE="c:\\test\\cranebot\\iot-certs\\dffe0feda088baf048a5a2da3bf26ddbaa52e72416f0a69f5b1a3d37fd19e03f-private.pem.key"
AWS_ACCESS_KEY_ID="<put values here>"
AWS_SECRET_ACCESS_KEY="<put values here>"
AWS_SESSION_TOKEN="<put values here>"
AWS_REGION_NAME='us-west-2'
WEBCAM_ID=0

#####Default values for parameters (tweak only if needed)#######
UPLOAD_BATCH_SIZE=50 # Number of parallel threads to create to upload the images to mqtt
FRAME_RATE=30 # Approximate capture frame rate
MQTT_TOPIC="cranebot"
IOT_ENDPOINT="abpraz52fkm0l-ats.iot.us-west-2.amazonaws.com"
LOCALLY_CALL_DETECTION=False #For debugging by directly calling the detection endpoint
SEND_MQTT_MESSAGE=True # Keep this true to send messages to MQTT topic
DETECTION_THRESHOLD=0.3 # Not used for MQTT. Used only for Local call detection. Dont send images to detection if not meets threshold




def process_image(frame, gameid, counter):
    imagehsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    BALL_MIN = np.array([10, 20, 20])
    BALL_MAX = np.array([25, 255, 255])

    # masking the HSV image to get only black colors
    imagemask = cv2.inRange(imagehsv, BALL_MIN, BALL_MAX)

    filename="c:\\test\cranebot\\img-low-moving_ball_10_18_4\\"+str(gameid)+"_"+str(counter)+".jpg"
    orig_filename = "c:\\test\cranebot\\img-low-moving_ball_10_18_4\\"+str(gameid)+"_"+ str(counter) + "_orig.jpg"
    hsv_filename = "c:\\test\cranebot\\img-low-moving_ball_10_18_4\\" +str(gameid)+"_"+ str(counter) + "_hsv.jpg"

    cv2.imwrite(filename=orig_filename, img=frame)
    cv2.imwrite(filename=filename, img=imagemask)
    cv2.imwrite(filename=hsv_filename, img=imagehsv)

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
    # url = 'https://rv3tl2tjhl.execute-api.us-east-1.amazonaws.com/prod/rekognition_video_ball_detection?filename=' + filename
    # bytes = item
    # b64Str = base64.b64encode(bytes)
    # x = requests.post(url, b64Str)
    runtime = boto3.client(service_name="runtime.sagemaker",
                           aws_access_key_id=AWS_ACCESS_KEY_ID,
                           aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                           aws_session_token=AWS_SESSION_TOKEN,
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
            ##debugging purpose. stop capture after 300 images.
            #if (i > 300):
            #    break
            time.sleep(1/FRAME_RATE)
        except Exception as e:
            print(e)
    webcam.release()



##################
image_mqtt_sender_client = image_mqtt_sender.ImageMqttSender(MQTT_TOPIC)

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
#producer.join()
#consumer.join()
