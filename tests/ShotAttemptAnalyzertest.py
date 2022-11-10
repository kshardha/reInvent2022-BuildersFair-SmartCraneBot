import sys
import os
import unittest
from uuid import uuid4
import logging
import csv
import json
import boto3
from decimal import *

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from image_detection.detector.ShotAttemptAnalyzer import analyze_shot_frame, detect_start_of_shot, set_sns
from image_detection.detector.ParameterManager import *

REGION='us-west-2'
ACCESS_KEY = os.environ['AWS_ACCESS_KEY_ID']
SECRET_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
SESSION_TOKEN = os.environ['AWS_SESSION_TOKEN']

session = boto3.Session(
                aws_access_key_id=ACCESS_KEY,
                aws_secret_access_key=SECRET_KEY,
                aws_session_token=SESSION_TOKEN,
                region_name=REGION
            )

set_ssm(session.client('ssm'))
set_sns(session.client('sns'))

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            # wanted a simple yield str(o) in the next line,
            # but that would mean a yield on the line with super(...),
            # which wouldn't work (see my comment below), so...
            return (str(o) for o in [o])
        return super(DecimalEncoder, self).default(o)

class TestShotAnalysis(unittest.TestCase):

    def test_shot_attempt_analyzer_to_file(self):
        try:
            data = {}
            output_data = {}
            with open('tests/data/db_export_v0.json', 'r') as jsf:
                fileReader = json.load(jsf)
                rows = fileReader['Items']
                sorted_rows = sorted(rows, key=lambda d: int(d['item_counter']['N'])) 
                for row in sorted_rows:
                    key = row['id']
                    row['id'] = row['id']['S']
                    row['ball_found'] = row['ball_found']['N']
                    row['x0'] = row['x0']['N']
                    row['y0'] = row['y0']['N']
                    row['x1'] = row['x1']['N']
                    row['y1'] = row['y1']['N']
                    row['gameid'] = row['gameid']['S']
                    row['image_time'] = row['image_time']['S']
                    row['item_counter'] = row['item_counter']['N']
                    row['image_width'] = 320
                    row['image_height'] = 240

                    #data[key] = rows
                    if row['ball_found'] == '1':
                        analyze_shot_frame(row['gameid'], '999', row, output_data)
            
            #with open('tests/data/output_results.json', 'w', encoding='utf-8') as jsonf:
            #    jsonf.write(json.dumps(output_data, indent=4, cls=DecimalEncoder))
        except Exception as e:
            print(e)
            self.fail("Exeption occured: " + repr(e))

    def test_shot_attempt_analyzer_to_table(self):
        try:
            dyn_resource = session.resource('dynamodb')

            data = {}
            output_data = {}
            with open('tests/data/db_export_v0.json', 'r') as jsf:
                fileReader = json.load(jsf)
                rows = fileReader['Items']
                sorted_rows = sorted(rows, key=lambda d: int(d['item_counter']['N'])) 
                for row in sorted_rows:
                    key = row['id']
                    row['id'] = row['id']['S']
                    row['ball_found'] = row['ball_found']['N']
                    row['x0'] = row['x0']['N']
                    row['y0'] = row['y0']['N']
                    row['x1'] = row['x1']['N']
                    row['y1'] = row['y1']['N']
                    row['gameid'] = row['gameid']['S']
                    row['image_time'] = row['image_time']['S']
                    row['item_counter'] = row['item_counter']['N']
                    row['image_width'] = 320
                    row['image_height'] = 240

                    #data[key] = rows
                    if row['ball_found'] == '1':
                        shot_detect = detect_start_of_shot(row['gameid'], row, dynamodb_resource=dyn_resource)
                        if 'current_shot_id' in shot_detect:
                            analyze_shot_frame(row['gameid'], shot_detect['current_shot_id'], row, output_data, dynamodb_resource=dyn_resource)
            
            #with open('tests/data/output_results.json', 'w', encoding='utf-8') as jsonf:
            #    jsonf.write(json.dumps(output_data, indent=4, cls=DecimalEncoder))
        except Exception as e:
            print(e)
            self.fail("Exeption occured: " + repr(e))

if __name__ == '__main__':
    unittest.main()