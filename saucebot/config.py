# Load our configuration
from configparser import ConfigParser

config = ConfigParser()
config.read(['config.default.ini', 'config.ini'])
