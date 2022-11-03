import boto3
import json


GOAL_BOUNDING_BOX='goal_bounding_box'
TIER1_BOUNDING_BOX='tier1_bounding_box'
TIER2_BOUNDING_BOX='tier2_bounding_box'
IMAGE_DIMENSIONS='image_dimensions'

local_cache = {}

ssm = boto3.client('ssm')

def get_shot_tier_bounding_box(tier):
    if 'tier_'+tier not in local_cache:    
        if tier == '1':
            local_cache['tier_'+tier] = get_json_param(TIER1_BOUNDING_BOX)
        elif tier == '2':
            local_cache['tier_'+tier] = get_json_param(TIER2_BOUNDING_BOX)
        elif tier == 'GOAL':
            local_cache['tier_'+tier] = get_json_param(GOAL_BOUNDING_BOX)
    return local_cache['tier_'+tier]
    

def get_image_dimensions():
    if 'image_dimensions' not in local_cache:
        local_cache['image_dimensions'] = get_json_param(IMAGE_DIMENSIONS)
    return local_cache['image_dimensions']

def get_json_param(param_name):
    parameter = ssm.get_parameter(Name=param_name)
    return json.loads(str(parameter['Parameter']['Value']))

#def get_goal_bounding_box():
#    return {'x1': 150, 'y1': 9, 'x2': 200, 'y2': 36}

#def get_tier1_shot_bounding_box():
#    return {'x1': 129, 'y1': 16, 'x2': 229, 'y2': 57}

#def get_tier2_shot_bounding_box():
#    return {'x1': 111, 'y1': 15, 'x2': 240, 'y2': 96}

#def get_image_dimensions():
#    return {'w':320, 'h':240}
