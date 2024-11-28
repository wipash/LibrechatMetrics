from pymongo import MongoClient
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
unique_users_per_day_gauge = Gauge('librechat_unique_users_per_day', 'Unique users per day')
average_users_per_day_gauge = Gauge('librechat_average_users_per_day', 'Average users per day')
stddev_users_per_day_gauge = Gauge('librechat_stddev_users_per_day', 'Standard deviation of users per day')
average_messages_per_user_gauge = Gauge('librechat_average_messages_per_user', 'Average messages per user')
stddev_messages_per_user_gauge = Gauge('librechat_stddev_messages_per_user', 'Standard deviation of messages per user')


def get_unique_users_per_day():
    pipeline = [
        {
            '$match': {
                'sender': 'User'
            }
        },
        {
            '$group': {
                '_id': {
                    'date': {
                        '$dateToString': {'format': '%Y-%m-%d', 'date': '$createdAt'}
                    },
                    'user': '$user'
                }
            }
        },
        {
            '$group': {
                '_id': '$_id.date',
                'uniqueUsers': {'$sum': 1}
            }
        },
        {
            '$sort': {'_id': 1}
        }
    ]
    return list(messages_collection.aggregate(pipeline))


def collect_unique_users_per_day():
    results = get_unique_users_per_day()
    total_users = sum(record['uniqueUsers'] for record in results)
    day_count = len(results)

    if day_count > 0:
        average_users = total_users / day_count
        variance = sum((record['uniqueUsers'] - average_users) ** 2 for record in results) / day_count
        stddev_users = variance ** 0.5

        unique_users_per_day_gauge.set(total_users)
        average_users_per_day_gauge.set(average_users)
        stddev_users_per_day_gauge.set(stddev_users)
    else:
        unique_users_per_day_gauge.set(0)
        average_users_per_day_gauge.set(0)
        stddev_users_per_day_gauge.set(0)


def collect_average_and_stddev_messages_per_user():
    pipeline = [
        {
            '$match': {
                'sender': 'User'
            }
        },
        {
            '$group': {
                '_id': '$user',
                'messageCount': {'$sum': 1}
            }
        }
    ]
    results = list(messages_collection.aggregate(pipeline))
    total_users = len(results)

    if total_users > 0:
        total_messages = sum(user['messageCount'] for user in results)
        average_messages = total_messages / total_users
        variance = sum((user['messageCount'] - average_messages) ** 2 for user in results) / total_users
        stddev_messages = variance ** 0.5

        average_messages_per_user_gauge.set(average_messages)
        stddev_messages_per_user_gauge.set(stddev_messages)
    else:
        average_messages_per_user_gauge.set(0)
        stddev_messages_per_user_gauge.set(0)


def collect_metrics():
    try:
        collect_unique_users_per_day()
        collect_average_and_stddev_messages_per_user()
        logger.info("Metrics collected successfully.")
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")


if __name__ == "__main__":
    # Start up the server to expose the metrics.
    start_http_server(8000)  # Expose on port 8000
    logger.info("Metrics server is running on port 8000.")
    # Collect metrics at regular intervals
    while True:
        collect_metrics()
        time.sleep(60)  # Collect every 60 seconds
