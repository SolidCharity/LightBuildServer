#!/usr/bin/env python3
"""BuildHelper: abstract base class for various builders"""

# Copyright (c) 2014-2020 Timotheus Pokorra

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
import Config
from Database import Database

class BuildHelper:
  'abstract base class for BuildHelper implementations for the various Linux Distributions'

  def __init__(self, container, username, projectname, packagename, branchname):
    self.container = container
    self.fedora = 0
    self.suse_version = 0
    self.rhel = 0
    self.release = 0
    if container is not None:
      self.arch = container.arch
      self.release = container.release
      self.rhel = self.release
    self.username = username
    self.projectname = projectname
    self.packagename = packagename
    self.branchname = branchname
    self.config = Config.LoadConfig()
    self.pathSrc=self.config['lbs']['GitSrcPath']+"/"+self.username

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
    file = self.pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/config.yml"
    if os.path.isfile(file):
      stream = open(file, 'r')
      pkgconfig = yaml.load(stream)
      for url in pkgconfig['lbs']['source']['download']:
        filename="`basename " + url + "`"
        if isinstance(pkgconfig['lbs']['source']['download'], dict):
          filename=url
          url=pkgconfig['lbs']['source']['download'][url]
        self.run("mkdir -p /root/sources")
        if not self.run("curl -L " + url + " -o /root/sources/" + filename):
          return False
    return True

  def InstallRepositories(self, DownloadUrl):
    print("not implemented")
    return True

  def InstallRequiredPackages(self):
    print("not implemented")
    return True

  def BuildPackage(self):
    print("not implemented")
    return True

  def SetupEnvironment(self, branchname):
    path="lbs-" + self.projectname + "/" + self.packagename
    if not os.path.isdir(self.pathSrc + "/" + path):
      self.log("cannot find path " + path)
      return False
    setupfile=path + "/setup.sh"
    if os.path.isfile(self.pathSrc + "/" + setupfile):
      if not self.run("cd " + path + "; HOSTNAME='" + container.hostname + "' ./setup.sh " + branchname):
        return False
    return True

  def DisableOutgoingNetwork(self):
    if not self.run("mydevice=\`ip -o route get to 8.8.8.8 | awk '{ print \$5 }'\`; myip=\`ip -o route get to 8.8.8.8 | awk '{ print \$7 }'\`; ip route add \$myip dev \$mydevice"):
      return False
    return True

  def GetWinInstructions(self, DownloadUrl, buildtarget, branchname):
    return None

  def GetSrcInstructions(self, DownloadUrl, buildtarget):
    return "not implemented"

  def GetRepoInstructions(self, DownloadUrl, buildtarget):
    return "not implemented"

  def CreateRepoFile(self):
    return "not implemented"
 
  def GetDependanciesAndProvides(self, lxcdistro, lxcrelease, lxcarch):
    print("not implemented")
    return False

  def StorePackageDependancies(self, packages, builddepends):
    con = Database(self.config)
    for package in packages:
      # find the package id
      cursor = con.execute("SELECT id FROM package WHERE username = ? AND projectname = ? AND packagename = ? AND branchname = ?", (self.username, self.projectname, package, self.branchname))
      row = cursor.fetchone()
      if row is None:
        print("There is no package " + package)
        continue
      packageid = row['id']
      # delete all dependancies
      stmt = "DELETE FROM packagedependancy WHERE dependantpackage = ?"
      cursor = con.execute(stmt, (packageid,))
      con.commit()
      for requiredpackage in builddepends[package]:
        # find required package id
        cursor = con.execute("SELECT id FROM package WHERE username = ? AND projectname = ? AND packagename = ? AND branchname = ?", (self.username, self.projectname, requiredpackage, self.branchname))
        row = cursor.fetchone()
        if row is not None:
          requiredpackageid = row['id']
          stmt = "INSERT INTO packagedependancy (dependantpackage, requiredpackage) VALUES (?, ?)"
          cursor = con.execute(stmt, (packageid, requiredpackageid))
          con.commit()
    con.close()
    return

  def CalculatePackageOrder(self, lxcdistro, lxcrelease, lxcarch):
    result = deque()
    self.release = lxcrelease
    self.arch = lxcarch
    userconfig=self.config['lbs']['Users'][self.username]
    projectconfig=userconfig['Projects'][self.projectname]
    if 'Packages' in projectconfig:
      packages = userconfig['Projects'][self.projectname]['Packages']
    else:
      packages = userconfig['Projects'][self.projectname]
    unsorted={}
    builddepends={}
    depends={}
    providedby={}
    deliverables={}
    for package in packages:
      excludeDistro=False
      if packages[package] is not None and "ExcludeDistros" in packages[package]:
        for exclude in packages[package]['ExcludeDistros']:
          if (lxcdistro + "/" + lxcrelease + "/" + lxcarch).startswith(exclude):
            excludeDistro = True
      includeDistro=True
      if packages[package] is not None and "Distros" in packages[package]:
        includeDistro=False
        for incl in packages[package]['Distros']:
          if (lxcdistro + "/" + lxcrelease + "/" + lxcarch) == incl:
            includeDistro=True
      if includeDistro and not excludeDistro:
        self.packagename=package
        (builddepends[package],deliverables[package]) = self.GetDependanciesAndProvides()
        for p in deliverables[package]:
          unsorted[p] = 1
          depends[p] = deliverables[package][p]['requires']
          for pv in deliverables[package][p]['provides']:
            providedby[pv] = package
        if not package in unsorted:
          unsorted[package] = 1
        # useful for debugging:
        if False:
          print( package + " builddepends on: ")
          for p in builddepends[package]:
            print("   " + p)
          print( package + " produces these packages: ")
          for p1 in deliverables[package]:
            for p in deliverables[package][p1]['provides']:
              print("   " + p + " which requires during installation:")
              for d in depends[p1]:
                print("      " + d)

    while len(unsorted) > 0:
      nextPackage = None
      for package in sorted(unsorted):
        if package in packages and nextPackage is None:
          missingRequirement=False
          # check that this package does not require a package that is in unsorted
          if package in depends:
            for dep in depends[package]:
              if dep in providedby:
                pv = providedby[dep]
                if pv != package and pv in unsorted and pv in packages:
                  missingRequirement=True
          if package in builddepends:
            for dep in builddepends[package]:
              if dep in providedby:
                pv = providedby[dep]
                if pv != package and pv in unsorted and pv in packages:
                  missingRequirement=True
          if not missingRequirement:
            nextPackage=package
      if nextPackage == None:
        # problem: circular dependancy
        print ("circular dependancy, remaining packages: ")
        for package in unsorted:
          if not package in packages:
            continue
          print(package)
          print(" build requires: ")
          if package in builddepends:
            for dep in builddepends[package]:
              if dep in providedby:
                pv = providedby[dep]
                if pv != package and pv in unsorted:
                  print("   " + pv)
          print(" install requires: ")
          if package in depends:
            for dep in depends[package]:
              if dep in providedby:
                pv = providedby[dep]
                if pv != package and pv in unsorted:
                  print("   " + pv)
        return None
      result.append(nextPackage)
      for p in deliverables[nextPackage]:
        if p in unsorted:
          del unsorted[p]
      if nextPackage in unsorted:
        del unsorted[nextPackage]

    #print(result)
    #raise Exception("test")

    self.StorePackageDependancies(packages, builddepends)

    return result
