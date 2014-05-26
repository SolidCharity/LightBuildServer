#!/usr/bin/env python3
"""BuildHelper for CentOS: knows how to build packages for CentOS"""

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
import os
import yaml

class BuildHelperCentos(BuildHelper):
  'build packages for CentOS'

  def __init__(self, container, pathInsideContainer, projectname, packagename):
    self.dist='centos'
    BuildHelper.__init__(self, container, pathInsideContainer, projectname, packagename)

  def PrepareMachineBeforeStart(self):
    rootfs=self.container.getrootfs()
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
    # setup tmpfs /dev/shm
    self.container.executeshell("echo \"lxc.mount.entry = tmpfs " + rootfs + "/dev/shm tmpfs defaults 0 0\" >> " + rootfs + "/../config")
    # configure timezone
    self.container.executeshell("cd " + rootfs + "/etc; rm -f localtime; ln -s ../usr/share/zoneinfo/Europe/Berlin localtime")

  def PrepareForBuilding(self):
    if not self.run("yum -y update"):
      return self.output
    if not self.run("yum -y install wget tar"):
      return self.output
    self.run("mkdir -p rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}");

  def InstallRequiredPackages(self):
    rootfs=self.container.getrootfs()

    # first install required repos
    configfile=rootfs + "/root/lbs-" + self.projectname + "-master/config.yml"
    stream = open(configfile, 'r')
    config = yaml.load(stream)
    repos = config['lbs'][self.dist][str(self.container.release)]['repos']
    for repo in repos:
      self.run("cd /etc/yum.repos.d/; wget " + repo);

    # now install required packages
    specfile=rootfs + "/root/" + "lbs-" + self.projectname + "-master/" + self.packagename + "/" + self.packagename + ".spec"
    if os.path.isfile(specfile):
      for line in open(specfile):
        if line.startswith("BuildRequires: "):
          packagesWithVersions=line[len("BuildRequires: "):].split()
          packages=[]
          ignoreNext=False
          for word in packagesWithVersions:
            if not ignoreNext:
              # filter >= 3.0, only use package names
              if word[0] == '>' or word[0] == '<' or word[0] == '=':
                ignoreNext=True
              else:
                packages.append(word)
            else:
              ignoreNext=False
          if not self.run("yum -y install rpm-build " + " ".join(packages)):
            return self.output

  def BuildPackage(self):
    rootfs=self.container.getrootfs()
    specfile=rootfs + "/root/" + "lbs-" + self.projectname + "-master/" + self.packagename + "/" + self.packagename + ".spec"
    if os.path.isfile(specfile):
      self.run("cp lbs-" + self.projectname + "-master/" + self.packagename + "/" + self.packagename + ".spec rpmbuild/SPECS")

      # copy patches, and other files (eg. env.sh for mono-opt)
      self.run("cp lbs-" + self.projectname + "-master/" + self.packagename + "/* rpmbuild/SOURCES")

      # move the sources that have been downloaded according to instructions in config.yml. see BuildHelper::DownloadSources
      self.run("mv sources/* rpmbuild/SOURCES")

      # TODO: build counter for automatically increasing the release number?
      self.run("sed -i -e 's/Release: %{release}/Release: 99/g' rpmbuild/SPECS/" + self.packagename + ".spec")
      if not self.run("rpmbuild -ba rpmbuild/SPECS/" + self.packagename + ".spec"):
        return self.output

  def RunTests(self):
    if not self.run("cd lbs-" + self.projectname + "-master/" + self.packagename + " && ./runtests.sh"):
      return self.output
