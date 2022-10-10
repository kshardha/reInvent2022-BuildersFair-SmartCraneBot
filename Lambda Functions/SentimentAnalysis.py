import json
import boto3

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
    
    if(sentiment == "POSITIVE" or sentiment == "NEUTRAL" or sentiment == "MIXED"):
        print(sentiment)
        response_body = "Sentiment analysis has completed. It is " + sentiment
    elif(sentiment == "NEGATIVE"):
        print("Sentiment is negative")
        response_body = "Sentiment analysis has completed. It is " + sentiment
    
    
    return {
        'statusCode': 200,
        'body': json.dumps(response_body)
    }
