#!/usr/bin/env python3
"""Interface class for Container Management"""

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
import Config
from Logger import Logger
from Shell import Shell

class RemoteContainer:
  def __init__(self, containername, configBuildMachine, logger):
    self.hostname = containername

    self.port="22"
    if "port" in configBuildMachine:
      self.port=str(configBuildMachine['port'])
    self.cid=10
    if "cid" in configBuildMachine:
      self.cid=configBuildMachine['cid']

    self.containername = str(self.cid) + "-" + containername
    self.containerIP=socket.gethostbyname(self.hostname)
    self.containerPort=str(2000+int(self.cid))

    # we just test if the host server for the build container is actually hosting the LBS application as well
    lbsipaddress=socket.gethostbyname(socket.gethostname()).split('.')
    buildserveraddress=socket.gethostbyname(containername).split('.')

    if buildserveraddress[3] == "1":
      buildserveraddress.pop()
      lbsipaddress.pop()
      if '.'.join(buildserveraddress) == '.'.join(lbsipaddress):
        self.containerIP='.'.join(buildserveraddress) + "." + str(self.cid)
        self.containerPort="22"

    # or if the container is running on localhost
    if socket.gethostbyname(containername) == "127.0.0.1":
      if os.path.isfile("/etc/libvirt/qemu/networks/default.xml"):
        # Fedora
        self.containerIP="192.168.122." + str(self.cid)
      elif os.path.isfile("/etc/init/lxc-net.conf"):
        # Ubuntu
        self.containerIP="10.0.3." + str(self.cid)
      self.containerPort="22"

    self.config = Config.LoadConfig()
    self.SSHContainerPath = self.config['lbs']['SSHContainerPath']
    self.logger = logger
    self.shell = Shell(logger)
    # we are reusing the slots, for caches etc
    self.slot = containername
    self.distro = ""
    self.release = ""
    self.arch = ""
    self.staticIP = ""

  def executeOnHost(self, command):
    if self.shell.executeshell('ssh -f -o "StrictHostKeyChecking no" -p ' + self.port + ' -i ' + self.SSHContainerPath + "/container_rsa root@" + self.hostname + " \"export LANG=C; " + command + " 2>&1; echo \$?\""):
      return self.logger.getLastLine() == "0"
    return False

  def createmachine(self, distro, release, arch, staticIP):
    # not implemented here
    return False

  def startmachine(self):
    # not implemented here
    return False

  def executeInContainer(self, command):
    """Execute a command in a container via SSH"""
    # not implemented here
    return False

  def destroy(self):
    # not implemented here
    return False

  def stop(self):
    # not implemented here
    return False

  def rsyncContainerPut(self, src, dest):
    # not implemented here
    return False

  def rsyncContainerGet(self, path, dest = None):
    # not implemented here
    return False

  def rsyncHostPut(self, src, dest = None):
    # not implemented here
    return False

  def rsyncHostGet(self, path, dest = None):
    # not implemented here
    return False

  def installmount(self, localpath, hostpath = None):
    # not implemented here
    return False
