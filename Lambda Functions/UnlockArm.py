import boto3
import json
from datetime import datetime

client = boto3.client('iot-data', region_name='us-west-2')


def lambda_handler(event, context):
    #data = json.loads(event["body"])

    response = client.publish(
        topic="smart_crane_bot/leap_device_topic",
        qos=1,
        payload=json.dumps(
            {
                "type": "API",
                "state": "UNLOCK"
            }
        )
    )

    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
        },
        'body': json.dumps(
            {
                "message": "Success unlocking!!"
            }
        )
    }
