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

  def __init__(self, container, pathInsideContainer, username, projectname, packagename):
    self.dist='centos'
    BuildHelper.__init__(self, container, pathInsideContainer, username, projectname, packagename)

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
    # yum: keep the cache
    self.container.executeshell("sed -i 's/^keepcache=0/keepcache=1/g' " + rootfs + "/etc/yum.conf")

  def PrepareForBuilding(self):
    #self.run("yum clean headers dbcache rpmdb")
    if not self.run("yum -y update"):
      return self.output
    if not self.run("yum -y install tar createrepo"):
      return self.output
    # CentOS5: /root/rpmbuild should point to /usr/src/redhat
    if self.dist == "centos" and self.container.release == "5":
      self.run("mkdir -p /usr/src/redhat; ln -s /usr/src/redhat rpmbuild")
    self.run("mkdir -p rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}");

  def GetSpecFilename(self):
    pathSrc="/var/lib/lbs/src/"+self.username
    for file in os.listdir(pathSrc + "/lbs-" + self.projectname + "/" + self.packagename):
      if file.endswith(".spec") and self.packagename.startswith(file.split('.')[0]):
        return file
    return self.packagename + ".spec"

  def InstallRequiredPackages(self):
    rootfs=self.container.getrootfs()

    # first install required repos
    configfile=rootfs + "/root/lbs-" + self.projectname + "/config.yml"
    if os.path.isfile(configfile):
      stream = open(configfile, 'r')
      config = yaml.load(stream)
      if self.dist in config['lbs'] and str(self.container.release) in config['lbs'][self.dist]:
        repos = config['lbs'][self.dist][str(self.container.release)]['repos']
        for repo in repos:
          self.container.executeshell("cd " + rootfs + "/etc/yum.repos.d/; wget " + repo);

    # now install required packages
    specfile=rootfs + "/root/" + "lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetSpecFilename()
    if os.path.isfile(specfile):
      for line in open(specfile):
        if line.startswith("BuildRequires: "):
          if line.count(",") > 0:
            packagesWithVersions=line[len("BuildRequires: "):].split(",")
          else:
            packagesWithVersions=line[len("BuildRequires: "):].split()
          packages=[]
          ignoreNext=False
          for word in packagesWithVersions:
            if not ignoreNext:
              # filter >= 3.0, only use package names
              if word[0] == '>' or word[0] == '<' or word[0] == '=':
                ignoreNext=True
              else:
                packages.append(word.strip())
            else:
              ignoreNext=False
          if not self.run("yum -y install rpm-build " + " ".join(packages)):
            return self.output

  def BuildPackage(self, LBSUrl):
    rootfs=self.container.getrootfs()
    specfile=rootfs + "/root/" + "lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetSpecFilename()
    if os.path.isfile(specfile):
      self.run("cp lbs-" + self.projectname + "/" + self.packagename + "/" + self.packagename + ".spec rpmbuild/SPECS")

      # copy patches, and other files (eg. env.sh for mono-opt)
      self.run("cp lbs-" + self.projectname + "/" + self.packagename + "/* rpmbuild/SOURCES")

      # move the sources that have been downloaded according to instructions in config.yml. see BuildHelper::DownloadSources
      self.run("mv sources/* rpmbuild/SOURCES")

      # TODO: build counter for automatically increasing the release number?
      self.run("sed -i -e 's/Release: %{release}/Release: 99/g' rpmbuild/SPECS/" + self.packagename + ".spec")
      if not self.run("rpmbuild -ba rpmbuild/SPECS/" + self.packagename + ".spec"):
        return self.output

      # add result to repo
      self.run("mkdir -p ~/repo/src")
      self.run("cp ~/rpmbuild/SRPMS/*.src.rpm ~/repo/src")
      self.run("cp -R ~/rpmbuild/RPMS/* ~/repo")
      repoFileContent="[lbs-"+self.username + "-"+self.projectname +"]\n"
      repoFileContent+="name=LBS-"+self.username + "-"+self.projectname +"\n"
      repoFileContent+="baseurl=" + LBSUrl + "/repos/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + self.container.release + "\n"
      repoFileContent+="enabled=1\n"
      repoFileContent+="gpgcheck=0\n"
      with open(rootfs + "/root/lbs-"+self.username + "-"+self.projectname +".repo", 'w') as f:
        f.write(repoFileContent)
      if not self.run("cd repo && createrepo ."):
        return self.output
      self.run("cp /root/lbs-"+self.username + "-"+self.projectname +".repo repo")

  def RunTests(self):
    if not self.run("cd lbs-" + self.projectname + "/" + self.packagename + " && ./runtests.sh"):
      return self.output

  def GetRepoInstructions(self, config, buildtarget):
    buildtarget = buildtarget.split("/")
    result = "cd /etc/yum.repos.d/\n"
    result += "wget " + config["lbs"]["LBSUrl"] + "/repos/" + self.username + "/" + self.projectname + "/" + buildtarget[0] + "/" + buildtarget[1] + "/lbs-"+self.username + "-"+self.projectname +".repo\n"
    # packagename: name of spec file, without .spec at the end
    result += "apt-get install " + self.GetSpecFilename()[:-5]
    return result
