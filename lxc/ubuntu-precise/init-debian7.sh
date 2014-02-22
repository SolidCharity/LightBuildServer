#!/bin/bash

# this will do the initial installation of the lxc template etc

cp -f templates/lxc-debian* /usr/lib/lxc/templates/

# This will create a master lxc template, that will be cloned for new machines
lxc-create -t debian-wheezy -n debian7-master
