#!/usr/bin/env python3
"""Interface class for Container Management"""

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
import Config
from Logger import Logger
from Shell import Shell

class RemoteContainer:
  def __init__(self, containername, configBuildMachine, logger, packageSrcPath, containertype):
    self.hostname = containername
    self.staticMachine = (True if ('static' in configBuildMachine and configBuildMachine['static'] == True) else False)

    self.port="22"
    if "port" in configBuildMachine:
      self.port=str(configBuildMachine['port'])
    self.cid=10
    if "cid" in configBuildMachine:
      self.cid=configBuildMachine['cid']

    self.containername = str(self.cid).zfill(3) + "-" + containername
    self.containerIP=socket.gethostbyname(self.hostname)
    self.containerPort=str(2000+int(self.cid))

    if "local" in configBuildMachine and configBuildMachine['local'] == True:
      # the host server for the build container is actually hosting the LBS application as well
      # or the container is running on localhost
      if containertype == "lxc":
        self.containerIP=self.calculateLocalContainerIP(self.cid)
        self.containerPort="22"
      if containertype == "docker":
        self.containerIP=self.calculateLocalContainerIP(1)
        self.containerPort=str(2000+int(self.cid))

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
    self.packageSrcPath = packageSrcPath

  def calculateLocalContainerIP(self, cid):
    if os.path.isfile("/etc/libvirt/qemu/networks/default.xml"):
      # Fedora
      return "192.168.122." + str(cid)
    elif os.path.isfile("/etc/init/lxc-net.conf"):
      # Ubuntu
      return "10.0.3." + str(cid)
    else:
      # we are inside a container as well
      # we just test if the host server for the build container is actually hosting the LBS application as well
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
      # just need to connect to any external host to know which is the IP address of the machine that hosts LBS
      s.connect((self.containername, 80))
      lbsipaddress=s.getsockname()[0].split('.')
      lbsipaddress.pop()
      return '.'.join(lbsipaddress) + "." + str(cid)

  def executeOnHost(self, command):
    if self.shell.executeshell('ssh -f -o "StrictHostKeyChecking no" -p ' + self.port + ' -i ' + self.SSHContainerPath + "/container_rsa root@" + self.hostname + " \"export LC_ALL=C; (" + command + ") 2>&1; echo \$?\""):
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
