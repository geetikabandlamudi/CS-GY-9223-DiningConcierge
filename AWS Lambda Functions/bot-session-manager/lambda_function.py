import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
from opensearchpy import OpenSearch, RequestsHttpConnection
from datetime import datetime
import ast

index_name = 'restaurants'

def get_item(session_id):
    dynamo_client = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamo_client.Table('restaurant-chat-history')
    response = table.query(KeyConditionExpression=Key('session_id').eq(session_id))
    print(response)
    return response

def create_client():
    host = 'https://search-yelp-restaurants-d3u6dmgrb43vnv5ggpqfqnuwra.us-east-1.es.amazonaws.com'
    port = 443
    auth = ('admin', 'Admin1230!')

    client = OpenSearch(
        hosts = [host],
        http_auth = auth,
        use_ssl = True,
        verify_certs = True,
        ssl_assert_hostname = False,
        ssl_show_warn = False,
        connection_class = RequestsHttpConnection
    )
    return client


def query_elastic_search(cruisine, client):
    resp = client.search(
        index=index_name,
        size=2,
        body={
            "query": {
                "bool": {
                    "must": {
                        "match_phrase": {
                            "Restaurant.cuisine": cruisine.capitalize(),
                        }
                    },
                },
            },            
        }
    )
    return resp['hits']['hits']

def form_message_body(cruisine, data):
    dynamo_client = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamo_client.Table('yelp-restaurants')
    if not data:
        body = "Oops, with the data you have provided, we couldn't find any restaurants"
    else:
        message = 'I have curated these restaurants based on your previous search for the ' + cruisine + ' cuisine:\n\n'
        for each_data in data:
            restaurant_id = each_data['_source']['Restaurant']['restaurantId']
            cruisine = each_data['_source']['Restaurant']['cuisine']
            response = table.query(KeyConditionExpression=Key('cruisine').eq(cruisine) & Key('id').eq(restaurant_id))
            items = response['Items'][0]
            json_data = ast.literal_eval(json.dumps(items['location'])).replace("\'", "\"").replace("None", "\"\"")
            json_data = json.loads(json_data)
            address = " ".join(json_data['display_address'])
            message = message + items['name'] + ' Address: ' + address + ' , Phone: ' + items['display_phone'] + "\n"
    print(message)
    return message
    
def get_recommendations(cruisine):
    client = create_client()
    data = query_elastic_search(cruisine, client)
    message = form_message_body(cruisine, data)
    return message

def format_message(msg):
    if not msg:
        return ''
    response = {
        'messages': [
            {'type': 'unstructured',
            'unstructured': {'text': msg}}]
    }
    return response
    
def lambda_handler(event, context):
    print(event)
    print(context)
    res = ''
    if event.get('current_session_id'):
        data = get_item(event['current_session_id'])
        if data.get('Items'):
            cruisine = data['Items'][0]['cruisine']
            res = get_recommendations(cruisine)
    response = format_message(res)
    return response
    
