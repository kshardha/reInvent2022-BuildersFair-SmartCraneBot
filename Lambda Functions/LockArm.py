import boto3
import json
from datetime import datetime

iot_data_client = boto3.client('iot-data')
iot_client = boto3.client('iot')
dynamodb = boto3.client('dynamodb')

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

    response = iot_data_client.publish(
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
    
    #Disable Image Capture IoT rule for ML process
    iot_rule_name_parameter = ps_client.get_parameter(
        Name='IoT_Rule_Name_for_Image_Detection'
    )
    iot_rule_name_parameter_value = str(iot_rule_name_parameter.get("Parameter").get("Value"))
    print("IoT Rule Name: " + iot_rule_name_parameter_value)

    response = iot_client.disable_topic_rule(
        ruleName=iot_rule_name_parameter_value
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
