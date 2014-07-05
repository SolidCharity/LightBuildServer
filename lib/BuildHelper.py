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
    return self.container.executeInContainer(command)

  def PrepareMachineBeforeStart(self):
    print("not implemented")
    return True

  def PrepareMachineAfterStart(self):
    print("not implemented")
    return True

  def PrepareForBuilding(self):
    print("not implemented")
    return True

  def DownloadSources(self):
    # parse config.yml file and download the sources
    # unpacking and moving to the right place depends on the distro
    pathSrc="/var/lib/lbs/src/"+self.username
    file = pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/config.yml"
    if os.path.isfile(file):
      stream = open(file, 'r')
      config = yaml.load(stream)
      for url in config['lbs']['source']['download']:
        self.run("mkdir -p /root/sources")
        self.run("curl -L " + url + " -o /root/sources/`basename " + url + "`")
    return True

  def InstallRequiredPackages(self, LBSUrl):
    print("not implemented")
    return True

  def BuildPackage(self, LBSUrl):
    print("not implemented")
    return True

  def SetupEnvironment(self, branchname):
    pathSrc="/var/lib/lbs/src/"+self.username
    setupfile="lbs-" + self.projectname + "/" + self.packagename + "/setup.sh"
    if os.path.isfile(pathSrc + "/" + setupfile):
      if not self.run("cd " + os.path.dirname(setupfile) + "; ./setup.sh " + branchname):
        return False
    return True

  def GetRepoInstructions(self, LBSUrl, buildtarget):
    return "not implemented"
