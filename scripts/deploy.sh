#!/bin/bash
set -e

# $(dirname ${0%})/build.sh

# Stuff is copied to a seperate prod location so
# that edits can be made in this dev location
#
# NOTE: To be run as root
# NOTE: Assumed a `server` user and group exists
systemctl stop forumbot.service

# Move config and db files to a temporary location because they would be overwritten otherwise
mv /home/server/prod/osu-forum-feed/config.yaml /home/server/tmp/config.yaml

# Nuke the folder and copy over the updated files in repo location -> prod location
rm -rf /home/server/prod/osu-forum-feed
rsync -av --progress . /home/server/prod/osu-forum-feed --exclude config.yaml
chown -R server:server /home/server/prod/osu-forum-feed

# Move config and db files back
mkdir -p /home/server/tmp
mv /home/server/tmp/config.yaml /home/server/prod/osu-forum-feed/config.yaml

# Sensitive files should only be accesible by the user these files are for
# config: r--r-----
# db:     rw-rw----
chown root:server /home/server/prod/osu-forum-feed/config.yaml
chmod 440 /home/server/prod/osu-forum-feed/config.yaml
chown -R root:server /var/lib/forum-bot
chmod -R 660 /var/lib/forum-bot

# Logs dir
mkdir -p /var/log/forum-bot
chown -R root:server /var/log/forum-bot

chmod +x /home/server/prod/osu-forum-feed/scripts/run.sh

systemctl start forumbot.service

echo "[ DONE ]"
