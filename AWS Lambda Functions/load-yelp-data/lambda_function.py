import json
import boto3
import time
import datetime
from decimal import Decimal



def put_item_in_database(jsondata):
    print("Initiating insert...")
    count = 1
    # jsondata = jsondata[count:]
    
    for datadict in jsondata:
        print("inserting ", count)
        datadict = json.loads(json.dumps(datadict), parse_float=Decimal)
        datadict["insertedAtTimestamp"] = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        database = boto3.resource('dynamodb')
        table = database.Table('yelp-restaurants')
        if count != 910:
            try:
                table.put_item(Item = datadict)
            except Exception as ex:
                time.sleep(2)
                table.put_item(Item = datadict)
        count = count + 1
    
    print("Completed insert...")
    
def lambda_handler(event, context):
    """
    Main function
    """
    
    # Read the json file
    with open('yelp-data.json') as data:
        parsed_json = json.load(data)
    
    print(len(parsed_json))
    print(type(parsed_json))
    print(type(parsed_json[0]))
    # Call function to write into dynamodb
    put_item_in_database(parsed_json)
    print("Done and dusted...")
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
    

    
    
