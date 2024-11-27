from pymongo import MongoClient
from datetime import datetime
from prometheus_client import start_http_server, Gauge
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect to MongoDB
client = MongoClient('mongodb://mongodb:27017/')
db = client['LibreChat']
messages_collection = db['messages']

# Define Prometheus metrics
unique_users_gauge = Gauge('librechat_unique_users_per_day', 'Unique users per day', ['date'])
average_users_gauge = Gauge('librechat_average_users_per_day', 'Average users per day')
messages_per_user_gauge = Gauge('librechat_messages_per_user', 'Messages per user', ['user'])
average_messages_gauge = Gauge('librechat_average_messages_per_user', 'Average messages per user')


def get_unique_users_per_day():
    pipeline = [
        {
            '$match': {
                'sender': 'User'  # Only consider messages from human users
            }
        },
        {
            '$group': {
                '_id': {
                    'year': {'$year': '$createdAt'},
                    'month': {'$month': '$createdAt'},
                    'day': {'$dayOfMonth': '$createdAt'},
                    'user': '$user'  # Group by user and date
                }
            }
        },
        {
            '$group': {
                '_id': {
                    'year': '$_id.year',
                    'month': '$_id.month',
                    'day': '$_id.day',
                },
                'uniqueUsers': {'$addToSet': '$_id.user'}  # Collect unique users
            }
        },
        {
            '$project': {
                'date': {
                    '$dateFromParts': {
                        'year': '$_id.year',
                        'month': '$_id.month',
                        'day': '$_id.day'
                    }
                },
                'userCount': {'$size': '$uniqueUsers'}  # Count unique users
            }
        },
        {
            '$sort': {'date': 1}  # Sort by date
        }
    ]

    return messages_collection.aggregate(pipeline)


def get_messages_per_user_pipeline():
    pipeline = [
        {
            '$match': {
                'sender': 'User',  # Only include messages from human users
            }
        },
        {
            '$group': {
                '_id': '$user',  # Group by user
                'messageCount': {'$sum': 1}
            }
        },
        {
            '$sort': {'messageCount': -1}  # Sort by message count descending
        }
    ]

    return messages_collection.aggregate(pipeline)


def collect_metrics():
    try:
        collect_unique_users_per_day()
        collect_average_users_per_day()
        collect_messages_per_user()
        collect_average_messages_per_user()
        logger.info("Metrics collected successfully.")
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")


def collect_unique_users_per_day():
    results = get_unique_users_per_day()

    # Clear existing metrics to avoid duplication
    unique_users_gauge.clear()

    for record in results:
        date = record['date'].strftime('%Y-%m-%d')
        count = record['userCount']
        unique_users_gauge.labels(date=date).set(count)


def collect_average_users_per_day():
    results = list(get_unique_users_per_day())

    if results:
        total_users = sum(record['userCount'] for record in results)
        day_count = len(results)
        average = total_users / day_count
        average_users_gauge.set(average)
    else:
        average_users_gauge.set(0)


def collect_messages_per_user():
    results = get_messages_per_user_pipeline()

    # Clear existing metrics to avoid duplication
    messages_per_user_gauge.clear()

    for record in results:
        user_id = str(record['_id'])  # Convert ObjectId or ID to string
        count = record['messageCount']
        messages_per_user_gauge.labels(user=user_id).set(count)


def collect_average_messages_per_user():
    pipeline = [
        {
            '$match': {
                'sender': 'User',  # Filter for messages from human users
            }
        },
        {
            '$group': {
                '_id': '$user',
                'messageCount': {'$sum': 1}
            }
        },
        {
            '$group': {
                '_id': None,
                'totalMessages': {'$sum': '$messageCount'},
                'userCount': {'$sum': 1}  # Count unique users
            }
        }
    ]

    result = messages_collection.aggregate(pipeline)

    for record in result:
        if record['userCount'] > 0:
            average = record['totalMessages'] / record['userCount']
            average_messages_gauge.set(average)
        else:
            average_messages_gauge.set(0)


if __name__ == "__main__":
    # Start up the server to expose the metrics.
    start_http_server(8000)  # Expose on port 8000
    logger.info("Metrics server is running on port 8000.")
    # Collect metrics at regular intervals
    while True:
        collect_metrics()
        time.sleep(60)  # Collect every 60 seconds
