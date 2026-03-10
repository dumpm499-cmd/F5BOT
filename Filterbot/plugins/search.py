import math
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated
from database import search_files
from plugins.fsub import check_fsub, fsub_markup
from config import MAX_RESULTS, MAX_BTN_ROW
import asyncio
import logging

logger = logging.getLogger(__name__)


def build_keyboard(results: list, query: str, page: int, total: int) -> InlineKeyboardMarkup:
    """Build paginated inline keyboard from search results."""
    buttons = []
    row = []

    for i, file in enumerate(results):
        name = file.get('file_name') or file.get('caption') or 'Unknown File'
        # Trim long names for button label
        label = name[:60] + '…' if len(name) > 60 else name
        # callback: f|<message_id>|<chat_id>
        cb_data = f"f|{file['message_id']}|{file['chat_id']}"
        row.append(InlineKeyboardButton(f"🎬 {label}", callback_data=cb_data))
        if len(row) == MAX_BTN_ROW:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Pagination row
    total_pages = max(1, math.ceil(total / MAX_RESULTS))
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"page|{query}|{page - 1}"))
    nav.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"page|{query}|{page + 1}"))
    if nav:
        buttons.append(nav)

    # Send All button if multiple results
    if total > 1:
        buttons.append([
            InlineKeyboardButton(
                f"📤 Send All ({min(total, 50)})",
                callback_data=f"sendall|{query}|1"
            )
        ])

    return InlineKeyboardMarkup(buttons)


@Client.on_message(filters.private & filters.text & ~filters.command(['start', 'help', 'index', 'stats', 'broadcast', 'deleteall']))
async def search_handler(bot: Client, msg: Message):
    """Handle any text message as a file search query."""
    # Force subscribe check
    if not await check_fsub(bot, msg.from_user.id):
        markup = await fsub_markup(bot)
        await msg.reply_text("⚠️ **Join our channel first!**", reply_markup=markup)
        return

    query = msg.text.strip()
    if len(query) < 2:
        await msg.reply_text("🔍 Please send at least 2 characters to search.")
        return

    results, total = await search_files(query, offset=0, limit=MAX_RESULTS)

    if not results:
        await msg.reply_text(
            f"❌ **No results found for:** `{query}`\n\n"
            "Try different keywords or check the spelling."
        )
        return

    keyboard = build_keyboard(results, query, page=1, total=total)
    total_pages = max(1, math.ceil(total / MAX_RESULTS))

    await msg.reply_text(
        f"🔍 **Search:** `{query}`\n"
        f"📁 **Found:** {total} file(s) — Page 1/{total_pages}",
        reply_markup=keyboard
    )


@Client.on_callback_query(filters.regex(r'^page\|'))
async def page_handler(bot: Client, cb: CallbackQuery):
    """Handle pagination button presses."""
    _, query, page_str = cb.data.split('|', 2)
    page   = int(page_str)
    offset = (page - 1) * MAX_RESULTS

    results, total = await search_files(query, offset=offset, limit=MAX_RESULTS)
    if not results:
        await cb.answer("No more results.", show_alert=True)
        return

    keyboard     = build_keyboard(results, query, page=page, total=total)
    total_pages  = max(1, math.ceil(total / MAX_RESULTS))

    await cb.message.edit_text(
        f"🔍 **Search:** `{query}`\n"
        f"📁 **Found:** {total} file(s) — Page {page}/{total_pages}",
        reply_markup=keyboard
    )
    await cb.answer()


@Client.on_callback_query(filters.regex(r'^f\|'))
async def send_file(bot: Client, cb: CallbackQuery):
    """Forward a single file to the user WITHOUT forward tag using copy_message."""
    _, msg_id_str, chat_id_str = cb.data.split('|')
    msg_id  = int(msg_id_str)
    chat_id = int(chat_id_str)

    await cb.answer("📤 Sending file...", show_alert=False)
    try:
        await bot.copy_message(
            chat_id    = cb.from_user.id,
            from_chat_id = chat_id,
            message_id = msg_id
        )
    except FloodWait as e:
        await asyncio.sleep(e.value)
        await bot.copy_message(
            chat_id      = cb.from_user.id,
            from_chat_id = chat_id,
            message_id   = msg_id
        )
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await cb.answer("❌ Failed to send file. It may have been deleted.", show_alert=True)


@Client.on_callback_query(filters.regex(r'^sendall\|'))
async def send_all(bot: Client, cb: CallbackQuery):
    """Send up to 50 files from search results to the user."""
    _, query, _ = cb.data.split('|', 2)
    await cb.answer("📤 Sending all files, please wait...", show_alert=True)

    results, total = await search_files(query, offset=0, limit=50)
    sent = 0
    for file in results:
        try:
            await bot.copy_message(
                chat_id      = cb.from_user.id,
                from_chat_id = file['chat_id'],
                message_id   = file['message_id']
            )
            sent += 1
            await asyncio.sleep(0.3)  # avoid flood
        except FloodWait as e:
            await asyncio.sleep(e.value)
        except (UserIsBlocked, InputUserDeactivated):
            break
        except Exception as e:
            logger.error(f"Send all error: {e}")

    try:
        await cb.message.reply_text(f"✅ Sent **{sent}** file(s) successfully!")
    except Exception:
        pass


@Client.on_callback_query(filters.regex('^noop$'))
async def noop(bot: Client, cb: CallbackQuery):
    await cb.answer()
