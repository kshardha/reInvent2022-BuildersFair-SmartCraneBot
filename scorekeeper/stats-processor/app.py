import json
import boto3
from boto3.dynamodb.conditions import Key
import os

LEADER_BOARD_TABLE_NAME = 'Session-ic466rpeprhqno474shb2rlioy-dev'

GOAL_POINTS = os.environ['GOAL_POINTS']
TIER1_POINTS = os.environ['TIER1_POINTS']
TIER2_POINTS = os.environ['TIER2_POINTS']

dynamodb_resource = boto3.resource('dynamodb')
table = dynamodb_resource.Table(LEADER_BOARD_TABLE_NAME)
ssm = boto3.client('ssm')

table_name_parameter = ssm.get_parameter(Name='LeaderBoard_DDB_Table_Name')
LEADER_BOARD_TABLE_NAME = str(table_name_parameter['Parameter']['Value'])

def lambda_handler(event, context):
    log_message = "New game event received!" + repr(event)
    print(log_message)
    status_code = 200
    try:
        message = json.loads(event['Records'][0]['Sns']['Message'])
        game_id = message['game_id']
        tier = message['tier']
        log_message = "Processing new game event for game: " + game_id 
        print(log_message)
        response = table.query(KeyConditionExpression=(Key('id').eq(str(game_id))))
        print(response)
        if 'Items' in response:
            items = response['Items']
            if len(items)>0:
                items = response['Items']
                game_item = items[0]
                current_score = 0
                nb_tier1_shots = 0
                nb_tier2_shots = 0
                nb_goals = 0
                
                if 'score' in game_item:
                    current_score = int(game_item['score'])
                    nb_goals = int(game_item['nbGoals'])
                    if 'nbTier1' in game_item:
                        nb_tier1_shots = int(game_item['nbTier1'])
                    
                    if 'nbTier2' in game_item:
                        nb_tier2_shots = int(game_item['nbTier2'])
                
                if tier == 'GOAL':
                    currGoalTime = message['start_time']
                    nb_goals += 1
                    if 'goalTimes' in game_item:
                        goalTimes = json.loads(game_item['goalTimes'])
                    else:
                        goalTimes = {}
                    goalTimes[str(nb_goals)] = currGoalTime
                elif tier == '1':
                    nb_tier1_shots += 1
                elif tier == '2':
                    nb_tier2_shots += 1
                current_score = nb_goals*int(GOAL_POINTS) + nb_tier1_shots*int(TIER1_POINTS) + nb_tier2_shots*int(TIER2_POINTS)
                response = table.update_item(
                    Key={'id': game_id},
                    UpdateExpression="set score = :score, nbGoals = :nb_goals, nbTier1 = :nb_tier1_shots, nbTier = :nb_tier2_shots, goalTimes = :goalTimes",
                    ExpressionAttributeValues={
                        ':score': str(current_score), ':nb_goals': str(nb_goals), ':nb_tier1_shots':str(nb_tier1_shots), ':nb_tier2_shots':str(nb_tier2_shots), ':goalTimes':json.dumps(goalTimes)
                        
                    },
                    ReturnValues="UPDATED_NEW")
    
                log_message = "Successfully updated session:" + game_id
        else:
            log_message = "No game session found for session_id:" + game_id
        print(log_message)
    except Exception as error:
        log_message = "Unexpected error received: " + repr(error)
        status_code = 400
    return {
        "statusCode": status_code,
        "body": json.dumps({
            "message": log_message
        }),
    }
