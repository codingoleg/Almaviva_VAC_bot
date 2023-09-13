from os import environ

# Any set of symbols for encrypting some database values
key: str = environ['key']
salt: str = environ['salt']

# Both parameters should be 'localhost' for local usage
# or 'redis' for docker usage
redis_host: str = 'localhost'
bot_storage_host: str = 'localhost'

# Telegram parameters
admin_id: str = environ['admin_id']
token: str = environ['token']
