from pymongo import MongoClient
from datetime import datetime

# Connect to MongoDB
client = MongoClient('mongodb://mongodb:27017/')
db = client['LibreChat']
users_collection = db['users']
messages_collection = db['messages']


# Function to count users per day
def count_users_per_day():
    pipeline = [
        {
            '$group': {
                '_id': {
                    'year': {'$year': '$createdAt'},
                    'month': {'$month': '$createdAt'},
                    'day': {'$dayOfMonth': '$createdAt'}
                },
                'userCount': {'$sum': 1}
            }
        },
        {
            '$sort': {'_id': 1}
        }
    ]
    results = users_collection.aggregate(pipeline)
    print("Number of users per day:")
    for record in results:
        date = datetime(
            record['_id']['year'],
            record['_id']['month'],
            record['_id']['day']
        ).strftime('%Y-%m-%d')
        count = record['userCount']
        print(f"{date}: {count} users")


def average_users_per_day():
    pipeline = [
        {
            '$group': {
                '_id': {
                    'year': {'$year': '$createdAt'},
                    'month': {'$month': '$createdAt'},
                    'day': {'$dayOfMonth': '$createdAt'}
                },
                'userCount': {'$sum': 1}
            }
        },
        {
            '$group': {
                '_id': None,
                'totalUsers': {'$sum': '$userCount'},
                'daysCount': {'$sum': 1}
            }
        }
    ]

    result = users_collection.aggregate(pipeline)

    for record in result:
        average = record['totalUsers'] / record['daysCount']
        print(f"Average users per day: {average:.2f}")


# Function to count messages per user
def count_messages_per_user():
    pipeline = [
        {
            '$match': {
                'user': {'$exists': True, '$ne': None}  # Ensure user field exists
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
    results = messages_collection.aggregate(pipeline)
    print("Number of messages per user:")
    for record in results:
        user_id = str(record['_id'])  # Convert ObjectId or ID to string
        count = record['messageCount']
        print(f"User {user_id}: {count} messages")


def average_messages_per_user():
    pipeline = [
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
                'userCount': {'$sum': 1}  # Counting the number of unique users
            }
        }
    ]

    result = messages_collection.aggregate(pipeline)

    for record in result:
        if record['userCount'] > 0:
            average = record['totalMessages'] / record['userCount']
            print(f"Average messages per user: {average:.2f}")
        else:
            print("No messages found.")


if __name__ == "__main__":
    log_file_path = '/opt/librechat/metrics/logs/logfile.log'
    current_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open(log_file_path, 'a') as f:
        f.write(f'[{current_date}] Running metrics...\n')
    count_users_per_day()
    print()
    average_users_per_day()
    print()
    count_messages_per_user()
    print()
    average_messages_per_user()
