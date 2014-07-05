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

  def create_sshkeys(self):
    """Create SSH keys to access containers with"""
    # m2crypto hasn't been ported to python3 yet
    # so for now we do it via shell
    self.logger.print (" * Generating ssh keypair...")
    directory = os.path.dirname(self.LBSHOME_PATH + "ssh/")
    if not os.path.exists(directory):
      os.makedirs(directory)
    if self.shell.executeshell(("ssh-keygen -f %sssh/container_rsa -N ''"
                % (self.LBSHOME_PATH))):
      self.logger.print ("   keypair generated" )
      return True
    else:
      self.logger.print ("   keypair generation failed")
      return False

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
    self.shell.executeshell("chmod -R 600 " + root_fs + "/root/.ssh")
    self.shell.executeshell("chmod -R 600 " + self.LBSHOME_PATH + "ssh/container_rsa")
    self.logger.print (" Done with Updating keys...")
