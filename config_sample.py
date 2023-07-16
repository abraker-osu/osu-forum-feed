from os import path
import pathlib


# Runtime Settings and paths
runtime_mode = [ 'db' ]     # Add 'db' in list for warn, info, and debug printouts
runtime_quit = False        # Don't change

root          = path.abspath(path.dirname(__file__))
log_path      = pathlib.Path(root + '/logs')
bots_log_path = pathlib.Path(root + '/logs/bots')
bots_path     = pathlib.Path(root + '/bots')

# Forum monitor bootstrap settings
# This is only used as starting values if it doesn't exist in DB
latest_post_id = int()

# Forum monitor rate settings
rate_post_max   = int()  # Maximum number of seconds to wait between fetching posts when encountering osu! rate limitting
rate_post_warn  = int()  # Warn when rate between fetching posts is higher than this
rate_post_min   = int()  # Minimum number of seconds to wait between fetching posts
rate_fetch_fail = int()  # Seconds to wait after encountering a connection error when fetching posts

# Port for discord bot relaying forum feed
discord_bot_port = int()

# Discord id of admin
discord_admin_user_id = int()

# Port on which the forum bot API will listen on
api_port = int()

# Username and password for osu!web
# NOTE: When logging in, osu! sends a verification to the email address associated with the account.
#   This must be acknowledged manually upon bot initialization
# TODO: Is there a way to avoid putting this in plaintext here?
web_username = ''
web_password = ''
