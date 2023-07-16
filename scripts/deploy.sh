$(dirname ${0%})/build.sh

# Stuff is copied to a seperate prod location so
# that edits can be made in this dev location
#
# To be run as root
systemctl stop forumbot.service
mv /home/server/prod/osu-forum-feed/config.py /home/server/tmp/config.py
mv /home/server/prod/osu-forum-feed/db.json /home/server/tmp/db.json
rm -rf /home/server/prod/osu-forum-feed
rsync -av --progress . /home/server/prod/osu-forum-feed --exclude config.py
chown -R server:server /home/server/prod/osu-forum-feed
mv /home/server/tmp/config.py /home/server/prod/osu-forum-feed/config.py
mv /home/server/tmp/db.json /home/server/prod/osu-forum-feed/db.json
systemctl start forumbot.service
