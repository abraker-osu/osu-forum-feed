$(dirname ${0%})/build.sh

# Stuff is copied to a seperate prod location so
# that edits can be made in this dev location
#
# NOTE: To be run as root
# NOTE: Assumed a `server` user and group exists
systemctl stop forumbot.service
mv /home/server/prod/osu-forum-feed/config.yaml /home/server/tmp/config.yaml
mv /home/server/prod/osu-forum-feed/db.json /home/server/tmp/db.json
rm -rf /home/server/prod/osu-forum-feed
rsync -av --progress . /home/server/prod/osu-forum-feed --exclude config.yaml
chown -R server:server /home/server/prod/osu-forum-feed
mv /home/server/tmp/config.yaml /home/server/prod/osu-forum-feed/config.yaml
mv /home/server/tmp/db.json /home/server/prod/osu-forum-feed/db.json
systemctl start forumbot.service
