import json
import boto3
import random, string

leaderboard_ddb_table = "LeaderBoard"


def lambda_handler(event, context):
    
    # Get API body containing the message
    event_payload = event.get("body")
    #print(event_payload)
    
    # Calling Comprehend Detect Sentiment API
    client = boto3.client('comprehend')
    response = client.detect_sentiment(
        Text=event_payload,
        LanguageCode='en'
    )
    
    # What's the sentiment
    sentiment = response.get("Sentiment")
    #print(sentiment)
    
    if(sentiment == "POSITIVE" or sentiment == "NEUTRAL"):
        print(sentiment)
        response_body = "Sentiment analysis has completed. It is " + sentiment
        
        # Generate Session ID and store it in the table
        
        random_session_id = ''.join(random.choices(string.ascii_letters + string.digits, k=25))
        print(random_session_id)
        dynamodb_client = boto3.client('dynamodb')
        dynamodb_client.put_item(TableName=leaderboard_ddb_table, Item={'session-id':{'S':random_session_id}, 'msg':{'S': event_payload}})
        
        # Call Timer functionality
        
        # Enable IoT Things
        
        # Call ML Inference piece
        
    elif(sentiment == "NEGATIVE" or sentiment == "MIXED"):
        print("Sentiment is negative")
        response_body = "Sentiment analysis has completed. It is " + sentiment
    
    
    return {
        'statusCode': 200,
        'body': json.dumps(response_body)
    }
