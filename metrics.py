from pymongo import MongoClient
from datetime import datetime

# Connect to MongoDB
client = MongoClient('mongodb://mongodb:27017/')
db = client['LibreChat']
messages_collection = db['messages']


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
                'uniqueUsers': {'$addToSet': '$_id.user'}  # Count distinct users
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
                'userCount': {'$size': '$uniqueUsers'}  # Get the count of unique users
            }
        },
        {
            '$sort': {'date': 1}  # Sort by date
        }
    ]

    return messages_collection.aggregate(pipeline)


def count_unique_users_per_day():
    results = get_unique_users_per_day()

    print("Number of unique users per day:")
    for record in results:
        date = record['date'].strftime('%Y-%m-%d')
        count = record['userCount']
        print(f"{date}: {count} unique users")


def average_users_per_day():
    results = list(get_unique_users_per_day())

    if results:
        total_users = sum(record['userCount'] for record in results)
        day_count = len(results)

        average = total_users / day_count
        print(f"Average users per day: {average:.2f}")
    else:
        print("No users found.")


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


def count_messages_per_user():
    results = get_messages_per_user_pipeline()

    print("Number of messages per user:")
    for record in results:
        user_id = str(record['_id'])  # Convert ObjectId or ID to string
        count = record['messageCount']
        print(f"User {user_id}: {count} messages")


def average_messages_per_user():
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
            print(f"Average messages per user: {average:.2f}")
        else:
            print("No messages found.")


if __name__ == "__main__":
    log_file_path = '/opt/librechat/metrics/logs/logfile.log'
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open(log_file_path, 'a') as f:
        f.write(f'[{current_date}] Running metrics...\n')

    count_unique_users_per_day()
    print()
    average_users_per_day()
    print()
    count_messages_per_user()
    print()
    average_messages_per_user()
