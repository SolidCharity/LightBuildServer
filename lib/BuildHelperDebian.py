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

  def PrepareMachineBeforeStart(self):
    print("not implemented")

  def PrepareForBuilding(self):
    if not self.run("apt-get update"):
      return self.output
    if not self.run("apt-get -y upgrade"):
      return self.output
    if not self.run("apt-get -y install wget build-essential ca-certificates locales"):
      return self.output
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

    # TODO now install required packages

  def BuildPackage(self):
    rootfs=self.container.getrootfs()
    buildfile="lbs-" + self.projectname + "/" + self.packagename + "/debian.build"
    buildfileWithRoot=rootfs + "/root/" + buildfile
    if os.path.isfile(buildfileWithRoot):
      if not self.run("cd `dirname " + buildfile + "`; ./debian.build"):
        return self.output

  def RunTests(self):
    if not self.run("cd lbs-" + self.projectname + "/" + self.packagename + " && ./runtests.sh"):
      return self.output
