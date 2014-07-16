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

import sys
import os
import time
import socket
from Logger import Logger
from Shell import Shell

class RemoteContainer:
  def __init__(self, containername, logger):
    self.name = containername
    self.logger = logger
    self.shell = Shell(logger)
    # we are reusing the slots, for caches etc
    self.slot = containername
    self.distro = ""
    self.release = ""
    self.arch = ""
    self.staticIP = ""
    self.LBSHOME_PATH = "/var/lib/lbs/"
    self.LXCHOME_PATH = "/var/lib/lxc/"

  def executeOnLxcHost(self, command):
    if self.shell.executeshell('ssh -f -o "StrictHostKeyChecking no" -i ' + self.LBSHOME_PATH + "ssh/container_rsa " + self.name + " \"export LANG=C; " + command + " 2>&1; echo \$?\""):
      return self.logger.getLastLine() == "0"
    return False

  def createmachine(self, lxcdistro, lxcrelease, lxcarch, staticIP):
    # create lxc container with specified OS
    self.distro = lxcdistro
    self.release = lxcrelease
    self.arch = lxcarch
    self.staticIP = staticIP
    if self.executeOnLxcHost("if [ -d /var/lib/lxc/" + self.name + " ]; then lxc-destroy --name " + self.name + "; fi") == False:
      return False
    result = False
    if lxcdistro == "centos":
      result = self.executeOnLxcHost("./scripts/initCentOS.sh " + self.name + " 10 " + lxcrelease + " " + lxcarch + " 0")
    if lxcdistro == "fedora":
      if lxcrelease == "rawhide":
        # rawhide is an upgrade from the latest fedora release. see BuildHelperFedora.PrepareMachineAfterStart
        lxcrelease = "20"
      result = self.executeOnLxcHost("./scripts/initFedora.sh " + self.name + " 10 " + lxcrelease + " " + lxcarch + " 0")
    if lxcdistro == "debian":
      result = self.executeOnLxcHost("./scripts/initDebian.sh " + self.name + " 10 " + lxcrelease + " " + lxcarch + " 0")
    if lxcdistro == "ubuntu":
      result = self.executeOnLxcHost("./scripts/initUbuntu.sh " + self.name + " 10 " + lxcrelease + " " + lxcarch + " 0")
    if result == True:
      result = self.executeOnLxcHost("./scripts/tunnelport.sh " + self.name + " 10 22")
    sshpath="/var/lib/lxc/" + self.name + "/rootfs/root/.ssh/"
    if result == True:
      result = self.executeOnLxcHost("mkdir -p " + sshpath)
    if result == True:
     result = self.shell.executeshell('echo "put /var/lib/lbs/ssh/container_rsa.pub authorized_keys" | sftp -o "StrictHostKeyChecking no" -i /var/lib/lbs/ssh/container_rsa ' + self.name + ':' + sshpath)
    if result == True:
      result = self.executeOnLxcHost("chmod 700 " + sshpath + " && chmod 600 " + sshpath + "authorized_keys")
    return result

  def startmachine(self):
    if self.executeOnLxcHost("lxc-start -d -n " + self.name):
      self.shell.executeshell('ssh-keygen -f "/root/.ssh/known_hosts" -R [' + self.name + ']:2010')
      # also remove the ip address
      self.shell.executeshell('ssh-keygen -f "/root/.ssh/known_hosts" -R [' + socket.gethostbyname(self.name) + ']:2010')
      # wait until ssh server is running
      result = self.executeInContainer('echo "container is running"')
      return result
    return False

  def executeInContainer(self, command):
    """Execute a command in a container via SSH"""
    print (" * Executing '%s' in %s..." % (command,
                                             self.name))
    # wait until ssh server is running
    for x in range(0, 19):
      result = self.shell.executeshell('ssh -f -o "StrictHostKeyChecking no" -o Port=2010 -i ' + self.LBSHOME_PATH + "ssh/container_rsa " + self.name + " \"export LANG=C; " + command + " 2>&1; echo \$?\"")
      if result:
        return self.logger.getLastLine() == "0"
      # sleep for half a second
      time.sleep(0.5)
    return False

  def destroy(self):
    return self.executeOnLxcHost("lxc-destroy --name " + self.name)

  def stop(self):
    return self.executeOnLxcHost("lxc-stop --name " + self.name)

  def copytree(self, src, dest):
    return self.rsyncHostPut(src, "/var/lib/lxc/" + self.name + "/rootfs" + dest)

  def rsyncContainerGet(self, path, dest = None):
    if dest == None:
      dest = path[:path.rindex("/")]
    result = self.shell.executeshell('rsync -avz -e "ssh -i ' + self.LBSHOME_PATH + "ssh/container_rsa " + '" root@' + self.name + ':/var/lib/lxc/' + self.name + '/rootfs' + path + ' ' + dest)
    return result

  def rsyncHostPut(self, src, dest = None):
    if dest == None:
      dest = src
    dest = dest[:dest.rindex("/")]
    result = self.shell.executeshell('rsync -avz -e "ssh -i ' + self.LBSHOME_PATH + "ssh/container_rsa " + '" ' + src + ' root@' + self.name + ':' + dest)
    return result 

  def rsyncHostGet(self, path, dest = None):
    if dest == None:
      dest = path[:path.rindex("/")]
    result = self.shell.executeshell('rsync -avz -e "ssh -i ' + self.LBSHOME_PATH + "ssh/container_rsa " + '" root@' + self.name + ':' + path + ' ' + dest)
    return result

  def installmount(self, localpath, hostpath = None):
    if hostpath is None:
      hostpath = self.LBSHOME_PATH + self.slot + "/" + self.distro + "/" + self.release + "/" + self.arch + localpath
    result = self.executeOnLxcHost("./scripts/initMount.sh " + hostpath + " " + self.name + " " + localpath)
    if result:
      if not os.path.exists(hostpath):
          self.shell.executeshell("mkdir -p " + hostpath)
      #rsync the contents
      return self.rsyncHostPut(hostpath)
    return False
