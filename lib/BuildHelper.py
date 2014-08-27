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
from collections import deque

class BuildHelper:
  'abstract base class for BuildHelper implementations for the various Linux Distributions'

  def __init__(self, container, pathInsideContainer, username, projectname, packagename):
    self.container = container
    self.fedora = 0
    self.suse_version = 0
    self.rhel = 0
    self.release = 0
    if container is not None:
      self.arch = container.arch
      self.release = container.release
      self.rhel = self.release
    self.pathInsideContainer = pathInsideContainer
    self.username = username
    self.projectname = projectname
    self.packagename = packagename

  def log(self, message):
    if self.container is not None:
      self.container.logger.print(message);

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

  def BuildPackage(self, config):
    print("not implemented")
    return True

  def SetupEnvironment(self, branchname):
    pathSrc="/var/lib/lbs/src/"+self.username
    setupfile="lbs-" + self.projectname + "/" + self.packagename + "/setup.sh"
    if os.path.isfile(pathSrc + "/" + setupfile):
      if not self.run("cd " + os.path.dirname(setupfile) + "; ./setup.sh " + branchname):
        return False
    return True

  def DisableOutgoingNetwork(self):
    if not self.run("iptables -P OUTPUT DROP && iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT && iptables -A OUTPUT -j DROP"):
      return False
    return True

  def GetRepoInstructions(self, LBSUrl, buildtarget):
    return "not implemented"
 
  def GetDependanciesAndProvides(self, config, lxcdistro, lxcrelease, lxcarch):
    print("not implemented")
    return False

  def CalculatePackageOrder(self, config, lxcdistro, lxcrelease, lxcarch):
    result = deque()
    self.release = lxcrelease
    self.arch = lxcarch
    userconfig=config['lbs']['Users'][self.username]
    projectconfig=userconfig['Projects'][self.projectname]
    if 'Packages' in projectconfig:
      packages = userconfig['Projects'][self.projectname]['Packages']
    else:
      packages = userconfig['Projects'][self.projectname]
    unsorted={}
    depends={}
    provides={}
    for package in packages:
      excludeDistro=False
      if packages[package] is not None and "ExcludeDistros" in packages[package]:
        for exclude in packages[package]['ExcludeDistros']:
          if (lxcdistro + "/" + lxcrelease + "/" + lxcarch).startswith(exclude):
            excludeDistro = True
      if not excludeDistro:
        unsorted[package] = 1
        self.packagename=package
        (depends[package],provides[package]) = self.GetDependanciesAndProvides()

    loopCounter = len(unsorted)
    for i in range(1, loopCounter):
      nextPackage = None
      for package in unsorted:
        if nextPackage is None:
          missingRequirement=False
          # check that this package does not require a package that is in unsorted
          for dep in depends[package]:
            if dep in unsorted:
              missingRequirement=True
          if not missingRequirement:
            nextPackage=package
      if nextPackage == None and len(unsorted) > 0:
        # problem: circular dependancy
        return None
      result.append(package)
      del unsorted[package]

    return result
