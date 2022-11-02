import json
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key
from decimal import Decimal
import detection.ParameterManager as param
import os
from math import ceil

SHOT_TRACKING_TABLE_NAME = 'game_stats'
SHOT_TIERS = ['GOAL', '2', '1']
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
AREA_INTERSECTION_THRESHOLDS = {'GOAL':0.20, '1': 0.1, '2': 0.1}

GAME_STATS_TOPIC_ARN = os.environ['GAME_STATS_TOPIC_ARN']

sns_client = boto3.client('sns')

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        try:
            if isinstance(o, Decimal):
                # wanted a simple yield str(o) in the next line,
                # but that would mean a yield on the line with super(...),
                # which wouldn't work (see my comment below), so...
                return (str(o) for o in [o])
            return super(DecimalEncoder, self).default(o)
        except:
            pass
        return ''

# Analyzes current frame and determine whether a goal was detected or not. Also identifies if the shot attempts counts toward the score based on shot tiering parameters 
# If dynamodb_client is past the dynamo db game_tracking table is updated with the new information from the frame
# Returns first detected shot tier 
def analyze_shot_frame(game_id, shot_attempt_id, detection_data, game_stats_data={}, dynamodb_resource=None, parameter_store=None):
    ball_bounding_box = {}
    image_dimensions = param.get_image_dimensions(parameter_store)
    w = image_dimensions['w']
    h = image_dimensions['h']

    ball_bounding_box['x1'] = int(float(detection_data['x0']) * w)
    ball_bounding_box['y1'] = int(float(detection_data['y0']) * h)
    ball_bounding_box['x2'] = int(float(detection_data['x1']) * w)
    ball_bounding_box['y2'] = int(float(detection_data['y1']) * h)

    detected_tier = "N.A"
   
    def load_current_game_data(table):
        response = table.query(KeyConditionExpression=(Key('game_id').eq(str(game_id)) & Key('shot_attempt_id').eq(str(shot_attempt_id))))
        items = response['Items']
        highest_tier = None
        for item in items:
            _game_id = item['game_id']
            _shot_attempt_id = item['shot_attempt_id']
            _tier = item['tier']
            key = get_shot_attempt_key(str(_game_id), str(_shot_attempt_id), str(_tier))
            game_stats_data[key] = item
            curr_tier = SHOT_TIERS.index(_tier)
            if highest_tier == None or highest_tier>curr_tier:
                highest_tier = curr_tier
        return highest_tier

    try:
        table = None
        currently_detected_tier_index = None
        if dynamodb_resource is not None:
            table = dynamodb_resource.Table(SHOT_TRACKING_TABLE_NAME)
            currently_detected_tier_index = load_current_game_data(table)
        
        detected_tier = None
        for tier in SHOT_TIERS:
            tier_index = SHOT_TIERS.index(tier)
            shot_tier_bounding_box = param.get_shot_tier_bounding_box(tier, parameter_store)
            res = get_intersection_pct(shot_tier_bounding_box, ball_bounding_box, detection_data['image_width'], detection_data['image_height'])
            if res != 0.0:
                intersection_area_pct = res['iop']
                distance_to_goal = res['distance']
                if intersection_area_pct > AREA_INTERSECTION_THRESHOLDS[tier] and (currently_detected_tier_index is None or tier_index < currently_detected_tier_index):
                    detected_tier = tier
                    # shot attempt tier dectected
                    shot_record = update_shot_attempt(game_id, shot_attempt_id, tier, distance_to_goal, detection_data, game_stats_data)
                    if shot_record['notification_status'] == 'Pending' and sns_client is not None:
                        json_obj = {'default': json.dumps(shot_record, cls=DecimalEncoder)}
                        response = sns_client.publish(TargetArn=GAME_STATS_TOPIC_ARN, Message=json.dumps(json_obj), MessageStructure='json')
                        if response is not None and 'MessageId' in response:
                            shot_record['notification_status'] = 'Sent'
                    if table is not None:
                        table.put_item(Item = shot_record)
                break
    except Exception as e:
        print(e)
    return detected_tier

