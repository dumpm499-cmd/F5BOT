import re
from os import environ

id_pattern = re.compile(r'^-?\d+$')

def to_int_list(env_key):
    raw = environ.get(env_key, '')
    return [int(x) for x in raw.split() if id_pattern.search(x)]

def to_int(env_key, default=None):
    val = environ.get(env_key, '')
    return int(val) if val and id_pattern.search(val) else default

# ── Bot Credentials ────────────────────────────────────────────
SESSION      = environ.get('SESSION', 'FilterBot')
API_ID       = int(environ.get('API_ID', '0'))
API_HASH     = environ.get('API_HASH', '')
BOT_TOKEN    = environ.get('BOT_TOKEN', '')

# ── Admins ─────────────────────────────────────────────────────
ADMINS       = to_int_list('ADMINS')

# ── Channels ───────────────────────────────────────────────────
# FILE_CHANNEL: where files are stored — bot must be admin here
FILE_CHANNEL  = to_int('FILE_CHANNEL')

# LOG_CHANNEL: bot logs activity here
LOG_CHANNEL   = to_int('LOG_CHANNEL')

# AUTH_CHANNEL: force subscribe channel (leave blank to disable)
_auth         = environ.get('AUTH_CHANNEL', '')
AUTH_CHANNEL  = int(_auth) if _auth and id_pattern.search(_auth) else None

# ── Database ───────────────────────────────────────────────────
DATABASE_URI  = environ.get('DATABASE_URI', '')
DATABASE_NAME = environ.get('DATABASE_NAME', 'filterbot')

# ── Search Settings ────────────────────────────────────────────
MAX_RESULTS   = int(environ.get('MAX_RESULTS', '10'))   # results per page
MAX_BTN_ROW   = int(environ.get('MAX_BTN_ROW', '2'))    # buttons per row

# ── Web Server (needed for Choreo health check) ────────────────
PORT          = int(environ.get('PORT', '8000'))
ON_HEROKU     = bool(environ.get('ON_HEROKU', False))
URL           = environ.get('URL', '')
PING_INTERVAL = int(environ.get('PING_INTERVAL', '240'))
