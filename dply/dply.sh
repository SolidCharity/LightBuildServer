#!/bin/bash
# this runs on Fedora 25

dbpwd="test"
Fedora=25
dnf install -y 'dnf-command(config-manager)'
dnf config-manager --add-repo https://download.solidcharity.com/repos/tpokorra/lbs/fedora/$Fedora/lbs-tpokorra-lbs.repo

dnf install -y lightbuildserver lxc-scripts docker-scripts
# somewhere permissive mode is set in /etc/selinux/config while installing these packages
# set selinux permissive mode for nginx to work with uwsgi, without reboot
setenforce 0
systemctl start libvirtd
systemctl enable libvirtd
/usr/share/lightbuildserver/init.sh

touch /root/.ssh/id_rsa
cd /usr/share/lxc-scripts && ./initLXC.sh; cd -

cd /root
cat > initDB.sql <<FINISH
CREATE DATABASE lbs  DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_general_ci;
GRANT ALL ON lbs.* TO lbs@localhost IDENTIFIED BY '$dbpwd';
FINISH

mysql < initDB.sql

# configure lighttpd
ipaddress=`ifconfig eth0 | awk '/inet / {gsub("addr:", "", $2); print $2}'`
sed -i "s/localhost/$ipaddress/g" /etc/nginx/conf.d/lightbuildserver.conf
systemctl restart nginx

sed -i "s/#Mysql/Mysql/g; s/SqliteFile/#SqliteFile/g" /etc/lightbuildserver/config.yml
sed -i "s/MysqlPassword: \"secret/MysqlPassword: \"$dbpwd/g" /etc/lightbuildserver/config.yml
sed -i "s#http://lbs.example.org#http://$ipaddress#g" /etc/lightbuildserver/config.yml
systemctl restart uwsgi

# next step: visit http://your.ip, login with user: demo, password: demo
# adjust settings:
#  vi /etc/lightbuildserver/config.yml
#  # for the changes to take effect, run:
# systemctl restart uwsgi
