import json
import random 
import decimal 
import time
from config import *
import boto3
from datetime import datetime
import re
import uuid
    
def push_to_sqs(context):
    print("Attempting to push to SQS ::", context)
    current_time = datetime.now().strftime("%H:%M:%S %p")
    context['current_time'] = current_time
    payload = json.dumps(context)
    sqs = boto3.client('sqs')
    print("Pushed to sqs")
    res = sqs.send_message(QueueUrl=SQS_URL, MessageBody=payload)
    print(res)
    return res

def insert_into_history(context, session_attributes):
    print("Inserting into dynamodb")
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('restaurant-chat-history')
    response = table.put_item(Item={
        'session_id': session_attributes['current_session_id'], 
        'cruisine': context['cruisine']
        }
    )
    return response

def random_num():
    return(decimal.Decimal(random.randrange(1000, 50000))/100)

def get_slots(intent_request):
    return intent_request['sessionState']['intent']['slots']
    
def get_slot(intent_request, slotName):
    slots = get_slots(intent_request)
    if slots is not None and slotName in slots and slots[slotName] is not None:
        return slots[slotName]['value'].get('interpretedValue') or slots[slotName]['value'].get('originalValue')
    else:
        return None

def isTimeFormat(time_str):
    print("Time got from frontend", time_str)
    universal_time = None
    try:
        time_str = time_str.lower().replace(" ", "")
        org_time = time_str
        if time_str.endswith("am") or time_str.endswith("pm"):
            time_str = time_str[:-2]
            if ":" in time_str:
                universal_time = datetime.strptime(time_str, "%I:%M").strftime("%H:%M")
            elif time_str.endswith("oclock"):
                universal_time = datetime.strptime(time_str[:-6], "%I").strftime("%H:%M")
            else:
                universal_time = datetime.strptime(time_str, "%I").strftime("%H:%M")
            if org_time.endswith("pm"): # Add 12 hours to times in the afternoon/evening
                hour = int(universal_time.split(":")[0])
                if hour < 12:
                    hour += 12
                universal_time = f"{hour:02}:{universal_time.split(':')[1]}"
                
        elif time_str.endswith("oclock"):
            universal_time = datetime.strptime(time_str[:-6], "%I").strftime("%H:%M")
        else:
            universal_time = datetime.strptime(time_str, "%H:%M").strftime("%H:%M")
            
        print("Universal time :: ", universal_time)
        return True
    except ValueError:
        return False

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
        
def get_session_attributes(intent_request):
    sessionState = intent_request['sessionState']
    print("Session attributes, ", sessionState)
    if 'sessionAttributes' in sessionState:
        if 'current_session_id' not in sessionState['sessionAttributes']:
            sessionState['sessionAttributes']['current_session_id'] = str(uuid.uuid4())
        return sessionState['sessionAttributes']

    return {}

def close(intent_request, session_attributes, fulfillment_state, message, dialogState):
    intent_request['sessionState']['intent']['state'] = fulfillment_state
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': dialogState
            },
            'intent': intent_request['sessionState']['intent']
        },
        'messages': [message],
        'sessionId': intent_request['sessionId'],
        'requestAttributes': intent_request['requestAttributes'] if 'requestAttributes' in intent_request else None
    }


def validate_request(intent_request):
    session_attributes = get_session_attributes(intent_request)
    print(session_attributes)
    slots = get_slots(intent_request)
    print("Geetika Check data :: ", slots)
    cruisine = get_slot(intent_request, 'cruisine')
    location = get_slot(intent_request, 'location')
    time = get_slot(intent_request, 'time')
    numberofpeople = get_slot(intent_request, 'numberofpeople')
    phonenumber = get_slot(intent_request, 'phonenumber')
    context = {
        'cruisine': cruisine,
        'location': location,
        'time': time,
        'numberofpeople': numberofpeople,
        'phonenumber': phonenumber
    }
    print("CloudOne context:: ", context)
    message = ""
    if cruisine:
        if cruisine.lower() not in ALLOWED_CRUISINES:
            print("Invalid cruisine", cruisine)
            message += "Uh oh, we don't support that cuisine"
    if location:
        if location.lower() not in ALLOWED_LOCATIONS:
            print("Invalid location", location)
            message += "Oops, we support only Manhattan at the moment "
    if time:
        if not isTimeFormat(time):
            print("Invalid time. Express as 13:00 or 11:00pm", time)
            message += "Not a valid time for me to work with "
    if numberofpeople:
        if not numberofpeople.isdigit() or int(numberofpeople)< 1:
            print("Invalid numberofpeople", numberofpeople)
            message += "Sorry, not a valid number of people "
    # if phonenumber:
    #     if (not phonenumber.isdigit() or len(phonenumber) != 10):
    #         print("Invalid phonenumber", phonenumber)
    #         message += "Not a valid phonenumber "
    if phonenumber:
        if not validate_email(phonenumber):
            print("Invalid emailID", phonenumber)
            message += "Woopsy, That's an email I can't really contact "
    
    # Error message - Close with error
    if message:
        dialogAction = 'Close'
    elif all(context.values()): # All data received - push to SQS
        push_to_sqs(context)
        insert_into_history(context, session_attributes)
        del session_attributes['current_session_id']
        message = "I have received your request. I will notify you over a text once I have the list of restaurant suggestions"
        dialogAction = 'Close'
    else: # Still pending to receive - Delegate
        message = "Delegate"
        dialogAction = 'Delegate'

    data =  {
            'contentType': 'PlainText',
            'content': message
        }
    print("before close::", data)
    fulfillment_state = "Fulfilled"   
    
    return close(intent_request, session_attributes, fulfillment_state, data, dialogAction)   

def dispatch(intent_request):
    intent_name = intent_request['sessionState']['intent']['name']
    response = None
    print(intent_name)
    if intent_name != "RestaurantIntent":
        raise Exception('Intent with name ' + intent_name + ' not supported')
    else:
        return validate_request(intent_request)
        
        
def lambda_handler(event, context):
    # TODO implement
    # return {
    #     'statusCode': 200,
    #     'body': json.dumps('Hello from Lambda!')
    # }
    print(event)
    print(context)
    response = dispatch(event)
    return response