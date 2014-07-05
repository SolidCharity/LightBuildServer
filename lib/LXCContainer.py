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
from Logger import Logger
from Shell import Shell

class LXCContainer():
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

  def executeshell(self, command):
    return self.shell.executeshell(command)

  def createmachine(self, lxcdistro, lxcrelease, lxcarch, staticIP):
    # create lxc container with specified OS
    self.distro = lxcdistro
    self.release = lxcrelease
    self.arch = lxcarch
    self.staticIP = staticIP
    self.destroy();
    # in case that https://jenkins.linuxcontainers.org/ is down and -t download does not work
    # for centos 5 there is no download available anyway
    if lxcdistro=="centos" and lxcrelease=="5":
      if lxcarch == "amd64":
        lxcarch = "x86_64"
      result = self.executeshell("lxc-create --name " + self.name + 
         " -t " + lxcdistro + " -- --release=" + lxcrelease + " --arch=" + lxcarch)
    # fedora works better when we install it directly (related to https://github.com/SolidCharity/LightBuildServer/issues/23)
    elif lxcdistro=="fedora":
      if lxcarch == "amd64":
        lxcarch = "x86_64"
      if lxcrelease == "rawhide":
        # first install latest Fedora version, then upgrade later to rawhide
        result = self.executeshell("lxc-create --name " + self.name + 
           " -t " + lxcdistro + " -- --release=20 --arch=" + lxcarch)
      else:
        result = self.executeshell("lxc-create --name " + self.name + 
           " -t " + lxcdistro + " -- --release=" + lxcrelease + " --arch=" + lxcarch)
    else:
      result = self.executeshell("lxc-create -t download --name " + self.name +
    	" -- -d " + lxcdistro + " -r " + lxcrelease + " -a " + lxcarch)
    if result:
      lxc.Container.__init__(self, self.name)
      if not os.path.exists(self.LBSHOME_PATH + "ssh/container_rsa"):
        self.create_sshkeys()
      self.install_sshkey()

      # for each build slot, create a cache mount, depending on the OS. /var/cache contains yum and apt caches
      if lxcdistro == "debian" or lxcdistro == "ubuntu":
        self.installmount("/var/cache/apt")
      if lxcdistro == "fedora" or lxcdistro == "centos":
        self.installmount("/var/cache/yum")
    return result

  def startmachine(self):
    if self.executeshell("lxc-start -d -n " + self.name):
      # wait until ip can be detected
      for x in range(0, 19):
        if not self.getIP() == None:
          ip = self.getIP()
          result = self.executeshell('ssh-keygen -f "/root/.ssh/known_hosts" -R ' + ip)
          return True
        # sleep for half a second
        time.sleep(0.5)
    return False

  def destroy(self):
    return self.executeshell("lxc-destroy -n " + self.name)

  def stop(self):
    return self.executeshell("lxc-stop -n " + self.name)

  def create_sshkeys(self):
    """Create SSH keys to access containers with"""
    # m2crypto hasn't been ported to python3 yet
    # so for now we do it via shell
    self.logger.print (" * Generating ssh keypair...")
    directory = os.path.dirname(self.LBSHOME_PATH + "ssh/")
    if not os.path.exists(directory):
      os.makedirs(directory)
    if self.executeshell(("ssh-keygen -f %sssh/container_rsa -N ''"
                % (self.LBSHOME_PATH))):
      self.logger.print ("   keypair generated" )
      return True
    else:
      self.logger.print ("   keypair generation failed")
      return False

  def getrootfs(self):
    # does not seem to work, Invalid configuration key
    return self.get_config_item('lxc.rootfs')
    #return self.LXCHOME_PATH + self.name + "/rootfs/"
    
  def install_sshkey(self):
    """Update ssh key in LXC container"""
    self.logger.print (" * Updating keys...")
    # read public key file:
    pkey = open(self.LBSHOME_PATH + "ssh/container_rsa.pub", "r")
    pkeydata = pkey.read()
    pkey.close()
    root_fs=self.getrootfs()
    if not os.path.exists(root_fs + "/root/.ssh"):
      os.makedirs(root_fs + "/root/.ssh")
    # append public key to authorized_keys in container
    fout = open(root_fs + "/root/.ssh/authorized_keys", "a+")
    fout.write(pkeydata)
    fout.close()
    self.executeshell("chmod -R 600 " + root_fs + "/root/.ssh")
    self.executeshell("chmod -R 600 " + self.LBSHOME_PATH + "ssh/container_rsa")
    self.logger.print (" Done with Updating keys...")

  def getIP(self):
    ipaddress = self.get_ips(family="inet", interface="eth0")
    if not ipaddress:
      return None
    return ipaddress[0]

  def executeInContainer(self, command):
    """Execute a command in a container via SSH"""
    print (" * Executing '%s' in %s..." % (command,
                                             self.name))
    # wait until ssh server is running
    for x in range(0, 19):
      #client = SSHClient()
      #client.set_missing_host_key_policy(paramiko.WarningPolicy())
      #key = paramiko.RSAKey.from_private_key_file(self.LBSHOME_PATH + "ssh/container_rsa")
      #client.load_system_host_keys()
      #client.connect(self.getIP(), username="root", pkey=key)
      #stdin, stdout, stderr = client.exec_command(command)
      #result = not stdout.channel.recv_exit_status()
      ip = self.getIP()
      result = self.executeshell('ssh -f -o "StrictHostKeyChecking no" -i ' + self.LBSHOME_PATH + "ssh/container_rsa " + ip + " \"export LANG=C; " + command + " 2>&1; echo \$?\"")
      if result:
        return self.logger.getLastLine() == "0"
      # sleep for half a second
      time.sleep(0.5)
    return False

  def copytree(self, src, dest):
    shutil.copytree(src, self.container.getrootfs() + dest)

  def installmount(self, localpath, hostpath = None):
      containerpath = self.getrootfs() + localpath
      if hostpath is None:
        hostpath = self.LBSHOME_PATH + self.slot + "/" + self.distro + "/" + self.release + "/" + self.arch + localpath
      if os.path.exists(containerpath):
        if not os.path.exists(hostpath):
          # eg /var/cache/apt after installing first machine
          self.executeshell("mkdir -p " + hostpath)
          self.executeshell("rm -Rf " + hostpath)
          self.executeshell("mv " + containerpath + " " + hostpath)
        else:
          self.executeshell("rm -Rf " + containerpath)
      else:
        if not os.path.exists(hostpath):
          self.executeshell("mkdir -p " + hostpath)
      self.executeshell("mkdir -p " + containerpath)
      fout = open(self.LXCHOME_PATH + self.name + "/config", "a+")
      line = "lxc.mount.entry = " + hostpath + " " + containerpath + " none defaults,bind 0 0\n"
      fout.write(line)
      fout.close()
