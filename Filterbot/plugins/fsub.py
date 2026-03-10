from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, ChannelInvalid
from config import AUTH_CHANNEL


async def check_fsub(bot: Client, user_id: int) -> bool:
    """Returns True if user is subscribed or AUTH_CHANNEL is not set."""
    if not AUTH_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(AUTH_CHANNEL, user_id)
        return member.status.name not in ('LEFT', 'BANNED', 'KICKED')
    except UserNotParticipant:
        return False
    except (ChatAdminRequired, ChannelInvalid):
        return True  # misconfigured, don't block users
    except Exception:
        return True


async def fsub_markup(bot: Client) -> InlineKeyboardMarkup | None:
    """Returns the join button markup, or None if fsub not configured."""
    if not AUTH_CHANNEL:
        return None
    try:
        invite = await bot.export_chat_invite_link(AUTH_CHANNEL)
        chat   = await bot.get_chat(AUTH_CHANNEL)
        return InlineKeyboardMarkup([[
            InlineKeyboardButton(f"📢 Join {chat.title}", url=invite)
        ], [
            InlineKeyboardButton("🔄 Try Again", callback_data="check_fsub")
        ]])
    except Exception:
        return None
