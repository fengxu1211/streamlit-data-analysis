import json
from utils import opensearch
from opensearchpy import OpenSearch
from dotenv import load_dotenv
import os
import boto3

load_dotenv()

AOS_HOST = os.getenv('AOS_HOST', '')
AOS_PORT = os.getenv('AOS_PORT', 9200)
AOS_USER = os.getenv('AOS_USER', 'admin')
AOS_PASSWORD = os.getenv('AOS_PASSWORD', 'admin')
AOS_DOMAIN = os.getenv('AOS_DOMAIN', 'llm-data-analytics')
AOS_REGION = os.getenv('AOS_REGION')
AOS_INDEX = os.getenv('AOS_INDEX', 'uba')
AOS_TYPE = os.getenv('AOS_TYPE', 'uba')
BEDROCK_REGION = os.getenv('BEDROCK_REGION')

REGION_NAME = AOS_REGION
early_stop_record_count = 100
index_name = AOS_INDEX
opensearch_user = AOS_USER
opensearch_password = AOS_PASSWORD
# create opensearch domain
domain = AOS_DOMAIN

if AOS_HOST == '':
    # add a new opensearch domain named llm-data-analytics in us-west-2
    client = boto3.client('opensearch', region_name=REGION_NAME)
    client.create_domain(
        DomainName='llm-data-analytics',
        EngineVersion='OpenSearch_2.7',
        NodeToNodeEncryptionOptions={
            'Enabled': True
        },
        EncryptionAtRestOptions={
            'Enabled': True
        },
        AdvancedSecurityOptions={
            'Enabled': True,
            'InternalUserDatabaseEnabled': True,
            'MasterUserOptions': {
                'MasterUserName': 'admin',
                'MasterUserPassword': 'Admin&123'
            }
        },
        DomainEndpointOptions={
            'EnforceHTTPS': True
        },
        EBSOptions={
            'EBSEnabled': True,
            'VolumeType': 'gp2',
            'VolumeSize': 10
        }
    )

    # initiate AWS OpenSearch client and insert new data into the index
    opensearch_client = opensearch.get_opensearch_cluster_client(domain, opensearch_user, opensearch_password,
                                                                 REGION_NAME,
                                                                 index_name)
else:
    auth = (opensearch_user, opensearch_password)
    host = AOS_HOST
    port = AOS_PORT
    # Create the client with SSL/TLS enabled, but hostname verification disabled.
    opensearch_client = OpenSearch(
        hosts=[{'host': host, 'port': port}],
        http_compress=True,  # enables gzip compression for request bodies
        http_auth=auth,
        use_ssl=True,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False
    )

