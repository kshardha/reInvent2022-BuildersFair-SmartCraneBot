import boto3
import json
from datetime import datetime

iot_client = boto3.client('iot-data')
dynamodb = boto3.client('dynamodb')
iot_topic_name = ""

def lambda_handler(event, context):
    print(event)
    session_id = event.get("session_id")
    ddb_table_name = event.get("table_name")
    #data = json.loads(event["body"])
    
    # Get IoT Topic Name from Parameter Store
    ps_client = boto3.client('ssm')
    iot_topic_name_parameter = ps_client.get_parameter(
        Name='IoT_Topic_Name'
    )
    
    # Send IoT Message
    iot_topic_name_parameter_value = str(iot_topic_name_parameter.get("Parameter").get("Value"))
    print("IoT Topic Name: " + iot_topic_name_parameter_value)

    response = iot_client.publish(
        topic=iot_topic_name_parameter_value,
        qos=1,
        payload=json.dumps(
            {
                "type": "API",
                "state": "LOCK"
            }
        )
    )
    
    # Update DynamoDB table with start timestamp
    response = dynamodb.update_item(
        TableName=ddb_table_name,
        Key={
            'session-id': {'S': session_id}
        },
        AttributeUpdates={
            'game_end_time': {'Value': {'S': datetime.now().isoformat()}}
        }
    )
    
    print(response)

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
        },
        'body': json.dumps(
            {
                "message": "Success locking!!"
            }
        )
    }
