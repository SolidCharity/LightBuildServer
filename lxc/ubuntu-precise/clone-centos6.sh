#!/bin/bash
name=70-centos6-lbs
lxc-clone -o centos6-master -n $name
sed -i "s/centos6-master/$name/g" /var/lib/lxc/$name/config
