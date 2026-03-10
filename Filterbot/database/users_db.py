from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE_URI, DATABASE_NAME
from datetime import datetime

client = AsyncIOMotorClient(DATABASE_URI)
db     = client[DATABASE_NAME]

users_col = db['users']

async def add_user(user_id: int, name: str, username: str = None):
    if not await user_exists(user_id):
        await users_col.insert_one({
            '_id': user_id,
            'name': name,
            'username': username,
            'joined': datetime.utcnow()
        })

async def user_exists(user_id: int) -> bool:
    return bool(await users_col.find_one({'_id': user_id}))

async def get_all_users():
    return users_col.find({})

async def total_users() -> int:
    return await users_col.count_documents({})

async def delete_user(user_id: int):
    await users_col.delete_one({'_id': user_id})
