import json
import boto3
import random, string
import urllib3

random_session_id = ""
game_duration_value = ""
sentiment = ""
step_function_arn = ""

def lambda_handler(event, context):
    
    # Get API body containing the message
    print(event)
    event_payload = event.get("msg")
    print(event_payload)
    
    # Calling Comprehend Detect Sentiment API
    comprehend_client = boto3.client('comprehend')
    response = comprehend_client.detect_sentiment(
        Text=event_payload,
        LanguageCode='en'
    )
    
    # What's the sentiment
    sentiment = response.get("Sentiment")
    #print(sentiment)
    
    if(sentiment == "POSITIVE" or sentiment == "NEUTRAL"):
        print(sentiment)
        response_body = "Sentiment analysis has completed. It is " + sentiment
        
        ps_client = boto3.client('ssm')
        
        # Get DDB table name from Parameter Store
        ps_parameter = ps_client.get_parameter(
            Name='LeaderBoard_DDB_Table_Name'
        )
        
        leaderboard_ddb_table = str(ps_parameter.get("Parameter").get("Value"))
        print("DDB Table Name: " + leaderboard_ddb_table)
        
        # Generate Session ID and store it in the table
        random_session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=25))
        print(random_session_id)
        http = urllib3.PoolManager()
        resp = http.request("GET", "http://reinvent2022-fargate-service-lb-715298439.us-west-2.elb.amazonaws.com/")
        player_assigned_name = resp.data.decode('utf8', 'strict')
        print("Assigned name to the player :" + player_assigned_name)
        dynamodb_client = boto3.client('dynamodb')
        dynamodb_client.put_item(TableName=leaderboard_ddb_table, Item={'session-id':{'S':random_session_id}, 'assigned-name':{'S':player_assigned_name}, 'msg':{'S': event_payload}})
        
        # Get GameDuration value from Parameter Store
        game_duration_parameter = ps_client.get_parameter(
            Name='GameDuration'
        )
        game_duration_value = str(game_duration_parameter.get("Parameter").get("Value"))
        print("Game Duration: " + game_duration_value)
        
        # Call Steps for Locking and Unlocking of Arm
        
        step_function_parameter = ps_client.get_parameter(
            Name='Step_Function_Arn'
        )
        step_function_parameter_value = str(step_function_parameter.get("Parameter").get("Value"))
        print("Step Function arn: " + step_function_parameter_value)
        
        step_function_client = boto3.client('stepfunctions')
        response = step_function_client.start_execution(
            stateMachineArn=step_function_parameter_value,
            input=json.dumps({'step_function_input': { 'session_id': random_session_id, 'table_name':leaderboard_ddb_table }})
        )
        print(response)
        
    elif(sentiment == "NEGATIVE" or sentiment == "MIXED"):
        print("Sentiment is negative")
        response_body = "Sentiment analysis has completed. It is " + sentiment
        random_session_id = ""
        game_duration_value = ""
    
    
    return {
        'statusCode': 200,
        'body': response_body,
        'sentiment': sentiment,
        'game_duration': game_duration_value,
        'session_id': random_session_id
        
    }
