import asyncio
import logging
import glob
import importlib
import sys
from pathlib import Path

from pyrogram import Client, idle
from aiohttp import web

from config import API_ID, API_HASH, BOT_TOKEN, SESSION, PORT, LOG_CHANNEL
from database import ensure_indexes
from plugins import web_server

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger('pyrogram').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ── Bot Client ─────────────────────────────────────────────────
bot = Client(
    SESSION,
    api_id    = API_ID,
    api_hash  = API_HASH,
    bot_token = BOT_TOKEN,
)


async def load_plugins():
    """Dynamically load all plugin files from plugins/ folder."""
    plugin_files = sorted(glob.glob('plugins/*.py'))
    for path in plugin_files:
        name = Path(path).stem
        if name == '__init__':
            continue
        module_path = f'plugins.{name}'
        spec   = importlib.util.spec_from_file_location(module_path, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[module_path] = module
        logger.info(f'Loaded plugin: {name}')


async def main():
    await bot.start()

    me = await bot.get_me()
    logger.info(f'Bot started: @{me.username}')

    # Ensure MongoDB indexes exist
    await ensure_indexes()
    logger.info('Database indexes ready.')

    # Load all plugins
    await load_plugins()

    # Notify log channel
    if LOG_CHANNEL:
        try:
            await bot.send_message(LOG_CHANNEL, f'✅ **Bot started:** @{me.username}')
        except Exception:
            logger.warning('Could not send message to LOG_CHANNEL. Make bot admin there.')

    # Start aiohttp web server (Choreo needs an active HTTP endpoint)
    runner = web.AppRunner(await web_server())
    await runner.setup()
    await web.TCPSite(runner, '0.0.0.0', PORT).start()
    logger.info(f'Web server running on port {PORT}')

    logger.info('Bot is running...')
    await idle()

    await bot.stop()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Bot stopped.')
