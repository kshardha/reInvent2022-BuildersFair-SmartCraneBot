import json
import base64
import boto3
import uuid
from decimal import Decimal

DETECTION_THRESHOLD=0.3

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
    runtime = boto3.client(service_name="runtime.sagemaker")
    ep = "jitens-endpoint"
    #ep="object-detection-2022-10-06-14-28-42-684"
    b = bytearray(item)
    endpoint_response = runtime.invoke_endpoint(EndpointName=ep, ContentType="image/jpeg", Body=b)
    results = endpoint_response["Body"].read()
    detections = json.loads(results)
    dets = detections['prediction']
    detection = filter_detections(dets)
    return detection


def save_to_dynamodb(event, imageTime, detection):
    x0=0
    y0=0
    x1=0
    y1=0
    score=0 
    if (detection == None):
        print ("time:", imageTime, " -No ball detected")
        ball_found = 0
        
    else:
        (klass, score, x0, y0, x1, y1) = detection
        ball_found=1
        print ("time:", imageTime, " Class:", klass, " Score:", score, " x0", x0, " y0", y0," x1", x1, " y1", y1)

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('ball-motion')
    ball_uuid = str(uuid.uuid4())
    item= {
            'id': ball_uuid,
            'ball_found': ball_found,
            'image_time': imageTime,
            'score': score,
            "x0": x0, "y0": y0,"x1": x1, "y1": y1,
            "item_counter": event['counter'],
            "gameid": event['gameid']
        }
    item = json.loads(json.dumps(item), parse_float=Decimal)
    response = table.put_item(
        Item= item
    )
    #print(response)
    
    
def detect_goal(detection):
    #Narcisse to implement
    pass

def do_additional_analytics(detection):
    #Narcisse to implement
    pass
    
def lambda_handler(event, context):
    
    imageStr = event['image']
    timeStr = event['time']
    gameid = event['gameid']
    counter = str(event['counter'])
    print("Gameid:", gameid, " Counter:", counter, " Time:", timeStr)
    #print("time:", timeStr)
    #print("image:", imageStr)
    imagebytes = base64.b64decode(imageStr)
    detection = locally_call_endpoint(imagebytes)
    detect_goal(detection)
    do_additional_analytics(detection)
    save_to_dynamodb(event, timeStr, detection)
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