bulk_questions = [
    {"question": "What is the average price of items purchased by female users under 30 years old?",
     "sql": '''SELECT AVG(price)
FROM interactions i 
JOIN items it ON i.item_id = it.item_id
JOIN users u ON i.user_id = u.user_id
WHERE u.gender = 'female' AND u.age < 30 AND i.event_type = 'purchase'
'''},
    {"question": "What are the top 3 categories of items viewed by male users over 40 years old? ",
     "sql": '''SELECT category_l1, COUNT(*) AS views
FROM interactions i
JOIN items it ON i.item_id = it.item_id 
JOIN users u ON i.user_id = u.user_id
WHERE u.gender = 'male' AND u.age > 40 AND i.event_type = 'view'
GROUP BY category_l1
ORDER BY views DESC
LIMIT 3
'''},
    {"question": "How many items were purchased at a discount by users aged 18-25?",
     "sql": '''SELECT COUNT(DISTINCT item_id)
FROM interactions i
JOIN users u ON i.user_id = u.user_id
WHERE u.age BETWEEN 18 AND 25  
AND i.event_type = 'purchase'
AND i.discount != ''
'''},
    {"question": "What is the conversion rate from views to purchases for each product category?",
     "sql": '''WITH views AS (
  SELECT category_l1, COUNT(*) AS views
  FROM interactions i 
  JOIN items it ON i.item_id = it.item_id
  WHERE i.event_type = 'view' 
  GROUP BY category_l1
),
purchases AS (
  SELECT category_l1, COUNT(*) AS purchases
  FROM interactions i
  JOIN items it ON i.item_id = it.item_id
  WHERE i.event_type = 'purchase'
  GROUP BY category_l1  
)
SELECT v.category_l1, purchases / views AS conversion_rate
FROM views v
JOIN purchases p ON v.category_l1 = p.category_l1
'''},
    {"question": "What are the top 5 most viewed items by users under 30?",
     "sql": '''SELECT item_id, COUNT(*) AS views
FROM interactions i
JOIN users u ON i.user_id = u.user_id
WHERE u.age < 30
AND i.event_type = 'view'  
GROUP BY item_id
ORDER BY views DESC
LIMIT 5
'''},
    {"question": "How many male vs female users made a purchase in the last 30 days?",
     "sql": '''
SELECT gender, COUNT(DISTINCT user_id) AS users 
FROM interactions i
JOIN users u ON i.user_id = u.user_id
WHERE i.event_type = 'purchase'
AND i.timestamp >= UNIX_TIMESTAMP(DATE_SUB(NOW(), INTERVAL 30 DAY)) 
GROUP BY gender
'''},
    {"question": "What is the distribution of ages for users who purchased items priced over $50?",
     "sql": '''SELECT age, COUNT(DISTINCT user_id) AS users
FROM interactions i
JOIN users u ON i.user_id = u.user_id 
JOIN items it ON i.item_id = it.item_id
WHERE i.event_type = 'purchase'
AND it.price > 50
GROUP BY age
'''},
    {"question": "What is the most common category for discounted items purchased by female users under 25?",
     "sql": '''SELECT category_l1, COUNT(*) AS purchases
FROM interactions i
JOIN items it ON i.item_id = it.item_id  
JOIN users u ON i.user_id = u.user_id
WHERE u.gender = 'female' AND u.age < 25
AND i.discount != ''
AND i.event_type = 'purchase' 
GROUP BY category_l1
ORDER BY purchases DESC
LIMIT 1
'''},
    {"question": "How many items were purchased multiple times by the same user? ",
     "sql": '''SELECT COUNT(*) 
FROM (
  SELECT item_id, user_id, COUNT(*) AS num_purchases
  FROM interactions
  WHERE event_type = 'purchase'
  GROUP BY item_id, user_id
  HAVING num_purchases > 1
) t
'''},
    {"question": "What items have been viewed but never purchased?",
     "sql": '''SELECT item_id
FROM interactions i
WHERE i.event_type = 'view'
AND item_id NOT IN (
  SELECT item_id 
  FROM interactions
  WHERE event_type = 'purchase'
)
'''},
    {"question": "What is the total revenue generated from purchases by users aged 30-40? ",
     "sql": '''SELECT SUM(price) AS total_revenue
FROM interactions i
JOIN items it ON i.item_id = it.item_id  
JOIN users u ON i.user_id = u.user_id
WHERE u.age BETWEEN 30 AND 40
AND i.event_type = 'purchase'
'''},
    {"question": "How many times has each item been added to cart on average?",
     "sql": '''SELECT item_id, AVG(added_to_cart) AS avg_cart_adds
FROM (
  SELECT item_id, COUNT(*) AS added_to_cart
  FROM interactions
  WHERE event_type = 'add_to_cart'
  GROUP BY item_id
) t
GROUP BY item_id
'''},
    {"question": "What percentage of purchases under $10 were made by female users?",
     "sql": '''WITH purchases AS (
  SELECT * 
  FROM interactions i
  JOIN items it ON i.item_id = it.item_id
  WHERE i.event_type = 'purchase' AND price < 10
)

SELECT COUNT(*) / (SELECT COUNT(*) FROM purchases) AS percentage
FROM purchases p
JOIN users u ON p.user_id = u.user_id 
WHERE u.gender = 'female'
'''},
    {"question": "What is the click-through rate from product views to product detail page views?",
     "sql": '''WITH product_views AS (
  SELECT COUNT(*) AS views 
  FROM interactions 
  WHERE event_type = 'view'
),

detail_views AS (
  SELECT COUNT(*) AS detail_views
  FROM interactions
  WHERE event_type = 'detail_view'  
)

SELECT detail_views / views AS ctr
FROM product_views, detail_views
'''},
    {"question": "What are the top 3 most commonly purchased item categories amongst users under 25?",
     "sql": '''SELECT category_l1, COUNT(*) AS purchases
FROM interactions i 
JOIN items it ON i.item_id = it.item_id
JOIN users u ON i.user_id = u.user_id
WHERE u.age < 25 AND i.event_type = 'purchase'
GROUP BY category_l1
ORDER BY purchases DESC
LIMIT 3
'''},
    {"question": "How many times has each product been purchased on average? ",
     "sql": '''SELECT item_id, AVG(purchases) AS avg_purchases
FROM (
  SELECT item_id, COUNT(*) AS purchases
  FROM interactions
  WHERE event_type = 'purchase'
  GROUP BY item_id  
) t
GROUP BY item_id
'''},
    {"question": "What is the percentage of discounts greater than 30% for purchases made by male users?",
     "sql": '''WITH male_purchases AS (
  SELECT *
  FROM interactions i
  JOIN users u ON i.user_id = u.user_id 
  WHERE u.gender = 'male' AND i.event_type = 'purchase'   
)

SELECT COUNT(*) / (SELECT COUNT(*) FROM male_purchases) AS percentage
FROM male_purchases
WHERE CAST(discount AS FLOAT) > 0.3
'''},
    {"question": "How many users have only viewed but never purchased items?",
     "sql": '''SELECT COUNT(DISTINCT user_id) 
FROM interactions
WHERE user_id NOT IN (
  SELECT DISTINCT user_id
  FROM interactions
  WHERE event_type = 'purchase'
)  
AND event_type = 'view'
'''},
    {"question": "What categories have the highest and lowest view-to-purchase conversion rates?",
     "sql": '''WITH views AS (
  SELECT category_l1, COUNT(*) AS views
  FROM interactions i
  JOIN items it ON i.item_id = it.item_id
  WHERE event_type = 'view'
  GROUP BY category_l1
),

purchases AS (
  SELECT category_l1, COUNT(*) AS purchases
  FROM interactions i
  JOIN items it ON i.item_id = it.item_id
  WHERE event_type = 'purchase'
  GROUP BY category_l1
)

SELECT v.category_l1, purchases/views AS conversion_rate
FROM views v
JOIN purchases p ON v.category_l1 = p.category_l1
ORDER BY conversion_rate DESC
LIMIT 1

UNION 

SELECT v.category_l1, purchases/views AS conversion_rate
FROM views v
JOIN purchases p ON v.category_l1 = p.category_l1
ORDER BY conversion_rate ASC
LIMIT 1
'''},
    {"question": "Which item has the highest view to purchase percentage?",
     "sql": '''WITH views AS (
  SELECT item_id, COUNT(*) AS views
  FROM interactions
  WHERE event_type = 'view'
  GROUP BY item_id  
),

purchases AS (
  SELECT item_id, COUNT(*) AS purchases
  FROM interactions
  WHERE event_type = 'purchase'
  GROUP BY item_id
)

SELECT v.item_id, purchases/views AS view_to_purchase_pct
FROM views v
JOIN purchases p ON v.item_id = p.item_id
ORDER BY view_to_purchase_pct DESC
LIMIT 1
'''},
]


