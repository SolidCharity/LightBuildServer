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
    self.SCRIPTS_PATH = "/usr/share/docker-scripts/"

  def executeOnHost(self, command):
    return RemoteContainer.executeOnHost(self, command)

  def createmachine(self, distro, release, arch, staticIP):
    # create docker container with specified OS
    self.distro = distro
    self.release = release
    self.arch = arch
    self.staticIP = staticIP
    self.mount = ""

    # TODO: somehow docker stop does not succeed. the current solution only works with CentOS host...
    if self.executeOnHost("if [ ! -z \\\"\`docker ps -a | grep " + self.containername + "\`\\\" ]; then service docker restart && docker stop " + self.containername + " && docker rm " + self.containername + "; fi") == False:
      return False

    if arch != 'amd64':
      # TODO: we do not support 32 bit builds with docker currently
      # perhaps: http://stackoverflow.com/a/26729010 ENTRYPOINT ["linux32"]
      print("we do not support 32 bit (" + arch + ") containers yet")
      return False

    if self.distro == "centos":
      self.release=release
    if self.distro == "fedora":
      if self.release == "rawhide":
        # rawhide is an upgrade from the latest fedora release. see BuildHelperFedora.PrepareMachineAfterStart
        self.release = "24"
    if self.distro == "debian":
      if self.release == 'wheezy':
        self.release = 7
      elif self.release == 'jessie':
        self.release = 8
    if self.distro == "ubuntu":
      if self.release == 'trusty':
        self.release = 14.04
      elif self.release == 'precise':
        self.release = 12.04

    return True

  def startmachine(self):
    result = self.executeOnHost("cd " + self.SCRIPTS_PATH + " && ./initDockerContainer.sh " + self.containername + " " + str(self.cid) + " Dockerfiles/Dockerfile." + self.distro + self.release + ' ' + self.mount)
    if result == False:
      return False

    # remove the ip address
    if self.containerPort == "22":
      self.shell.executeshell('ssh-keygen -f "' + os.path.expanduser("~") + '/.ssh/known_hosts" -R ' + self.containerIP)
      self.shell.executeshell('ssh-keygen -f "' + os.path.expanduser("~") + '/.ssh/known_hosts" -R ' + self.hostname)
    else:
      self.shell.executeshell('ssh-keygen -f "' + os.path.expanduser("~") + '/.ssh/known_hosts" -R [' + self.containerIP + ']:' + self.containerPort)
      self.shell.executeshell('ssh-keygen -f "' + os.path.expanduser("~") + '/.ssh/known_hosts" -R [' + self.hostname + ']:' + self.containerPort)

    # wait until ssh server is running
    result = self.executeInContainer('echo "container is running"')
    return result

  def executeInContainer(self, command):
    """Execute a command in a container via SSH"""
    print (" * Executing '%s' in %s..." % (command,
                                             self.containername))
    # wait until ssh server is running
    for x in range(0, 24):
      result = self.shell.executeshell('ssh -f -o "StrictHostKeyChecking no" -o Port=' + self.containerPort + ' -i ' + self.SSHContainerPath + "/container_rsa root@" + self.hostname + " \"export LANG=C; " + command + " 2>&1 && echo \$?\"")
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
    return self.executeOnHost("docker rm " + self.containername)

  def stop(self):
    #TODO docker stop does not work, not even for test job
    #return self.executeOnHost("docker stop " + self.containername)
    return self.executeOnHost("systemctl restart docker")

  def rsyncContainerPut(self, src, dest):
    dest = dest[:dest.rindex("/")]
    result = self.shell.executeshell('rsync -avz -e "ssh -i ' + self.SSHContainerPath + "/container_rsa -p " + self.containerPort + '" ' + src + ' root@' + self.hostname + ':' + dest)
    return result

  def rsyncContainerGet(self, path, dest = None):
    if dest == None:
      dest = path[:path.rindex("/")]
    result = self.shell.executeshell('rsync -avz -e "ssh -i ' + self.SSHContainerPath + "/container_rsa -p " + self.containerPort + '" root@' + self.hostname + ':' + path + ' ' + dest)
    return result

  def rsyncHostPut(self, src, dest = None):
    if dest == None:
      dest = src
    dest = dest[:dest.rindex("/")]
    self.executeOnHost("mkdir -p `dirname " + dest + "`")
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
    self.mount += " -v "+ hostpath + ":" + localpath
    if not os.path.exists(hostpath):
      self.shell.executeshell("mkdir -p " + hostpath)
    #rsync the contents
    return self.rsyncHostPut(hostpath)
