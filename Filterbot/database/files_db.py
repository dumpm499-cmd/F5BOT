import logging
from motor.motor_asyncio import AsyncIOMotorClient
from config import DATABASE_URI, DATABASE_NAME
from datetime import datetime

logger = logging.getLogger(__name__)

client   = AsyncIOMotorClient(DATABASE_URI)
db       = client[DATABASE_NAME]
files_col = db['files']

# ── Index Setup ────────────────────────────────────────────────
async def ensure_indexes():
    """Create text index on file_name for fast search. Call once on startup."""
    await files_col.create_index([('file_name', 'text')], name='file_name_text')
    await files_col.create_index('file_unique_id', unique=True, name='unique_file_id')
    logger.info("Database indexes ensured.")


# ── Save a File ────────────────────────────────────────────────
async def save_file(media) -> tuple[bool, str]:
    """
    Save a file to the database.
    Returns (True, 'saved') if new file saved.
    Returns (False, 'duplicate') if file already exists — silently skipped.
    """
    try:
        await files_col.insert_one({
            '_id':            media.file_unique_id,
            'file_unique_id': media.file_unique_id,
            'file_id':        media.file_id,
            'file_name':      getattr(media, 'file_name', '') or '',
            'file_size':      getattr(media, 'file_size', 0) or 0,
            'mime_type':      getattr(media, 'mime_type', '') or '',
            'caption':        media.caption or '',
            'message_id':     media.message_id,
            'chat_id':        media.chat_id,
            'media_type':     media.media_type,
            'indexed_at':     datetime.utcnow(),
        })
        return True, 'saved'
    except Exception as e:
        if 'duplicate key' in str(e).lower() or 'E11000' in str(e):
            return False, 'duplicate'
        logger.exception(f"Error saving file: {e}")
        return False, 'error'


# ── Search Files ───────────────────────────────────────────────
async def search_files(query: str, offset: int = 0, limit: int = 10) -> tuple[list, int]:
    """
    Search files by keyword using MongoDB text search + regex fallback.
    Returns (results_list, total_count).
    """
    query = query.strip()
    if not query:
        return [], 0

    # Build search filter — text search + regex for partial match
    search_filter = {
        '$or': [
            {'$text': {'$search': query}},
            {'file_name': {'$regex': '.*' + '.*'.join(query.split()) + '.*', '$options': 'i'}},
            {'caption':   {'$regex': '.*' + '.*'.join(query.split()) + '.*', '$options': 'i'}},
        ]
    }

    total   = await files_col.count_documents(search_filter)
    cursor  = files_col.find(search_filter).skip(offset).limit(limit)
    results = await cursor.to_list(length=limit)
    return results, total


# ── Total Files ────────────────────────────────────────────────
async def total_files() -> int:
    return await files_col.count_documents({})


# ── Delete a File ──────────────────────────────────────────────
async def delete_file(file_unique_id: str) -> bool:
    result = await files_col.delete_one({'_id': file_unique_id})
    return result.deleted_count > 0


# ── Delete All Files ───────────────────────────────────────────
async def delete_all_files() -> int:
    result = await files_col.delete_many({})
    return result.deleted_count
