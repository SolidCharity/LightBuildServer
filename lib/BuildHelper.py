#!/usr/bin/env python3
"""BuildHelper: abstract base class for various builders"""

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
import yaml
import os.path

class BuildHelper:
  'abstract base class for BuildHelper implementations for the various Linux Distributions'

  def __init__(self, container, pathInsideContainer, username, projectname, packagename):
    self.container = container
    self.pathInsideContainer = pathInsideContainer
    self.username = username
    self.projectname = projectname
    self.packagename = packagename

  def run(self, command):
    result = self.container.execute(command)
    # we do not handle self.container.output here
    return result

  def PrepareMachineBeforeStart(self):
    print("not implemented")

  def PrepareForBuilding(self):
    print("not implemented")

  def DownloadSources(self):
    # parse config.yml file and download the sources
    # unpacking and moving to the right place depends on the distro
    rootfs=self.container.getrootfs()
    file = rootfs + "/root/lbs-" + self.projectname + "/" + self.packagename + "/config.yml"
    if os.path.isfile(file):
      stream = open(file, 'r')
      config = yaml.load(stream)
      for url in config['lbs']['source']['download']:
        self.container.executeshell("mkdir -p " + rootfs + "/root/sources")
        self.container.executeshell("wget -O " + rootfs + "/root/sources/`basename " + url + "` " + url)

  def InstallRequiredPackages(self):
    print("not implemented")

  def BuildPackage(self):
    print("not implemented")

  def SetupEnvironment(self):
    rootfs=self.container.getrootfs()
    setupfile="lbs-" + self.projectname + "/" + self.packagename + "/setup.sh"
    setupfileWithRoot=rootfs + "/root/" + setupfile
    if os.path.isfile(setupfileWithRoot):
      if not self.run("cd `dirname " + setupfile + "`; ./setup.sh"):
        return self.output

  def RunTests(self):
    print("not implemented")

  def GetRepoInstructions(self, config, buildtarget):
    print("not implemented")
