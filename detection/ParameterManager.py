import boto3
import json


GOAL_BOUNDING_BOX='goal_bounding_box'
TIER1_BOUNDING_BOX='tier2_bounding_box'
TIER2_BOUNDING_BOX='tier1_bounding_box'
IMAGE_DIMENSIONS='image_dimensions'

#TODO Cache values

def get_shot_tier_bounding_box(tier, ssm):
    if tier == '1':
        return get_json_param(TIER1_BOUNDING_BOX, ssm)
    elif tier == '2':
        return get_json_param(TIER2_BOUNDING_BOX, ssm)
    elif tier == 'GOAL':
        return get_json_param(GOAL_BOUNDING_BOX, ssm)

def get_image_dimensions(ssm):
    return get_json_param(IMAGE_DIMENSIONS, ssm)

def get_json_param(param_name, ssm):
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
