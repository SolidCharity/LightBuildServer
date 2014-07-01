#!/usr/bin/env python3
"""Wrapper for LXC Container Management"""

# Copyright (c) 2014 Timotheus Pokorra

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301
# USA
#

import lxc
import sys
import os
import time
#from paramiko import SSHClient
from subprocess import Popen, PIPE, STDOUT
from Logger import Logger
from LXCContainer import LXCContainer

class RemoteContainer(LXCContainer):
  def executeremote(self, command):
    return self.executeshell('ssh -f -o "StrictHostKeyChecking no" -i ' + self.LBSHOME_PATH + "ssh/container_rsa " + self.name + " \"export LANG=C; " + command + " 2>&1\"")

  def createmachine(self, lxcdistro, lxcrelease, lxcarch, staticIP):
    # create lxc container with specified OS
    self.distro = lxcdistro
    self.release = lxcrelease
    self.arch = lxcarch
    self.staticIP = staticIP
    if self.executeremote("lxc-destroy --name " + self.name) == False:
      return False
    result = False
    if lxcdistro == "centos":
      result = self.executeremote("./scripts/initCentOS.sh " + self.name + " 1 " + lxcrelease + " " + lxcarch)
    if lxcdistro == "fedora":
      result = self.executeremote("./scripts/initFedora.sh " + self.name + " 1 " + lxcrelease + " " + lxcarch)
    if lxcdistro == "debian":
      result = self.executeremote("./scripts/initDebian.sh " + self.name + " 1 " + lxcrelease + " " + lxcarch)
    if lxcdistro == "ubuntu":
      result = self.executeremote("./scripts/initUbuntu.sh " + self.name + " 1 " + lxcrelease + " " + lxcarch)
    if result == True:
      result = self.executeremote("./scripts/tunnelssh.sh " + self.name + " 1 ")
    return result

  def startmachine(self):
    if self.executeremote("lxc-start -d -n " + self.name):
      # wait until ssh server is running
      result = self.execute('echo "container is running"')
      if result == True:
        result = self.executeshell('ssh-keygen -f "/root/.ssh/known_hosts" -R ' + self.name)
        return result
    return False

  def getrootfs(self):
    # we do not have access to the rootfs
    return ""

  def execute(self, command):
    """Execute a command in a container via SSH"""
    print (" * Executing '%s' in %s..." % (command,
                                             self.name))
    # wait until ssh server is running
    for x in range(0, 19):
      result = self.executeshell('ssh -f -o "StrictHostKeyChecking no" -o "Port 2001" -i ' + self.LBSHOME_PATH + "ssh/container_rsa " + self.name + " \"export LANG=C; " + command + " 2>&1\"")
      if result:
        if self.logger.hasLBSERROR():
          return False
        return True
      # sleep for half a second
      time.sleep(0.5)
    return False

  def installmount(self, localpath, hostpath = None):
    # not implemented. need to do something for repo and tarballs
    return False
