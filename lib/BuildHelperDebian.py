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

  def __init__(self, container, pathInsideContainer, projectname, packagename):
    self.dist='debian'
    self.locale="export LANGUAGE=en_US.UTF-8; export LANG=en_US.UTF-8; export LC_ALL=en_US.UTF-8; "
    BuildHelper.__init__(self, container, pathInsideContainer, projectname, packagename)

  def PrepareMachineBeforeStart(self):
    print("not implemented")

  def PrepareForBuilding(self):
    if not self.run("apt-get update"):
      return self.output
    if not self.run("apt-get -y upgrade"):
      return self.output
    if not self.run("apt-get -y install build-essential ca-certificates locales"):
      return self.output
    # fix problem: Perl warning Setting locale failed
    self.run(self.locale + " locale-gen en_US.UTF-8")
    # make sure we have a fully qualified hostname
    self.run("echo '127.0.0.1     " + self.container.name + "' > tmp; cat /etc/hosts >> tmp; mv tmp /etc/hosts")

  def InstallRequiredPackages(self):
    rootfs=self.container.getrootfs()

    # first install required repos
    configfile=rootfs + "/root/lbs-" + self.projectname + "/config.yml"
    if os.path.isfile(configfile):
      stream = open(configfile, 'r')
      config = yaml.load(stream)
      repos = config['lbs']['debian'][self.container.release]['repos']
      for repo in repos:
        self.run("cd /etc/apt/sources.list.d/; echo '" + repos[repo] + " ' > " + repo + ".list")
      self.run("apt-get update")

    # now install required packages
    dscfile=rootfs + "/root/" + "lbs-" + self.projectname + "/" + self.packagename + "/" + self.packagename + ".dsc"
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

  def BuildPackage(self):
    rootfs=self.container.getrootfs()
    dscfile=rootfs + "/root/" + "lbs-" + self.projectname + "/" + self.packagename + "/" + self.packagename + ".dsc"
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
      if not self.run(self.locale + " cd lbs-" + self.projectname + "/" + self.packagename + " && dpkg-buildpackage -rfakeroot -uc -b"):
        return self.output

      # add result to repo
      self.run("mkdir -p ~/repo/binary")
      self.run("cp lbs-" + self.projectname + "/*.deb repo/binary")
      if not self.run(self.locale + " cd repo && dpkg-scanpackages binary  /dev/null | gzip -9c > binary/Packages.gz"):
        return self.output

  def RunTests(self):
    if not self.run("cd lbs-" + self.projectname + "/" + self.packagename + " && ./runtests.sh"):
      return self.output
