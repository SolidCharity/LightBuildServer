#!/usr/bin/env python3
"""BuildHelper for Fedora: knows how to build packages for Fedora"""

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
from BuildHelper import BuildHelper;
from BuildHelperCentos import BuildHelperCentos;
import os
import yaml

class BuildHelperFedora(BuildHelperCentos):
  'build packages for Fedora'

  def __init__(self, container, pathInsideContainer, username, projectname, packagename):
    BuildHelperCentos.__init__(self, container, pathInsideContainer, username, projectname, packagename)
    self.dist='fedora'

  def PrepareMachineBeforeStart(self):
    rootfs=self.container.getrootfs()
    if rootfs == "":
      return True
    # clear the root password, since it is expired anyway, and no ssh access would be possible
    if not self.container.executeshell("chroot " + rootfs + " passwd -d root"):
      return self.output
    # setup a static IP address, to speed up the startup
    networkfile = rootfs+"/etc/sysconfig/network-scripts/ifcfg-eth0"
    self.container.executeshell("sed -i 's/^BOOTPROTO=dhcp/BOOTPROTO=static/g' "+networkfile)
    self.container.executeshell("echo \"IPADDR=" + self.container.staticIP +"\" >> " + networkfile)
    self.container.executeshell("echo \"GATEWAY=10.0.3.1\" >> " + networkfile)
    self.container.executeshell("echo \"NETMASK=255.255.255.0\" >> " + networkfile)
    self.container.executeshell("echo \"NETWORK=10.0.3.0\" >> " + networkfile)
    self.container.executeshell("echo \"nameserver 10.0.3.1\" > " + rootfs + "/etc/resolv.conf")
    self.container.executeshell("echo \"lxc.network.ipv4="+self.container.staticIP + "/24\" >> " + rootfs + "/../config")
    # fix a problem with AppArmor. otherwise you get a SEGV
    self.container.executeshell("echo \"lxc.aa_profile = unconfined\" >> " + rootfs + "/../config")
    # setup tmpfs /dev/shm
    #not needed for Fedora??? self.container.executeshell("echo \"lxc.mount.entry = tmpfs " + rootfs + "/dev/shm tmpfs defaults 0 0\" >> " + rootfs + "/../config")
    # configure timezone
    self.container.executeshell("cd " + rootfs + "/etc; rm -f localtime; ln -s ../usr/share/zoneinfo/Europe/Berlin localtime")
    # yum: keep the cache
    self.container.executeshell("sed -i 's/^keepcache=0/keepcache=1/g' " + rootfs + "/etc/yum.conf")
    return True

  def PrepareMachineAfterStart(self):
    if self.container.release == "rawhide":
      self.run("yum install -y fedora-release-rawhide yum-utils")
      self.run("yum-config-manager --disable fedora updates updates-testing")
      self.run("yum-config-manager --enable rawhide")
      self.run("yum update -y yum")
      self.run("yum --releasever=rawhide -y distro-sync --nogpgcheck")
    return True
