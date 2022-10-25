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
from detection.ShotAttemptAnalyzer import analyze_shot_frame
from detection.ParameterManager import *

REGION='us-west-2'
ACCESS_KEY = "ASIAW3NYPKRBQKKJJG6J"
SECRET_KEY = "Bj3Emp4C8cJDtF0wQOiO5qUzEVur5FUT+U3HOWQk"
SESSION_TOKEN = "IQoJb3JpZ2luX2VjEPT//////////wEaCXVzLWVhc3QtMSJHMEUCIAHUGK2x4jr1MrI24OE3a7iyftr0BKw38G8y5OVibFMqAiEA6rBmyq0tQFJYvZwZeN9RVsCmKqariNPNkEte0aj7tZwqpgIIzP//////////ARAAGgw0NzEyMjI2NzA0MDMiDCR7ckznL2XP+8jDqir6AWM29oExAibO8X6CQh4iWAzAynDXgLhmIXb7ickpz/KdW5Lpkt12B/591MDFEU8r4Wx9Oq7nNqGchfGpVdWQsy1jpSBQOQIyerRH41HqL7VyLKoX/B9t6s3Yu6BMD6+knPrVG5gdUNYP5pR3JI2o0WfIy6h3ep90oAxZFbszqTxQYrCkYJVNCbbzARjmwsBvga1gm1DrVGYOIWSPHVv0OHrzfL1KJT7UkEQSMtcFHOGiXHeb/raiu7KLE7jtRlvHQ0FNsbWVG9DL4VRFr8MLjeFvVTEpk1Hk7QTo3/MnHPNcenqATSuJWpqEoNgl7MXn3uXQrP0vZjU3KSkw3andmgY6nQHkX5N9whh7QKMyXwlW6oSzBinMi5bpsyN6fP6PniYNfWo9kCIG5pIoke+yi0LK6eDIEPW5EuqahsABHVOxhOYNu/pQmOB14pDe2S0hPTH4yE/hlkjKWY4FfBAtaNX3qnO7hmZhWPAOwEz1WsH/gxMoCHSaJuIlOppSSvom9l6CfYpv6sdrzpFlSoFciPQ2HIOx3sXQy/awngDG1dHh"

session = boto3.Session(
                aws_access_key_id=ACCESS_KEY,
                aws_secret_access_key=SECRET_KEY,
                aws_session_token=SESSION_TOKEN,
                region_name=REGION
            )

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
            with open('tests/data/export.json', 'r') as jsf:
                fileReader = json.load(jsf)
                rows = fileReader['Items']
                for row in rows:
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
                        analyze_shot_frame(row['gameid'], '999', row, output_data, parameter_store=session.client('ssm'))
            
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
            with open('tests/data/export.json', 'r') as jsf:
                fileReader = json.load(jsf)
                rows = fileReader['Items']
                for row in rows:
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
                        analyze_shot_frame(row['gameid'], '999', row, output_data, dynamodb_resource=dyn_resource, parameter_store=session.client('ssm'))
            
            #with open('tests/data/output_results.json', 'w', encoding='utf-8') as jsonf:
            #    jsonf.write(json.dumps(output_data, indent=4, cls=DecimalEncoder))
        except Exception as e:
            print(e)
            self.fail("Exeption occured: " + repr(e))


if __name__ == '__main__':
    unittest.main()