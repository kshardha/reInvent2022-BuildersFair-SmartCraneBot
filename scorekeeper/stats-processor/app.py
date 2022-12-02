import json
import boto3
from boto3.dynamodb.conditions import Key
import os
import traceback
import datetime

ssm = boto3.client('ssm')
table_name_parameter = ssm.get_parameter(Name='LeaderBoard_DDB_Table_Name')
LEADER_BOARD_TABLE_NAME = str(table_name_parameter['Parameter']['Value'])
GOAL_POINTS = os.environ['GOAL_POINTS']
TIER1_POINTS = os.environ['TIER1_POINTS']
TIER2_POINTS = os.environ['TIER2_POINTS']

dynamodb_resource = boto3.resource('dynamodb')
table = dynamodb_resource.Table(LEADER_BOARD_TABLE_NAME)

def lambda_handler(event, context):
    log_message = "New game event received!" + repr(event)
    print(log_message)
    status_code = 200
    try:
        message = json.loads(event['Records'][0]['Sns']['Message'])
        game_id = message['game_id']
        tier = message['tier']
        currShotTime = message['start_time']
        #d = datetime.datetime.strptime(currShotTime, "%Y-%m-%d %H:%M:%S.%f")
        #currShotTime = d.strftime("%Y-%m-%dT%H:%M:%S")
        
        #currShotTime = datetime.datetime.strptime(currShotTime, "%Y-%m-%d %H:%M:%S.%f")
        goalTimes = []
        
        #TODO: Fix goal double counting problem later
        log_message = "Processing new game event for game: " + str(game_id) 
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
                    if 'nbGoals' in game_item:
                        nb_goals = int(game_item['nbGoals'])
                        
                    if 'nbTier1' in game_item:
                        nb_tier1_shots = int(game_item['nbTier1'])
                    
                    if 'nbTier2' in game_item:
                        nb_tier2_shots = int(game_item['nbTier2'])
                
                if tier == 'GOAL':
                    if 'goalTimes' in game_item and len(game_item['goalTimes'])>0:
                        goalTimes = json.loads(game_item['goalTimes'])
                    else:
                        goalTimes = []
                    goalTimes.append(currShotTime)
                
                #update attempt timeline data
                attemptNumber = game_item['attemptNumber']
                if 'attemptsData' in game_item and len(game_item['attemptsData'])>0:
                    attemptsData = json.loads(game_item['attemptsData'])
                else:
                    attemptsData = {}

                if str(attemptNumber) in attemptsData:
                    currlist = attemptsData[str(attemptNumber)]
                else:
                    currlist = {}
                
                if tier in currlist:
                    if len(currlist[str(tier)]) == 0:
                        currlist[str(tier)].append(currShotTime) 
                else:
                    currlist[str(tier)] = [currShotTime] 
                
                attemptsData[str(attemptNumber)] = currlist
                
                current_score = 0
                for attempt in attemptsData:
                    current_score += 5
                    attemptTimeline = attemptsData[attempt]
                    if 'GOAL' in attemptTimeline:
                        current_score += int(GOAL_POINTS)
                        nb_goals += 1
                    elif '2' in attemptTimeline:
                        current_score += int(TIER2_POINTS)
                        nb_tier1_shots += 1
                    elif '1' in attemptTimeline:
                        current_score += int(TIER1_POINTS)
                        nb_tier2_shots += 1    
                #get current highest tier to calcuklate score
                #score_update = 0
                #if 'GOAL' in currlist:
                #    score_update = int(GOAL_POINTS)
                #elif '2' in currlist:
                #    score_update = int(TIER2_POINTS)
                #elif '1' in currlist:
                #    score_update = int(TIER1_POINTS)

                #current_score = current_score + score_update
                response = table.update_item(
                    Key={'id': game_id},
                    UpdateExpression="set score = :score, nbGoals = :nb_goals, nbTier1 = :nb_tier1_shots, nbTier2 = :nb_tier2_shots, goalTimes = :goalTimes, attemptsData = :attemptsData",
                    ExpressionAttributeValues={
                        ':score': current_score,
                        ':nb_goals': nb_goals,
                        ':nb_tier1_shots':nb_tier1_shots,
                        ':nb_tier2_shots':nb_tier2_shots, 
                        ':goalTimes':json.dumps(goalTimes),
                        ':attemptsData':json.dumps(attemptsData)
                        
                    },
                    ReturnValues="UPDATED_NEW")
    
                log_message = "Successfully updated session:" + game_id
        else:
            log_message = "No game session found for session_id:" + game_id
        print(log_message)
    except Exception as error:
        traceback.print_exc()
        log_message = "Unexpected error received: " + repr(error)
        status_code = 400
    return {
        "statusCode": status_code,
        "body": json.dumps({
            "message": log_message
        }),
    }