def create_vector_embedding_with_bedrock(text, index_name, bedrock_client):
    payload = {"inputText": f"{text}"}
    body = json.dumps(payload)
    modelId = "amazon.titan-embed-text-v1"
    accept = "application/json"
    contentType = "application/json"

    response = bedrock_client.invoke_model(
        body=body, modelId=modelId, accept=accept, contentType=contentType
    )
    response_body = json.loads(response.get("body").read())

    embedding = response_body.get("embedding")
    return {"_index": index_name, "text": text, "vector_field": embedding}


def get_bedrock_client(region):
    bedrock_client = boto3.client("bedrock-runtime", region_name=region)
    return bedrock_client


# Check if to delete OpenSearch index with the argument passed to the script --recreate 1
# response = opensearch.delete_opensearch_index(opensearch_client, name)

exists = opensearch.check_opensearch_index(opensearch_client, index_name)
if not exists:
    print("Creating OpenSearch index")
    success = opensearch.create_index(opensearch_client, index_name)
    if success:
        print("Creating OpenSearch index mapping")
        success = opensearch.create_index_mapping(opensearch_client, index_name)
        print(f"OpenSearch Index mapping created")
else:
    print("Index already exists. Exit with 0 now.")
    exit(0)

all_records = bulk_questions

# Initialize bedrock client
bedrock_client = get_bedrock_client(BEDROCK_REGION)

# Vector embedding using Amazon Bedrock Titan text embedding
all_json_records = []
print(f"Creating embeddings for records")

# using the arg --early-stop
i = 0
for record in all_records:
    i += 1
    records_with_embedding = create_vector_embedding_with_bedrock(record['question'], index_name, bedrock_client)
    print(f"Embedding for record {i} created")
    records_with_embedding['sql'] = record['sql']
    all_json_records.append(records_with_embedding)
    if i % 500 == 0 or i == len(all_records) - 1:
        # Bulk put all records to OpenSearch
        success, failed = opensearch.put_bulk_in_opensearch(all_json_records, opensearch_client)
        all_json_records = []
        print(f"Documents saved {success}, documents failed to save {failed}")

print("Finished creating records using Amazon Bedrock Titan text embedding")