def update_shot_attempt(game_id, shot_attempt_id, tier, distance_to_goal, detection_data, game_stats_data):
    key = get_shot_attempt_key(game_id, str(shot_attempt_id), str(tier))
    shot_record = {}
    if key in game_stats_data:
        shot_record = game_stats_data[key]
        current_start_time = datetime.strptime(shot_record['start_time'], DATETIME_FORMAT)
        current_end_time = datetime.strptime(shot_record['end_time'], DATETIME_FORMAT)
        image_time_str = detection_data['image_time']
        image_time = datetime.strptime(image_time_str, DATETIME_FORMAT)
        if image_time > current_end_time:
            current_end_time = image_time
            shot_record['end_time'] = image_time_str
        if image_time < current_start_time:
            current_start_time = image_time
            shot_record['start_time'] = image_time_str
        if 'shortest_distance_to_target' in shot_record:
            shortest_distance_to_target = shot_record['shortest_distance_to_target']
            if distance_to_goal<shortest_distance_to_target:
                shot_record['shortest_distance_to_goal'] = distance_to_goal
                shot_record['notification_status'] = 'Pending'
        else:
            shot_record['shortest_distance_to_goal'] = distance_to_goal
            shot_record['notification_status'] = 'Pending'

        duration = (current_end_time - current_start_time).total_seconds()
        frame_list = shot_record['frame_list']
        frame_list.append(detection_data['item_counter'])
        shot_record['frame_list'] = frame_list
        shot_record['frame_count'] = len(frame_list)
        shot_record['duration_sec']  = ceil(duration)

        #TODO check if shot tier pre-req is met (duration, frame count) and flag accordingly
        #shot_record['notification_sent'] = 
    else:
        shot_record = {}
        shot_record['game_id'] = game_id
        shot_record['shot_attempt_id'] = shot_attempt_id
        shot_record['tier'] = tier
        pos = detection_data['item_counter']
        shot_record['frame_list'] = [pos]
        shot_record['frame_count'] = 1
        shot_record['start_time'] = detection_data['image_time']
        shot_record['end_time'] = detection_data['image_time']
        shot_record['duration_sec']  = 0
        shot_record['shortest_distance_to_goal'] = distance_to_goal
        shot_record['notification_status'] = 'Pending'
        game_stats_data[key] = shot_record
    return shot_record


def get_intersection_pct(shot_tier_bounding_box, ball_bounding_box, w, h):
    """
    Calculate the Intersection area of both bounding boxes.

    Parameters
    ----------
    shot_tier_bounding_box : dict
        Keys: {'x1', 'x2', 'y1', 'y2'}
        The (x1, y1) position is at the top left corner,
        the (x2, y2) position is at the bottom right corner
    ball_bounding_box : dict
        Keys: {'x1', 'x2', 'y1', 'y2'}
        The (x, y) position is at the top left corner,
        the (x2, y2) position is at the bottom right corner

    Returns
    -------
    float
        in [0, 1]
    """
    assert shot_tier_bounding_box['x1'] < shot_tier_bounding_box['x2']
    assert shot_tier_bounding_box['y1'] < shot_tier_bounding_box['y2']
    assert ball_bounding_box['x1'] < ball_bounding_box['x2']
    assert ball_bounding_box['y1'] < ball_bounding_box['y2']

    # determine the coordinates of the intersection rectangle
    x_left = max(shot_tier_bounding_box['x1'], ball_bounding_box['x1'])
    y_top = max(shot_tier_bounding_box['y1'], ball_bounding_box['y1'])
    x_right = min(shot_tier_bounding_box['x2'], ball_bounding_box['x2'])
    y_bottom = min(shot_tier_bounding_box['y2'], ball_bounding_box['y2'])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    # The intersection of two axis-aligned bounding boxes is always an
    # axis-aligned bounding box
    intersection_area = (x_right - x_left) * (y_bottom - y_top) * w * h

    # compute the area of both AABBs
    goal_area = (shot_tier_bounding_box['x2'] - shot_tier_bounding_box['x1']) * (shot_tier_bounding_box['y2'] - shot_tier_bounding_box['y1']) * w * h
    ball_area = (ball_bounding_box['x2'] - ball_bounding_box['x1']) * (ball_bounding_box['y2'] - ball_bounding_box['y1']) * w * h

    # compute the intersection over union by taking the intersection
    # area and dividing it by the sum of prediction + ground-truth
    # areas - the interesection area
    #iou = intersection_area / float(bb1_area + bb2_area - intersection_area)
    
    #Instead of calculating iou (intersect over union) we choose to use intersect over predicted ball area
    #This will return the ratio of intersction area over the ball area
    iop = intersection_area / float(ball_area)
    #Modify to check if area is greater than x% of ball area

    def distanceCalculate(p1, p2):
        """p1 and p2 in format (x1,y1) and (x2,y2) tuples"""
        dis = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
        return dis

    ball_center_x = (ball_bounding_box['x1'] + ball_bounding_box['x2'])/2
    ball_center_y = (ball_bounding_box['y1'] + ball_bounding_box['y2'])/2

    tier_reference_x = (shot_tier_bounding_box['x1'] + shot_tier_bounding_box['x2'])/2
    tier_reference_y = min(shot_tier_bounding_box['y1'], shot_tier_bounding_box['y2']) #Closest to top of goal

    distance_to_goal = distanceCalculate((ball_center_x, ball_center_y), (tier_reference_x, tier_reference_y))

    return {'iop': iop, 'distance': Decimal(str(distance_to_goal))}

# Returns a JSON Object containing stats about the shot being currently analyzed
# {
#    'gameId': (string)
#    'shotAttemptId': (string)
#    'shotTier': Tier1|Tier2|Goal
#    'frameCount': {number)
#    'detectionStartTime': (string)
#    'detectionEndTime': (string)
#    'frameList':[] List of frame ids identified
# }
# 


def get_shot_attempt_key(game_id, shot_attempt_id, tier):
    return "/".join([str(game_id), str(shot_attempt_id), str(tier)])


