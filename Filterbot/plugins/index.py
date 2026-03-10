import logging
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, ChannelInvalid, ChatAdminRequired
from database import save_file
from config import ADMINS, FILE_CHANNEL

logger = logging.getLogger(__name__)

# Media types we care about
MEDIA_TYPES = ('document', 'video', 'audio', 'photo', 'animation', 'voice', 'video_note')

# Track ongoing index tasks per admin so we can cancel
_index_tasks: dict[int, asyncio.Task] = {}


def get_media(message: Message):
    """Extract media object from a message, return None if not a media message."""
    for attr in MEDIA_TYPES:
        media = getattr(message, attr, None)
        if media:
            return media, attr
    return None, None


def build_file_obj(message: Message, media, media_type: str):
    """Build a simple object to pass to save_file."""
    class FileObj:
        pass
    f = FileObj()
    f.file_id        = media.file_id
    f.file_unique_id = media.file_unique_id
    f.file_name      = getattr(media, 'file_name', None) or message.caption or f'file_{message.id}'
    f.file_size      = getattr(media, 'file_size', 0) or 0
    f.mime_type      = getattr(media, 'mime_type', '') or ''
    f.caption        = message.caption or ''
    f.message_id     = message.id
    f.chat_id        = message.chat.id
    f.media_type     = media_type
    return f


# ── /index command ─────────────────────────────────────────────
@Client.on_message(filters.command('index') & filters.private & filters.user(ADMINS))
async def index_command(bot: Client, msg: Message):
    """
    Usage:
      /index                    — index FILE_CHANNEL from message 1
      /index skip 20000         — skip first 20000 messages
      /index -1001234567890     — index a specific channel from message 1
      /index -1001234567890 skip 50000  — index specific channel, skip 50k
      /index stop               — stop ongoing index
    """
    args = msg.command[1:]  # words after /index

    # Stop ongoing index
    if args and args[0].lower() == 'stop':
        task = _index_tasks.get(msg.from_user.id)
        if task and not task.done():
            task.cancel()
            await msg.reply_text("🛑 **Indexing stopped.**")
        else:
            await msg.reply_text("ℹ️ No active indexing to stop.")
        return

    # Parse channel and skip
    channel_id = FILE_CHANNEL
    skip       = 0

    i = 0
    while i < len(args):
        a = args[i]
        if a.lstrip('-').isdigit() and len(a) > 5:
            channel_id = int(a)
        elif a.lower() == 'skip' and i + 1 < len(args):
            try:
                skip = int(args[i + 1])
                i += 1
            except ValueError:
                await msg.reply_text("❌ Invalid skip value. Use: `/index skip 20000`")
                return
        i += 1

    if not channel_id:
        await msg.reply_text(
            "❌ No FILE_CHANNEL set.\nUse: `/index -1001234567890` or set FILE_CHANNEL env var."
        )
        return

    # Start indexing as background task
    status_msg = await msg.reply_text(
        f"⏳ **Starting index...**\n"
        f"📡 Channel: `{channel_id}`\n"
        f"⏭️ Skip: `{skip}` messages"
    )

    task = asyncio.create_task(
        _do_index(bot, msg.from_user.id, channel_id, skip, status_msg)
    )
    _index_tasks[msg.from_user.id] = task


