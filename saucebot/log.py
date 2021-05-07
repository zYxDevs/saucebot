# Set up logging
import logging

import sentry_sdk

from saucebot.config import config

logLevel = getattr(logging, str(config.get('Bot', 'log_level', fallback='ERROR')).upper())
logFormat = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", "%Y-%m-%d %H:%M:%S")

log = logging.getLogger('saucebot')
log.setLevel(logLevel)

# logging.basicConfig(level=logging.DEBUG)

query_log = logging.getLogger('pony.orm.sql')
query_log.setLevel(logLevel)

ch = logging.StreamHandler()
ch.setLevel(logLevel)
ch.setFormatter(logFormat)

log.addHandler(ch)
query_log.addHandler(ch)

# Unless you're running your own custom fork of saucebot, you probably don't need this.
if config.has_option('Bot', 'sentry_logging') and config.getboolean('Bot', 'sentry_logging'):
    sentry_sdk.init(config.get('Bot', 'sentry_dsn'), traces_sample_rate=0.25)
