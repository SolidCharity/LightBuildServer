#!/usr/bin/env python3
"""Wrapper for LXC Container Management"""

# Copyright (c) 2014-2015 Timotheus Pokorra

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
from RemoteContainer import RemoteContainer
from Logger import Logger
from Shell import Shell

class LXCContainer(RemoteContainer):
  def __init__(self, containername, configBuildMachine, logger):
    RemoteContainer.__init__(self, containername, configBuildMachine, logger)
    self.LXCHOME_PATH = "/var/lib/lxc/"
    self.SCRIPTS_PATH = "/usr/share/lxc-scripts/"

  def executeOnHost(self, command):
    return RemoteContainer.executeOnHost(self, command)

  def createmachine(self, distro, release, arch, staticIP):
    # create lxc container with specified OS
    self.distro = distro
    self.release = release
    self.arch = arch
    self.staticIP = staticIP
    if self.executeOnHost("if [ -d /var/lib/lxc/" + self.name + " ]; then lxc-destroy --name " + self.name + "; fi") == False:
      return False
    result = False
    if distro == "centos":
      result = self.executeOnHost(self.SCRIPTS_PATH + "initCentOS.sh " + self.name + " " + str(self.cid) + " " + release + " " + arch + " 0")
    if distro == "fedora":
      result = self.executeOnHost(self.SCRIPTS_PATH + "initFedora.sh " + self.name + " " + str(self.cid) + " " + release + " " + arch + " 0")
    if distro == "debian":
      result = self.executeOnHost(self.SCRIPTS_PATH + "initDebian.sh " + self.name + " " + str(self.cid) + " " + release + " " + arch + " 0")
    if distro == "ubuntu":
      result = self.executeOnHost(self.SCRIPTS_PATH + "initUbuntu.sh " + self.name + " " + str(self.cid) + " " + release + " " + arch + " 0")
    if result == True:
      result = self.executeOnHost(self.SCRIPTS_PATH + "tunnelport.sh " + str(self.cid) + " 22")
    sshpath="/var/lib/lxc/" + self.name + "/rootfs/root/.ssh/"
    if result == True:
      result = self.executeOnHost("mkdir -p " + sshpath)
    if result == True:
     result = self.shell.executeshell('echo "put /var/lib/lbs/ssh/container_rsa.pub authorized_keys2" | sftp -o "StrictHostKeyChecking no" -oPort=' + self.port + ' -i /var/lib/lbs/ssh/container_rsa ' + self.name + ':' + sshpath)
    if result == True:
      result = self.executeOnHost("cd " + sshpath + " && cat authorized_keys2 >> authorized_keys && rm authorized_keys2")
    if result == True:
      result = self.executeOnHost("chmod 700 " + sshpath + " && chmod 600 " + sshpath + "authorized_keys")
    return result

  def startmachine(self):
    if self.executeOnHost("lxc-start -d -n " + self.name):
      # remove the ip address
      if self.containerPort == "22":
        self.shell.executeshell('ssh-keygen -f "/root/.ssh/known_hosts" -R ' + self.containerIP)
      else:
        self.shell.executeshell('ssh-keygen -f "/root/.ssh/known_hosts" -R [' + self.containerIP + ']:' + self.containerPort)
      # wait until ssh server is running
      result = self.executeInContainer('echo "container is running"')
      return result
    return False

  def executeInContainer(self, command):
    """Execute a command in a container via SSH"""
    print (" * Executing '%s' in %s..." % (command,
                                             self.name))
    # wait until ssh server is running
    for x in range(0, 24):
      result = self.shell.executeshell('ssh -f -o "StrictHostKeyChecking no" -o Port=' + self.containerPort + ' -i ' + self.LBSHOME_PATH + "ssh/container_rsa " + self.containerIP + " \"export LANG=C; " + command + " 2>&1 && echo \$?\"")
      if result:
        return self.logger.getLastLine() == "0"
      if x < 5:
        # sleep for half a second
        time.sleep(0.5)
      else:
        # sleep for 10 seconds
        time.sleep(10)
    return False

  def destroy(self):
    return self.executeOnHost("lxc-destroy --name " + self.name)

  def stop(self):
    return self.executeOnHost("lxc-stop --name " + self.name)

  def rsyncContainerPut(self, src, dest):
    return self.rsyncHostPut(src, "/var/lib/lxc/" + self.name + "/rootfs" + dest)

  def rsyncContainerGet(self, path, dest = None):
    if dest == None:
      dest = path[:path.rindex("/")]
    result = self.shell.executeshell('rsync -avz -e "ssh -i ' + self.LBSHOME_PATH + "ssh/container_rsa -p " + self.port + '" root@' + self.name + ':/var/lib/lxc/' + self.name + '/rootfs' + path + ' ' + dest)
    return result

  def rsyncHostPut(self, src, dest = None):
    if dest == None:
      dest = src
    dest = dest[:dest.rindex("/")]
    result = self.shell.executeshell('rsync -avz --delete -e "ssh -i ' + self.LBSHOME_PATH + "ssh/container_rsa -p " + self.port + '" ' + src + ' root@' + self.name + ':' + dest)
    return result 

  def rsyncHostGet(self, path, dest = None):
    if dest == None:
      dest = path[:path.rindex("/")]
    result = self.shell.executeshell('rsync -avz --delete -e "ssh -i ' + self.LBSHOME_PATH + "ssh/container_rsa -p " + self.port + '" root@' + self.name + ':' + path + ' ' + dest)
    return result

  def installmount(self, localpath, hostpath = None):
    if hostpath is None:
      hostpath = self.LBSHOME_PATH + self.slot + "/" + self.distro + "/" + self.release + "/" + self.arch + localpath
    result = self.executeOnHost(self.SCRIPTS_PATH + "initMount.sh " + hostpath + " " + self.name + " " + localpath)
    if result:
      if not os.path.exists(hostpath):
          self.shell.executeshell("mkdir -p " + hostpath)
      #rsync the contents
      return self.rsyncHostPut(hostpath)
    return False
