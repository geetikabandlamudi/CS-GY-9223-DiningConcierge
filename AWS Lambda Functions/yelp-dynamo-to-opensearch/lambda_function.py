import json
from opensearchpy import OpenSearch, RequestsHttpConnection
import boto3

index_name = 'restaurants'


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
    
def create_index(client):
    
    index_body = {
      'settings': {
        'index': {
          'number_of_shards': 4
        }
      }
    }
    response = client.indices.create(index_name, body=index_body)
    print('\nCreating index:')
    print(response)
    
def delete_index(client):
    response = client.indices.delete(
        index = index_name
    )
    print('\nDeleting index:')
    print(response)
    
def scan_table():
    with open('yelp-data.json') as data:
        data = json.load(data)
    print(len(data))
    print(type(data))
    print(type(data[0]))
    return data

def push_to_opensearch(client, data):
        
    for each_data in data:
        document = {'Restaurant': {'cuisine': each_data['cruisine'], 'restaurantId': each_data['id']}}
        response = None
        response = client.index(
            index = index_name,
            body = document,
            id = each_data['id'],
            refresh = True
        )
        print('\nAdding document:', document)
        print(response)

def lambda_handler(event, context):
    # TODO implement
    client = create_client()
    # delete_index(client)
    # create_index(client)
    data = scan_table()
    push_to_opensearch(client, data)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
