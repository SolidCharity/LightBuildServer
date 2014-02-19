#!/bin/bash

# this will do the initial installation of the lxc template etc

cp -f templates/centos-* /usr/lib/lxc/templates/

# This will create a master lxc template, that will be cloned for new machines
mkdir -p /usr/local/lbs/shared/centos6/base/packages
apt-get -y install yum
lxc-create -t centos6 -n centos6-master
mv /var/lib/lxc/centos6-master/rootfs/var/cache/yum/base/packages/* /usr/local/lbs/shared/centos6/base/packages
echo "lxc.mount.entry = /usr/local/lbs/shared/centos6/base/packages /var/lib/lxc/centos6-master/rootfs/var/cache/yum/base/packages none defaults,bind 0 0" >> /var/lib/lxc/centos6-master/config
