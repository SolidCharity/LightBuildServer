#!/bin/bash

# these lines will install the current source on top of a installed package

alias cp=cp
src=/root/LightBuildServer
prod=/usr/share/lightbuildserver

if [ ! -d $prod ]
then
  echo "please first install the lightbuildserver rpm: dnf install lightbuildserver"
  exit 1
fi

cp -fR $src/web/* $prod/web
cp -fR $src/lib/* $prod/lib
systemctl restart lbs
