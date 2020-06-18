# Load our configuration
from configparser import ConfigParser

config = ConfigParser()
config.read(['config.default.ini', 'config.ini'])

server_api_limit = config.get('SauceNao', 'server_api_limit', fallback=None)
member_api_limit = config.get('SauceNao', 'member_api_limit', fallback=None)