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

import lxc
import sys
import os
import time
#from paramiko import SSHClient
from subprocess import Popen, PIPE, STDOUT
from Logger import Logger

class LXCContainer(lxc.Container):
  def __init__(self, containername, logger):
    lxc.Container.__init__(self, name = containername)
    self.logger = logger
    # we are reusing the slots, for caches etc
    self.slot = containername
    self.distro = ""
    self.release = ""
    self.arch = ""
    self.staticIP = ""
    self.LBSHOME_PATH = "/var/lib/lbs/"
    self.LXCHOME_PATH = "/var/lib/lxc/"

  def executeshell(self, command):
    self.logger.print("now running: " + command)

    # see http://stackoverflow.com/questions/14858059/detecting-the-end-of-the-stream-on-popen-stdout-readline
    # problem is that subprocesses are started, and the pipe is still open???
    child = Popen(command, stdout=PIPE, stderr=STDOUT, universal_newlines=True, shell=True)
    processFinished = False
    returncode=None
    #for line in iter(child.stdout.readline,''):
    while True:
      line=child.stdout.readline()
      if ((len(line) == 0) and processFinished) or ("LBSScriptFinished" in line):
        if not processFinished and ("LBSScriptFinished" in line):
          returncode = child.poll()
          if returncode is None:
            returncode = 0
        break;
      self.logger.print(line)
      returncode = child.poll()
      if not processFinished and returncode is not None:
        processFinished = True
    return (not returncode)

  def createmachine(self, lxcdistro, lxcrelease, lxcarch, staticIP):
    # create lxc container with specified OS
    self.distro = lxcdistro
    self.release = lxcrelease
    self.arch = lxcarch
    self.staticIP = staticIP
    lxc.Container.__init__(self, self.name)
    self.destroy();
    #if self.create(lxcdistro, 0, {"release": lxcrelease, "arch": lxcarch}):
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

  def execute(self, command):
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
      result = self.executeshell('ssh -f -o "StrictHostKeyChecking no" -i ' + self.LBSHOME_PATH + "ssh/container_rsa " + ip + " \"LANG=C " + command + " 2>&1\"")
      if result:
        return True
      # sleep for half a second
      time.sleep(0.5)
    return False

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
