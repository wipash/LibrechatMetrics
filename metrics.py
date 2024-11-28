from pymongo import MongoClient
from prometheus_client import start_http_server, Gauge
import time
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env.example file
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get MongoDB URI from environment variable
mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://mongodb:27017/')
prometheus_port = int(os.getenv('PROMETHEUS_PORT', '8000'))

# Connect to MongoDB
client = MongoClient(mongodb_uri)
db = client['LibreChat']
messages_collection = db['messages']

# Define Prometheus metrics with date labels
unique_users_per_day_gauge = Gauge('librechat_unique_users_per_day', 'Unique users per day', ['date'])
average_users_per_day_gauge = Gauge('librechat_average_users_per_day', 'Average users per day')
stddev_users_per_day_gauge = Gauge('librechat_stddev_users_per_day', 'Standard deviation of users per day')
average_messages_per_user_gauge = Gauge('librechat_average_messages_per_user', 'Average messages per user')
stddev_messages_per_user_gauge = Gauge('librechat_stddev_messages_per_user', 'Standard deviation of messages per user')
# Define the gauge with 'model' and 'date' labels
messages_per_model_per_day_gauge = Gauge(
    'librechat_messages_per_model_per_day',
    'Messages per model per day',
    ['model', 'date']
)
average_messages_per_model_per_day_gauge = Gauge(
    'librechat_average_messages_per_model_per_day',
    'Average messages per model per day',
    ['model']
)
stddev_messages_per_model_per_day_gauge = Gauge(
    'librechat_stddev_messages_per_model_per_day',
    'Standard deviation of messages per model per day',
    ['model']
)


def get_model_daily_message_stats():
    pipeline = [
        {
            '$match': {
                'sender': {'$ne': 'User'}
            }
        },
        {
            '$group': {
                '_id': {
                    'model': '$model',
                    'date': {
                        '$dateToString': {
                            'format': '%Y-%m-%d',
                            'date': '$createdAt'
                        }
                    }
                },
                'dailyMessageCount': {'$sum': 1}
            }
        },
        {
            '$group': {
                '_id': '$_id.model',
                'dailyCounts': {'$push': '$dailyMessageCount'},
                'totalMessages': {'$sum': '$dailyMessageCount'},
                'dayCount': {'$sum': 1}
            }
        }
    ]
    return list(messages_collection.aggregate(pipeline))


def collect_average_and_stddev_messages_per_model_per_day():
    results = get_model_daily_message_stats()

    # Clear existing metrics to avoid duplication
    average_messages_per_model_per_day_gauge.clear()
    stddev_messages_per_model_per_day_gauge.clear()

    for record in results:
        model = record['_id'] if record['_id'] else 'Unknown'
        daily_counts = record['dailyCounts']
        day_count = record['dayCount']
        total_messages = record['totalMessages']

        if day_count > 0:
            # Calculate average
            average_messages = total_messages / day_count

            # Calculate standard deviation
            variance = sum((count - average_messages) ** 2 for count in daily_counts) / day_count
            stddev_messages = variance ** 0.5

            # Set metrics
            average_messages_per_model_per_day_gauge.labels(model=model).set(average_messages)
            stddev_messages_per_model_per_day_gauge.labels(model=model).set(stddev_messages)
        else:
            average_messages_per_model_per_day_gauge.labels(model=model).set(0)
            stddev_messages_per_model_per_day_gauge.labels(model=model).set(0)


def get_messages_per_model_per_day():
    pipeline = [
        {
            '$match': {
                'sender': {'$ne': 'User'}  # Include messages not from 'User'
            }
        },
        {
            '$group': {
                '_id': {
                    'model': '$model',
                    'date': {
                        '$dateToString': {
                            'format': '%Y-%m-%d',
                            'date': '$createdAt'
                        }
                    }
                },
                'messageCount': {'$sum': 1}
            }
        },
        {
            '$sort': {
                '_id.date': 1,
                '_id.model': 1
            }
        }
    ]
    return list(messages_collection.aggregate(pipeline))


def collect_messages_per_model_per_day():
    results = get_messages_per_model_per_day()

    # Clear existing metrics to avoid duplication
    messages_per_model_per_day_gauge.clear()

    for record in results:
        model = record['_id']['model'] if record['_id']['model'] else 'Unknown'
        date = record['_id']['date']
        count = record['messageCount']
        messages_per_model_per_day_gauge.labels(model=model, date=date).set(count)


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
        collect_messages_per_model_per_day()
        collect_average_and_stddev_messages_per_model_per_day()
        logger.info("Metrics collected successfully.")
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")


if __name__ == "__main__":
    # Start up the server to expose the metrics.
    start_http_server(prometheus_port)  # Use port from environment variable
    logger.info("Metrics server is running on port 8000.")
    # Collect metrics at regular intervals
    while True:
        collect_metrics()
        time.sleep(60)  # Collect every 60 seconds
