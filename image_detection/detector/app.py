import json
import base64
import boto3
import uuid
from decimal import Decimal
from ShotAttemptAnalyzer import * 
from ParameterManager import *

DETECTION_THRESHOLD=0.3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ball-motion')

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


def create_detection_item(event, imageTime, detection):
    x0=0
    y0=0
    x1=0
    y1=0
    score=0 
    
    ball_found=0
    if (detection == None):
        print ("time:", imageTime, " -No ball detected")
        return None
        
    else:
        (klass, score, x0, y0, x1, y1) = detection
        ball_found=1
        print ("time:", imageTime, " Class:", klass, " Score:", score, " x0", x0, " y0", y0," x1", x1, " y1", y1)

    ball_uuid = str(uuid.uuid4())
    image_dimensions = get_image_dimensions()
    item= {
            'id': ball_uuid,
            'ball_found': ball_found,
            'image_time': imageTime,
            'score': score,
            "x0": x0, "y0": y0,"x1": x1, "y1": y1,
            "item_counter": event['counter'],
            "gameid": event['gameid'],
            "image_width":image_dimensions['w'],
            "image_height":image_dimensions['h']
            
        }
    return item
    #print(response)

def save_to_dynamodb(item):
    item = json.loads(json.dumps(item), parse_float=Decimal)
    response = table.put_item(
        Item= item
    )
    #print(response)
    
    
def detect_goal(game_id, detection):
    #TODO: shot attempt id to be implemented
    #print (detection)
    print("calling analyze_shot")
    dynamodb_resource=boto3.resource('dynamodb')
    shot_detect = detect_start_of_shot(game_id=game_id, detection_data=detection, dynamodb_resource=dynamodb_resource)
    if 'current_shot_id' in shot_detect:
        analyze_shot_frame(game_id=game_id, shot_attempt_id=shot_detect['current_shot_id'], detection_data=detection, dynamodb_resource=boto3.resource('dynamodb'))

def do_additional_analytics(detection):
    #Narcisse to implement
    pass
    
def lambda_handler(event, context):
    #analyze_shot_frame(game_id, shot_attempt_id, detection_data, game_stats_data={}, dynamodb_resource=None, parameter_store=None):
    
    
    imageStr = event['image']
    timeStr = event['time']
    gameid = event['gameid']
    counter = str(event['counter'])
    print("Gameid:", gameid, " Counter:", counter, " Time:", timeStr)
    gameid="dZJpgGZSUwUIRXolqStv831o6"
    #print("time:", timeStr)
    #print("image:", imageStr)
    imagebytes = base64.b64decode(imageStr)
    detection = locally_call_endpoint(imagebytes)
    if detection is not None:
        item = create_detection_item(event, timeStr, detection)
        detect_goal(gameid, item)
        do_additional_analytics(detection)
        save_to_dynamodb(item)
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
