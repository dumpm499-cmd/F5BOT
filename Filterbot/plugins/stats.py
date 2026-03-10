from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database import total_users, total_files, delete_all_files
from config import ADMINS


@Client.on_message(filters.command('stats') & filters.private & filters.user(ADMINS))
async def stats(bot: Client, msg: Message):
    users = await total_users()
    files = await total_files()
    me    = await bot.get_me()
    await msg.reply_text(
        f"📊 **Bot Statistics**\n\n"
        f"🤖 Bot: @{me.username}\n"
        f"👤 Total Users: `{users}`\n"
        f"📁 Total Files: `{files}`"
    )


@Client.on_message(filters.command('deleteall') & filters.private & filters.user(ADMINS))
async def deleteall_cmd(bot: Client, msg: Message):
    await msg.reply_text(
        "⚠️ **Are you sure?**\n\nThis will delete ALL indexed files from the database.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Yes, delete all", callback_data="confirm_deleteall"),
            InlineKeyboardButton("❌ Cancel",          callback_data="cancel_deleteall"),
        ]])
    )


@Client.on_callback_query(filters.regex('^confirm_deleteall$') & filters.user(ADMINS))
async def confirm_deleteall(bot: Client, cb: CallbackQuery):
    count = await delete_all_files()
    await cb.message.edit_text(f"🗑️ **Deleted {count} files** from the database.")


@Client.on_callback_query(filters.regex('^cancel_deleteall$') & filters.user(ADMINS))
async def cancel_deleteall(bot: Client, cb: CallbackQuery):
    await cb.message.edit_text("❌ Deletion cancelled.")
