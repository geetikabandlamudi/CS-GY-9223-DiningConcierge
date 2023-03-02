import json
from opensearchpy import OpenSearch, RequestsHttpConnection
import boto3
from boto3.dynamodb.conditions import Key, Attr
import ast
from email.mime.text import MIMEText
import smtplib
from datetime import datetime

index_name = 'restaurants'
SQS_URL = 'https://sqs.us-east-1.amazonaws.com/023011713484/restaurant-requests'


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
    
def query_elastic_search(content, client):
    resp = client.search(
        index=index_name,
        size=5,
        body={
            "query": {
                "bool": {
                    "must": {
                        "match_phrase": {
                            "Restaurant.cuisine": content['cruisine'],
                        }
                    },
                },
            },            
        }
    )
    return resp['hits']['hits']

def form_email_body(content, data):
    dynamo_client = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamo_client.Table('yelp-restaurants')
    if not data:
        body = "Oops, with the data you have provided, we couldn't find any restaurants"
    else:
        message = 'I have curated these restaurants for ' + content['cruisine'] + ' cuisine:\n\n'
        for each_data in data:
            # print(each_data)
            restaurant_id = each_data['_source']['Restaurant']['restaurantId']
            cruisine = each_data['_source']['Restaurant']['cuisine']
            response = table.query(KeyConditionExpression=Key('cruisine').eq(cruisine) & Key('id').eq(restaurant_id))
            items = response['Items'][0]
            json_data = ast.literal_eval(json.dumps(items['location'])).replace("\'", "\"").replace("None", "\"\"")
            json_data = json.loads(json_data)
            address = " ".join(json_data['display_address'])

            message = message + items['name'] + ' Address: ' + address + ' , Phone: ' + items['display_phone'] + "\n"
    message = message + "Thanks. Have a great meal!"
    print(message)
    return message


def handler_name(event, context):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('My_Favorite_Movies')
    response = table.query(
    KeyConditionExpression=Key('year').eq('1999')
    )
    items = response['Items']
    
    return items

def send_email(content, mail_body):
    gmail_user = "violetorigin1999@gmail.com"
    gmail_app_password = "qcuktepgtxuayjln"
    sent_from = gmail_user
    sent_to = [content['phonenumber']]
    sent_subject = "Restaurant Suggestions"

    try:
        msg = MIMEText(mail_body)
        msg['Subject'] = sent_subject
        msg['From'] = sent_from
        msg['To'] = ', '.join(sent_to)
        smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        smtp_server.login(gmail_user, gmail_app_password)
        smtp_server.sendmail(sent_from, sent_to, msg.as_string())
        smtp_server.quit()
    except Exception as exception:
        print("Error: %s!\n\n" % exception)

def send_email_through_ses(content, mail_body):
    SENDER = "violetorigin1999@gmail.com"
    RECIPIENT = content['phonenumber']
    AWS_REGION = "us-east-1"
    client = boto3.client('ses',region_name=AWS_REGION)
    try:
        response = client.send_email(
            Destination={'ToAddresses': [RECIPIENT,]},
            Message={
                'Body': {'Text': {'Data': mail_body}},
                'Subject': {'Data': "Restaurant Suggestions"},
            },
            Source=SENDER
        )

    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])

def get_message_from_sqs():
    now = datetime.now()
    current_time = now.strftime("%S")
    sqs_client = boto3.client("sqs", region_name="us-east-1")
    response = sqs_client.receive_message(
        QueueUrl = SQS_URL)
    print(response)
    if response.get('Messages'):
        print(response['Messages'])
        return response['Messages']
    else:
        print("Queue is empty")
        return []
    
def delete_from_queue(receipt_handle):
    sqs_client = boto3.client("sqs", region_name="us-east-1")
    sqs_client.delete_message(QueueUrl=SQS_URL, ReceiptHandle=receipt_handle)
    print('Received and deleted message:')
    
def lambda_handler(event, context):
    # TODO implement
    # records = event['Records']
    records = get_message_from_sqs()
    client = create_client()
    
    for record in records:
        content = record['Body']
        receipt_handle = record['ReceiptHandle']
        content = json.loads(content)
        print(content)
        data = query_elastic_search(content, client)
        print(data)
        mail_body = form_email_body(content, data)
        send_email_through_ses(content, mail_body)
        delete_from_queue(receipt_handle)
        
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
