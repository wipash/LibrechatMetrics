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

# Define Prometheus metrics with date labels
unique_users_per_day_gauge = Gauge('librechat_unique_users_per_day', 'Unique users per day', ['date'])
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
                    '$dateToString': {'format': '%Y-%m-%d', 'date': '$createdAt'}
                },
                'users': {'$addToSet': '$user'}
            }
        },
        {
            '$project': {
                'date': '$_id',
                'uniqueUserCount': {'$size': '$users'}
            }
        },
        {
            '$sort': {'date': 1}
        }
    ]
    return list(messages_collection.aggregate(pipeline))


def collect_unique_users_per_day():
    results = get_unique_users_per_day()

    # Clear existing metrics to avoid duplication
    unique_users_per_day_gauge.clear()

    user_counts = []
    for record in results:
        date = record['date']
        unique_user_count = record['uniqueUserCount']
        unique_users_per_day_gauge.labels(date=date).set(unique_user_count)
        user_counts.append(unique_user_count)

    # Calculate average and standard deviation
    total_users = sum(user_counts)
    day_count = len(user_counts)

    if day_count > 0:
        average_users = total_users / day_count
        variance = sum((count - average_users) ** 2 for count in user_counts) / day_count
        stddev_users = variance ** 0.5

        average_users_per_day_gauge.set(average_users)
        stddev_users_per_day_gauge.set(stddev_users)
    else:
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
        message_counts = [user['messageCount'] for user in results]
        total_messages = sum(message_counts)
        average_messages = total_messages / total_users
        variance = sum((count - average_messages) ** 2 for count in message_counts) / total_users
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
