#!/usr/bin/env python3
"""Wrapper for Docker Container Management"""

# Copyright (c) 2014-2022 Timotheus Pokorra

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
from lib.RemoteContainer import RemoteContainer
from lib.Logger import Logger
from lib.Shell import Shell

class DockerContainer(RemoteContainer):
  def __init__(self, containername, configBuildMachine, logger, packageSrcPath):
    RemoteContainer.__init__(self, containername, configBuildMachine, logger, packageSrcPath, "docker")
    self.SCRIPTS_PATH = "/usr/share/docker-scripts/"

  def executeOnHost(self, command):
    return RemoteContainer.executeOnHost(self, command)

  def createmachine(self, distro, release, arch, staticIP):
    # create docker container with specified OS
    self.distro = distro
    self.release = release
    self.release_for_docker = release
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

    self.release_for_docker = self.release
    if self.distro == "centos":
      if self.release == "9-Stream":
        self.release_for_docker="stream9"
      elif self.release == "8-Stream":
        self.release_for_docker="stream8"
    if self.distro == "fedora":
      if self.release == "rawhide":
        # rawhide is an upgrade from the latest fedora release. see BuildHelperFedora.PrepareMachineAfterStart
        self.release_for_docker = "40"
    if self.distro == "debian":
      if self.release == 'buster':
        self.release_for_docker = "10"
      elif self.release == 'bullseye':
        self.release_for_docker = "11"
      elif self.release == 'bookworm':
        self.release_for_docker = "12"
    if self.distro == "ubuntu":
      if self.release == 'jammy':
        self.release_for_docker = "22.04"
      if self.release == 'focal':
        self.release_for_docker = "20.04"
      if self.release == 'bionic':
        self.release_for_docker = "18.04"

    return True

  def startmachine(self):
    Dockerfile="Dockerfiles/Dockerfile." + self.distro + self.release_for_docker
    DockerfileExt=self.packageSrcPath + "/Dockerfile." + self.distro + self.release_for_docker
    if not os.path.exists(DockerfileExt):
      DockerfileExt=self.packageSrcPath + "/Dockerfile." + self.distro
    if not os.path.exists(DockerfileExt):
      DockerfileExt=self.packageSrcPath + "/Dockerfile"
    if os.path.exists(DockerfileExt):
      self.executeOnHost("mkdir -p /tmp/" + self.containername)
      DockerfileOrig=Dockerfile
      Dockerfile="/tmp/" + self.containername + "/Dockerfile.new"
      DockerfileUploaded="/tmp/" + self.containername + "/" + os.path.basename(DockerfileExt)
      self.rsyncHostPut(DockerfileExt, DockerfileUploaded)
      self.executeOnHost("cd " + self.SCRIPTS_PATH + " && cat " + DockerfileOrig + " " + DockerfileUploaded + " > " + Dockerfile)
    result = self.executeOnHost("cd " + self.SCRIPTS_PATH + " && ./initDockerContainer.sh " + self.containername + " " + str(self.cid) + ' ' + Dockerfile + ' ' + self.mount)
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
      result = self.shell.executeshell('ssh -f -o "StrictHostKeyChecking no" -o Port=' + self.containerPort + ' -i ' + self.SSHContainerPath + "/container_rsa root@" + self.containerIP + " \"export LC_ALL=C; (" + command + ") 2>&1; echo \$?\"")
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
    return self.executeOnHost("(systemctl restart docker || service docker restart) && sleep 10")

  def rsyncContainerPut(self, src, dest):
    dest = dest[:dest.rindex("/")]
    result = self.shell.executeshell('rsync -avz -e "ssh -o \'StrictHostKeyChecking no\' -i ' + self.SSHContainerPath + "/container_rsa -p " + self.containerPort + '" ' + src + ' root@' + self.hostname + ':' + dest)
    return result

  def rsyncContainerGet(self, path, dest = None):
    if dest == None:
      dest = path[:path.rindex("/")]
    if not os.path.isdir(dest):
      os.makedirs(dest)
    result = self.shell.executeshell('rsync -avz -e "ssh -o \'StrictHostKeyChecking no\' -i ' + self.SSHContainerPath + "/container_rsa -p " + self.containerPort + '" root@' + self.hostname + ':' + path + ' ' + dest)
    return result

  def rsyncHostPut(self, src, dest = None):
    if dest == None:
      dest = src
    dest = dest[:dest.rindex("/")]
    self.executeOnHost("mkdir -p `dirname " + dest + "`")
    result = self.shell.executeshell('rsync -avz --delete -e "ssh -o \'StrictHostKeyChecking no\' -i ' + self.SSHContainerPath + "/container_rsa -p " + self.port + '" ' + src + ' root@' + self.hostname + ':' + dest)
    return result 

  def rsyncHostGet(self, path, dest = None):
    if dest == None:
      dest = path[:path.rindex("/")]
    if not os.path.isdir(dest):
      os.makedirs(dest)
    result = self.shell.executeshell('rsync -avz --delete -e "ssh -o \'StrictHostKeyChecking no\' -i ' + self.SSHContainerPath + "/container_rsa -p " + self.port + '" root@' + self.hostname + ':' + path + ' ' + dest)
    return result

  def installmount(self, srcpath, hostpath, containerpath):
    self.mount += " -v "+ hostpath + ":" + containerpath
    if not os.path.exists(srcpath):
      self.shell.executeshell("mkdir -p " + srcpath)
    #rsync the contents
    return self.rsyncHostPut(srcpath, hostpath)
