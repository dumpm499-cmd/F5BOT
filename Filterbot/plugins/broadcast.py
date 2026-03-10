import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from database import get_all_users, delete_user, total_users
from config import ADMINS

logger = logging.getLogger(__name__)

# Track who is waiting to send a broadcast
_waiting_broadcast: set[int] = set()


@Client.on_message(filters.command('broadcast') & filters.private & filters.user(ADMINS))
async def broadcast_cmd(bot: Client, msg: Message):
    """Admin sends /broadcast then replies with the message to send."""
    _waiting_broadcast.add(msg.from_user.id)
    await msg.reply_text(
        "📣 **Broadcast Mode**\n\n"
        "Now send the message you want to broadcast to all users.\n"
        "It can be text, photo, video, or any media.\n\n"
        "Send /cancel to abort."
    )


@Client.on_message(filters.command('cancel') & filters.private & filters.user(ADMINS))
async def cancel_cmd(bot: Client, msg: Message):
    if msg.from_user.id in _waiting_broadcast:
        _waiting_broadcast.discard(msg.from_user.id)
        await msg.reply_text("❌ Broadcast cancelled.")
    else:
        await msg.reply_text("Nothing to cancel.")


@Client.on_message(filters.private & filters.user(ADMINS) & ~filters.command(['broadcast', 'cancel', 'index', 'stats', 'deleteall', 'start']))
async def do_broadcast(bot: Client, msg: Message):
    """Handle the actual broadcast message."""
    if msg.from_user.id not in _waiting_broadcast:
        return
    _waiting_broadcast.discard(msg.from_user.id)

    total  = await total_users()
    status = await msg.reply_text(f"📣 Broadcasting to {total} users...")

    success = 0
    failed  = 0
    blocked = 0

    async for user in await get_all_users():
        try:
            await msg.copy(user['_id'])
            success += 1
            await asyncio.sleep(0.05)
        except FloodWait as e:
            await asyncio.sleep(e.value)
            try:
                await msg.copy(user['_id'])
                success += 1
            except Exception:
                failed += 1
        except UserIsBlocked:
            await delete_user(user['_id'])
            blocked += 1
        except InputUserDeactivated:
            await delete_user(user['_id'])
            blocked += 1
        except Exception as e:
            logger.error(f"Broadcast error for {user['_id']}: {e}")
            failed += 1

    await status.edit_text(
        f"✅ **Broadcast complete!**\n\n"
        f"✅ Sent: `{success}`\n"
        f"❌ Failed: `{failed}`\n"
        f"🚫 Blocked/Deleted: `{blocked}`"
          )
