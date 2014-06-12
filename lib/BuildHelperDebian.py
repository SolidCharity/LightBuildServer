#!/usr/bin/env python3
"""BuildHelper for Debian: knows how to build packages for Debian"""

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

class BuildHelperDebian(BuildHelper):
  'build packages for Debian'

  def __init__(self, container, pathInsideContainer, username, projectname, packagename):
    self.dist='debian'
    BuildHelper.__init__(self, container, pathInsideContainer, username, projectname, packagename)

  def PrepareMachineBeforeStart(self):
    print("not implemented")

  def PrepareForBuilding(self):
    if not self.run("apt-get update"):
      return self.output
    if not self.run("apt-get -y upgrade"):
      return self.output
    if not self.run("apt-get -y install build-essential ca-certificates"):
      return self.output
    # make sure we have a fully qualified hostname
    self.run("echo '127.0.0.1     " + self.container.name + "' > tmp; cat /etc/hosts >> tmp; mv tmp /etc/hosts")

  def GetDscFilename(self):
    pathSrc="/var/lib/lbs/src/"+self.username
    for file in os.listdir(pathSrc + "/lbs-" + self.projectname + "/" + self.packagename):
      if file.endswith(".dsc") and self.packagename.startswith(file.split('.')[0]):
        return file
    return self.packagename + ".dsc"

  def InstallRequiredPackages(self):
    rootfs=self.container.getrootfs()

    # first install required repos
    configfile=rootfs + "/root/lbs-" + self.projectname + "/config.yml"
    if os.path.isfile(configfile):
      stream = open(configfile, 'r')
      config = yaml.load(stream)
      if self.dist in config['lbs'] and str(self.container.release) in config['lbs'][self.dist]:
        repos = config['lbs']['debian'][self.container.release]['repos']
        for repo in repos:
          self.run("cd /etc/apt/sources.list.d/; echo '" + repos[repo] + " ' > " + repo + ".list")
        self.run("apt-get update")

    # now install required packages
    dscfile=rootfs + "/root/" + "lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetDscFilename()
    self.run("echo " + dscfile)
    if os.path.isfile(dscfile):
      for line in open(dscfile):
        if line.startswith("Build-Depends: "):
          packagesWithVersions=line[len("Build-Depends: "):].split(',')
          packages=[]
          for word in packagesWithVersions:
              # only use package names, ignore space (>= 9)
              packages.append(word.split()[0])
          if not self.run("apt-get install -y " + " ".join(packages)):
            return self.output

  def BuildPackage(self, LBSUrl):
    rootfs=self.container.getrootfs()
    dscfile=rootfs + "/root/" + "lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetDscFilename()
    if os.path.isfile(dscfile):
      # unpack the sources
      # the sources have been downloaded according to instructions in config.yml. see BuildHelper::DownloadSources
      SourcePath=rootfs + "/root/sources"
      for file in os.listdir(SourcePath):
        if file.endswith(".tar.xz") or file.endswith(".tar.gz") or file.endswith(".tar.bz2"):
          extractCmd="tar xf"
          if file.endswith(".tar.gz"):
            extractCmd="tar xzf"
          elif file.endswith(".tar.bz2"):
            extractCmd="tar xjf"
          self.run("mkdir tmpSource")
          if not self.run("cd tmpSource && " + extractCmd + " ../sources/" + file):
            return self.output
          for dir in os.listdir(rootfs + "/root/tmpSource"):
            if os.path.isdir(rootfs + "/root/tmpSource/" + dir):
              self.run("mv tmpSource/" + dir + "/* lbs-" + self.projectname + "/" + self.packagename)
          self.run("rm -Rf tmpSource")
        else:
          self.run("mv sources/" + file + " lbs-" + self.projectname + "/" + self.packagename)

      # TODO: build counter for automatically increasing the release number?
      if not self.run("cd lbs-" + self.projectname + "/" + self.packagename + " && dpkg-buildpackage -rfakeroot -uc -b"):
        return self.output

      # add result to repo
      self.run("mkdir -p ~/repo/" + self.container.arch + "/binary")
      self.run("cp lbs-" + self.projectname + "/*.deb repo/" + self.container.arch + "/binary")
      if not self.run("cd repo && dpkg-scanpackages . /dev/null | gzip -9c > Packages.gz"):
        return self.output

  def RunTests(self):
    if not self.run("cd lbs-" + self.projectname + "/" + self.packagename + " && ./runtests.sh"):
      return self.output

  def GetRepoInstructions(self, config, buildtarget):
    buildtarget = buildtarget.split("/")
    result = "echo 'deb " + config["lbs"]["LBSUrl"] + "/repos/" + self.username + "/" + self.projectname + "/" + buildtarget[0] + "/" + buildtarget[1] + "/ /' >> /etc/apt/sources.list\n"
    result += "apt-get update\n"
    # packagename: name of dsc file, without .dsc at the end
    result += "apt-get install " + self.GetDscFilename()[:-4]
    return result
