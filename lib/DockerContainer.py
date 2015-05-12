#!/usr/bin/env python3
"""Wrapper for Docker Container Management"""

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

class DockerContainer(RemoteContainer):
  def __init__(self, containername, configBuildMachine, logger):
    RemoteContainer.__init__(self, containername, configBuildMachine, logger)

  def executeOnHost(self, command):
    return RemoteContainer.executeOnHost(self, command)

  def createmachine(self, distro, release, arch, staticIP):
    # create docker container with specified OS
    self.distro = distro
    self.release = release
    self.arch = arch
    self.staticIP = staticIP

    # TODO: somehow docker stop does not succeed. the current solution only works with CentOS host...
    if self.executeOnHost("if [ ! -z \\\"\`docker ps -a | grep " + self.name + "\`\\\" ]; then service docker restart && docker stop " + self.name + " && docker rm " + self.name + "; fi") == False:
      return False

    if arch != 'amd64':
      # TODO: we do not support 32 bit builds with docker currently
      # perhaps: http://stackoverflow.com/a/26729010 ENTRYPOINT ["linux32"]
      print("we do not support 32 bit (" + arch + ") containers yet")
      return False

    result = False
    if distro == "centos":
      release=release
    if distro == "fedora":
      if release == "rawhide":
        # rawhide is an upgrade from the latest fedora release. see BuildHelperFedora.PrepareMachineAfterStart
        release = "21"
    if distro == "debian":
      if release == 'wheezy':
        release = 7
      elif release == 'jessie':
        release = 8
    if distro == "ubuntu":
      if release == 'trusty':
        release = 14.04
      elif release == 'precise':
        release = 12.04

    result = self.executeOnHost("cd docker-scripts && ./initDockerContainer.sh " + self.name + " " + str(self.cid) + " Dockerfiles/Dockerfile." + distro + release)

    return result

  def startmachine(self):
    # remove the ip address
    if self.containerPort == "22":
      self.shell.executeshell('ssh-keygen -f "/root/.ssh/known_hosts" -R ' + self.containerIP)
    else:
      self.shell.executeshell('ssh-keygen -f "/root/.ssh/known_hosts" -R [' + self.containerIP + ']:' + self.containerPort)

    # wait until ssh server is running
    result = self.executeInContainer('echo "container is running"')
    return result

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
    return self.executeOnHost("docker rm " + self.name)

  def stop(self):
    return self.executeOnHost("docker stop " + self.name)

  def copytree(self, src, dest):
    # TODO
    return False
    return self.rsyncHostPut(src, "/var/lib/lxc/" + self.name + "/rootfs" + dest)

  def rsyncContainerGet(self, path, dest = None):
    # TODO
    return False
    if dest == None:
      dest = path[:path.rindex("/")]
    result = self.shell.executeshell('rsync -avz -e "ssh -i ' + self.LBSHOME_PATH + "ssh/container_rsa -p " + self.port + '" root@' + self.name + ':/var/lib/lxc/' + self.name + '/rootfs' + path + ' ' + dest)
    return result

  def rsyncHostPut(self, src, dest = None):
    # TODO
    return False
    if dest == None:
      dest = src
    dest = dest[:dest.rindex("/")]
    result = self.shell.executeshell('rsync -avz --delete -e "ssh -i ' + self.LBSHOME_PATH + "ssh/container_rsa -p " + self.port + '" ' + src + ' root@' + self.name + ':' + dest)
    return result 

  def rsyncHostGet(self, path, dest = None):
    # TODO
    return False
    if dest == None:
      dest = path[:path.rindex("/")]
    result = self.shell.executeshell('rsync -avz --delete -e "ssh -i ' + self.LBSHOME_PATH + "ssh/container_rsa -p " + self.port + '" root@' + self.name + ':' + path + ' ' + dest)
    return result

  def installmount(self, localpath, hostpath = None):
    # TODO
    return False
    if hostpath is None:
      hostpath = self.LBSHOME_PATH + self.slot + "/" + self.distro + "/" + self.release + "/" + self.arch + localpath
    result = self.executeOnHost("./scripts/initMount.sh " + hostpath + " " + self.name + " " + localpath)
    if result:
      if not os.path.exists(hostpath):
          self.shell.executeshell("mkdir -p " + hostpath)
      #rsync the contents
      return self.rsyncHostPut(hostpath)
    return False
