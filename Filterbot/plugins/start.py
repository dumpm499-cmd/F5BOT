from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import add_user, total_users, total_files
from plugins.fsub import check_fsub, fsub_markup
from config import ADMINS

START_TEXT = """
👋 **Hello {name}!**

I'm a **File Search Bot** — send me any movie, series, or file name and I'll find it for you instantly.

🔍 **How to use:**
Just type the name of what you're looking for!

📂 **Example:** `Avengers Endgame`
"""

HELP_TEXT = """
📖 **Help & Commands**

**For Users:**
› Just send any text to search for files
› Use page buttons to browse results
› Click a file name to receive it

**For Admins:**
› `/index <channel_id> <skip>` — bulk index from a channel
› `/index skip 20000` — skip first 20k messages
› `/stats` — bot statistics
› `/broadcast` — message all users
› `/deleteall` — wipe all indexed files
"""


@Client.on_message(filters.command('start') & filters.private)
async def start(bot: Client, msg: Message):
    await add_user(msg.from_user.id, msg.from_user.first_name, msg.from_user.username)

    # Force subscribe check
    if not await check_fsub(bot, msg.from_user.id):
        markup = await fsub_markup(bot)
        await msg.reply_text(
            "⚠️ **You must join our channel to use this bot!**",
            reply_markup=markup
        )
        return

    await msg.reply_text(
        START_TEXT.format(name=msg.from_user.mention),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📖 Help", callback_data="help"),
            InlineKeyboardButton("📊 Stats", callback_data="stats"),
        ]])
    )


@Client.on_callback_query(filters.regex('^help$'))
async def help_cb(bot: Client, cb: CallbackQuery):
    await cb.message.edit_text(
        HELP_TEXT,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Back", callback_data="start")
        ]])
    )


@Client.on_callback_query(filters.regex('^stats$'))
async def stats_cb(bot: Client, cb: CallbackQuery):
    users = await total_users()
    files = await total_files()
    await cb.message.edit_text(
        f"📊 **Bot Stats**\n\n👤 Users: `{users}`\n📁 Files: `{files}`",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🏠 Back", callback_data="start")
        ]])
    )


@Client.on_callback_query(filters.regex('^start$'))
async def start_cb(bot: Client, cb: CallbackQuery):
    await cb.message.edit_text(
        START_TEXT.format(name=cb.from_user.mention),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📖 Help", callback_data="help"),
            InlineKeyboardButton("📊 Stats", callback_data="stats"),
        ]])
    )


@Client.on_callback_query(filters.regex('^check_fsub$'))
async def check_fsub_cb(bot: Client, cb: CallbackQuery):
    if await check_fsub(bot, cb.from_user.id):
        await cb.message.edit_text(
            START_TEXT.format(name=cb.from_user.mention),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📖 Help", callback_data="help"),
                InlineKeyboardButton("📊 Stats", callback_data="stats"),
            ]])
        )
    else:
        await cb.answer("❌ You haven't joined yet!", show_alert=True)
