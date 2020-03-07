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
    self.containertype = containertype
    self.staticMachine = (True if ('static' in configBuildMachine and configBuildMachine['static'] == "t") else False)

    self.port="22"
    if configBuildMachine['port'] is not None:
      self.port=str(configBuildMachine['port'])
    self.cid=10
    if configBuildMachine['cid'] is not None:
      self.cid=configBuildMachine['cid']

    self.containername = str(self.cid).zfill(3) + "-" + containername
    if containertype == "lxd":
      self.containername="l" + str(self.cid).zfill(3) + "-" + containername.replace(".","-")

    self.containerIP=socket.gethostbyname(self.hostname)
    self.containerPort=str(2000+int(self.cid))

    if configBuildMachine['local'] is not None and configBuildMachine['local'] == "t":
      # the host server for the build container is actually hosting the LBS application as well
      # or the container is running on localhost
      if containertype == "lxc":
        self.containerIP=self.calculateLocalContainerIP(self.cid)
        self.containerPort="22"
      if containertype == "lxd":
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
    # for LXD, we always configure the bridge with 10.0.4:
    # lxc network create lxdbr0 ipv6.address=none ipv4.address=10.0.4.1/24 ipv4.nat=true
    if self.containertype == "lxd":
      return "10.0.4." + str(cid)

    # test if we are inside a container as well
    # we just test if the host server for the build container is actually hosting the LBS application as well
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # just need to connect to any external host to know which is the IP address of the machine that hosts LBS
    s.connect((self.hostname, 80))
    lbsipaddress=s.getsockname()[0].split('.')
    lbsipaddress.pop()
    # on CentOS: /etc/libvirt/qemu/networks/default.xml 192.168.122
    # on Fedora 27: /etc/libvirt/qemu/networks/default.xml 192.168.124
    # on Ubuntu 16.04: /etc/default/lxc-net 10.0.3
    if '.'.join(lbsipaddress) == "192.168.122" or '.'.join(lbsipaddress) == "192.168.124" or '.'.join(lbsipaddress) == "10.0.3":
      return '.'.join(lbsipaddress) + "." + str(cid)

    # we are running uwsgi and lxc/docker on one host
    if os.path.isfile("/etc/redhat-release"):
      file = open("/etc/redhat-release", 'r')
      version = file.read()
      if "Fedora" in version:
        return "192.168.124." + str(cid)
      if "CentOS" in version:
        return "192.168.122." + str(cid)
    elif os.path.isfile("/etc/lsb-release"):
      file = open("/etc/lsb-release", 'r')
      version = file.read()
      if "Ubuntu" in version:
        return "10.0.3." + str(cid)

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
