#!/bin/bash

if [ -z $2 ]
then
  echo "please call $0 <name of new container> <cid>"
  echo "   eg. $0 50-centos6-mymachine 50"
  exit 1
fi
name=$1
cid=$2

lxc-clone -o centos6-master -n $name
sed -i "s/centos6-master/$name/g" /var/lib/lxc/$name/config
./tunnelssh.sh $name $cid
