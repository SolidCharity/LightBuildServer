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
import shlex
#from paramiko import SSHClient
from subprocess import Popen, PIPE

class LXCContainer(lxc.Container):
  def __init__(self, containername):
    lxc.Container.__init__(self, name = containername)
    self.output = ""
    self.LBSHOME_PATH = "/var/lib/lbs/"
    self.LXCHOME_PATH = "/var/lib/lxc/"

  def executeshell(self, command):
    print(command)
    cmdlist = shlex.split(command)
    child = Popen(cmdlist, stdout=PIPE, stderr=PIPE)
    while True:
      out = child.stdout.read(1).decode("utf-8")
      if (out == '') and child.poll() != None:
        break
      if (out != ''):
        sys.stdout.write(out)
        self.output += out
        sys.stdout.flush()
    streamdata = child.communicate();
    sys.stdout.write(streamdata[1].decode("utf-8"))
    sys.stdout.flush()
    self.output += streamdata[1].decode("utf-8")
    return (not child.returncode)

  def createmachine(self, lxcdistro, lxcrelease, lxcarch):
    # create lxc container with specified OS
    self.output = ""
    #if self.create(lxcdistro, 0, {"release": lxcrelease, "arch": lxcarch}):
    result = self.executeshell("lxc-create -t download --name " + self.name +
	" -- -d " + lxcdistro + " -r " + lxcrelease + " -a " + lxcarch)
    if result:
      lxc.Container.__init__(self, self.name)
      if not os.path.exists(self.LBSHOME_PATH + "ssh/container_rsa"):
        self.create_sshkeys()
      self.install_sshkey()
    return result

  def startmachine(self):
    if self.executeshell("lxc-start -d -n " + self.name):
      # wait until ip can be detected
      for x in range(0, 19):
        if not self.getIP() == None:
          return True
        # sleep for half a second
        time.sleep(0.5)
    return False

  def create_sshkeys(self):
    """Create SSH keys to access containers with"""
    # m2crypto hasn't been ported to python3 yet
    # so for now we do it via shell
    print (" * Generating ssh keypair...")
    directory = os.path.dirname(self.LBSHOME_PATH + "ssh/")
    if not os.path.exists(directory):
      os.makedirs(directory)
    if self.executeshell(("ssh-keygen -f %sssh/container_rsa -N ''"
                % (self.LBSHOME_PATH))):
      print ("   keypair generated" )
      return True
    else:
      print ("   keypair generation failed")
      return False

  def install_sshkey(self):
    """Update ssh key in LXC container"""
    print (" * Updating keys...")
    # read public key file:
    pkey = open(self.LBSHOME_PATH + "ssh/container_rsa.pub", "r")
    pkeydata = pkey.read()
    pkey.close()
    # does not seem to work, Invalid configuration key
    #root_fs = self.get_config_item('lxc.rootfs')
    root_fs = self.LXCHOME_PATH + self.name + "/rootfs/"
    if not os.path.exists(root_fs + "/root/.ssh"):
      os.makedirs(root_fs + "/root/.ssh")
    # append public key to authorized_keys in container
    fout = open(root_fs + "/root/.ssh/authorized_keys", "a+")
    fout.write(pkeydata)
    fout.close()
    self.executeshell("chmod -R 600 " + root_fs + "/root/.ssh")
    self.executeshell("chmod -R 600 " + self.LBSHOME_PATH + "ssh/container_rsa")

  def getIP(self):
    ipaddress = self.get_ips(family="inet", interface="eth0")
    if not ipaddress:
      return None
    return ipaddress[0]

  def execute(self, command):
    """Execute a command in a container via SSH"""
    self.output = ""
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
      result = self.executeshell('ssh -o "StrictHostKeyChecking no" -i ' + self.LBSHOME_PATH + "ssh/container_rsa " + self.getIP() + " " + command)
      if result:
        return True
      # sleep for half a second
      time.sleep(0.5)
    return False
