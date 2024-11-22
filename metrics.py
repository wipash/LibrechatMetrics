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


if __name__ == "__main__":
    count_users_per_day()
    print()
    count_messages_per_user()