async def _do_index(bot: Client, admin_id: int, channel_id: int, skip: int, status_msg: Message):
    """Core indexing loop — iterates channel history and saves files to DB."""
    saved     = 0
    duplicates = 0
    errors    = 0
    processed = 0
    UPDATE_EVERY = 500  # update progress message every N files

    try:
        async for message in bot.get_chat_history(channel_id):
            # Skip first N messages as requested
            if skip > 0:
                skip -= 1
                continue

            media, media_type = get_media(message)
            if not media:
                continue

            processed += 1
            file_obj = build_file_obj(message, media, media_type)
            success, reason = await save_file(file_obj)

            if success:
                saved += 1
            elif reason == 'duplicate':
                duplicates += 1
            else:
                errors += 1

            # Update progress every UPDATE_EVERY files
            if processed % UPDATE_EVERY == 0:
                try:
                    await status_msg.edit_text(
                        f"⏳ **Indexing in progress...**\n\n"
                        f"✅ Saved: `{saved}`\n"
                        f"⏭️ Duplicates skipped: `{duplicates}`\n"
                        f"❌ Errors: `{errors}`\n"
                        f"📊 Processed: `{processed}`\n\n"
                        f"Send `/index stop` to cancel."
                    )
                except Exception:
                    pass

            await asyncio.sleep(0)  # yield to event loop

    except asyncio.CancelledError:
        await status_msg.edit_text(
            f"🛑 **Indexing cancelled.**\n\n"
            f"✅ Saved: `{saved}`\n"
            f"⏭️ Duplicates: `{duplicates}`\n"
            f"📊 Processed: `{processed}`"
        )
        return
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except (ChannelInvalid, ChatAdminRequired):
        await status_msg.edit_text(
            "❌ **Cannot access channel.**\n"
            "Make sure the bot is an admin in the channel."
        )
        return
    except Exception as e:
        logger.exception(f"Index error: {e}")
        await status_msg.edit_text(f"❌ **Indexing failed:** `{e}`")
        return

    await status_msg.edit_text(
        f"✅ **Indexing complete!**\n\n"
        f"✅ Saved: `{saved}`\n"
        f"⏭️ Duplicates skipped: `{duplicates}`\n"
        f"❌ Errors: `{errors}`\n"
        f"📊 Total processed: `{processed}`"
    )


# ── Auto-index: files posted IN FILE_CHANNEL ──────────────────
@Client.on_message(filters.channel)
async def auto_index_channel(bot: Client, msg: Message):
    """Auto-index any file posted to FILE_CHANNEL."""
    if msg.chat.id != FILE_CHANNEL:
        return

    media, media_type = get_media(msg)
    if not media:
        return

    file_obj = build_file_obj(msg, media, media_type)
    success, reason = await save_file(file_obj)

    if success:
        logger.info(f"Auto-indexed: {file_obj.file_name}")
    elif reason == 'duplicate':
        logger.debug(f"Auto-index duplicate skipped: {file_obj.file_name}")


# ── Auto-index: admin forwards file to bot PM ─────────────────
@Client.on_message(filters.private & filters.user(ADMINS) & filters.media)
async def auto_index_pm(bot: Client, msg: Message):
    """Auto-index when admin sends/forwards a file directly to bot PM."""
    media, media_type = get_media(msg)
    if not media:
        return

    # Override chat_id to FILE_CHANNEL if forwarded from there, else use PM
    chat_id = FILE_CHANNEL or msg.chat.id
    if msg.forward_from_chat and msg.forward_from_chat.id == FILE_CHANNEL:
        chat_id    = FILE_CHANNEL
        message_id = msg.forward_from_message_id
    else:
        chat_id    = msg.chat.id
        message_id = msg.id

    class FileObj:
        pass
    f = FileObj()
    f.file_id        = media.file_id
    f.file_unique_id = media.file_unique_id
    f.file_name      = getattr(media, 'file_name', None) or msg.caption or f'file_{msg.id}'
    f.file_size      = getattr(media, 'file_size', 0) or 0
    f.mime_type      = getattr(media, 'mime_type', '') or ''
    f.caption        = msg.caption or ''
    f.message_id     = message_id
    f.chat_id        = chat_id
    f.media_type     = media_type

    success, reason = await save_file(f)

    if success:
        await msg.reply_text(f"✅ **Indexed:** `{f.file_name}`")
    elif reason == 'duplicate':
        await msg.reply_text(f"⏭️ **Already indexed:** `{f.file_name}`")
    else:
        await msg.reply_text("❌ Failed to index file.")
