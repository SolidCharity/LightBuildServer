#!/usr/bin/env python3
"""Wrapper for LXC Container Management"""

# Copyright (c) 2014-2016 Timotheus Pokorra

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
  def __init__(self, containername, configBuildMachine, logger, packageSrcPath):
    RemoteContainer.__init__(self, containername, configBuildMachine, logger, packageSrcPath, "lxc")
    self.SCRIPTS_PATH = "/usr/share/lxc-scripts/"

  def executeOnHost(self, command):
    return RemoteContainer.executeOnHost(self, command)

  def createmachine(self, distro, release, arch, staticIP):
    # create lxc container with specified OS
    self.distro = distro
    self.release = release
    self.arch = arch
    self.staticIP = staticIP
    if not self.staticMachine:
      if self.executeOnHost("if [ -d /var/lib/lxc/" + self.containername + " ]; then lxc-destroy --name " + self.containername + "; fi") == False:
        return False
    # make sure we can always start the CentOS machines. after an LXC package upgrade, the changes to the templates are lost
    self.executeOnHost(self.SCRIPTS_PATH + "initLXC.sh")
    result = False
    if self.staticMachine:
      result = True
    else:
      if distro == "centos":
        result = self.executeOnHost(self.SCRIPTS_PATH + "initCentOS.sh " + self.containername + " " + str(self.cid) + " " + release + " " + arch + " 0")
      if distro == "fedora":
        result = self.executeOnHost(self.SCRIPTS_PATH + "initFedora.sh " + self.containername + " " + str(self.cid) + " " + release + " " + arch + " 0")
      if distro == "debian":
        result = self.executeOnHost(self.SCRIPTS_PATH + "initDebian.sh " + self.containername + " " + str(self.cid) + " " + release + " " + arch + " 0")
      if distro == "ubuntu":
        result = self.executeOnHost(self.SCRIPTS_PATH + "initUbuntu.sh " + self.containername + " " + str(self.cid) + " " + release + " " + arch + " 0")
    if result == True:
      result = self.executeOnHost(self.SCRIPTS_PATH + "tunnelport.sh " + str(self.cid) + " 22")
    sshpath="/var/lib/lxc/" + self.containername + "/rootfs/root/.ssh/"
    if result == True:
      result = self.executeOnHost("mkdir -p " + sshpath)
    if result == True:
     result = self.shell.executeshell('echo "put ' + self.SSHContainerPath + '/container_rsa.pub authorized_keys2" | sftp -o "StrictHostKeyChecking no" -oPort=' + self.port + ' -i ' + self.SSHContainerPath + '/container_rsa root@' + self.hostname + ':' + sshpath)
    if result == True:
      result = self.executeOnHost("cd " + sshpath + " && cat authorized_keys2 >> authorized_keys && rm authorized_keys2")
    if result == True:
      result = self.executeOnHost("chmod 700 " + sshpath + " && chmod 600 " + sshpath + "authorized_keys")
    return result

  def startmachine(self):
    if self.executeOnHost("lxc-start -d -n " + self.containername):
      # remove the ip address
      if self.containerPort == "22":
        self.shell.executeshell('ssh-keygen -f "' + os.path.expanduser("~") + '/.ssh/known_hosts" -R ' + self.containerIP)
      else:
        self.shell.executeshell('ssh-keygen -f "' + os.path.expanduser("~") + '/.ssh/known_hosts" -R [' + self.containerIP + ']:' + self.containerPort)
      # wait until ssh server is running
      result = self.executeInContainer('echo "container is running"')
      return result
    return False

  def executeInContainer(self, command):
    """Execute a command in a container via SSH"""
    print (" * Executing '%s' in %s..." % (command,
                                             self.containername))
    # wait until ssh server is running
    for x in range(0, 24):
      result = self.shell.executeshell('ssh -f -o "StrictHostKeyChecking no" -o Port=' + self.containerPort + ' -i ' + self.SSHContainerPath + "/container_rsa root@" + self.containerIP + " \"export LC_ALL=C; (" + command + ") 2>&1 && echo \$?\"")
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
    return self.executeOnHost("lxc-destroy --name " + self.containername + " && sleep 10")

  def stop(self):
    return self.executeOnHost("lxc-stop --name " + self.containername + " && sleep 10")

  def rsyncContainerPut(self, src, dest):
    return self.rsyncHostPut(src, "/var/lib/lxc/" + self.containername + "/rootfs" + dest)

  def rsyncContainerGet(self, path, dest = None):
    if dest == None:
      dest = path[:path.rindex("/")]
    result = self.shell.executeshell('rsync -avz -e "ssh -i ' + self.SSHContainerPath + "/container_rsa -p " + self.port + '" root@' + self.hostname + ':/var/lib/lxc/' + self.containername + '/rootfs' + path + ' ' + dest)
    return result

  def rsyncHostPut(self, src, dest = None):
    if dest == None:
      dest = src
    dest = dest[:dest.rindex("/")]
    result = self.shell.executeshell('rsync -avz --delete -e "ssh -i ' + self.SSHContainerPath + "/container_rsa -p " + self.port + '" ' + src + ' root@' + self.hostname + ':' + dest)
    return result 

  def rsyncHostGet(self, path, dest = None):
    if dest == None:
      dest = path[:path.rindex("/")]
    result = self.shell.executeshell('rsync -avz --delete -e "ssh -i ' + self.SSHContainerPath + "/container_rsa -p " + self.port + '" root@' + self.hostname + ':' + path + ' ' + dest)
    return result

  def installmount(self, localpath, hostpath = None):
    if hostpath is None:
      hostpath = "/mnt/lbs/" + self.slot + "/" + self.distro + "/" + self.release + "/" + self.arch + localpath
    result = self.executeOnHost(self.SCRIPTS_PATH + "initMount.sh " + hostpath + " " + self.containername + " " + localpath)
    if result:
      if not os.path.exists(hostpath):
          self.shell.executeshell("mkdir -p " + hostpath)
      #rsync the contents
      return self.rsyncHostPut(hostpath)
    return False
