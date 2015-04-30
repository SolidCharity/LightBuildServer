#!/usr/bin/env python3
"""BuildHelper for Debian: knows how to build packages for Debian"""

# Copyright (c) 2014-2015 Timotheus Pokorra

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
import tempfile
import shutil
import re
import os
import glob
import yaml

class BuildHelperDebian(BuildHelper):
  'build packages for Debian'

  def __init__(self, container, username, projectname, packagename):
    self.dist='debian'
    BuildHelper.__init__(self, container, username, projectname, packagename)

  def PrepareMachineBeforeStart(self):
    print("not implemented")
    return True

  def PrepareForBuilding(self):
    if not self.run("apt-get update"):
      return False
    if not self.run("apt-get -y upgrade"):
      return False
    if not self.run("apt-get -y install build-essential ca-certificates iptables curl apt-transport-https dpkg-sig reprepro wget"):
      #apt-utils
      return False
    # make sure we have a fully qualified hostname
    self.run("echo '127.0.0.1     " + self.container.name + "' > tmp; cat /etc/hosts >> tmp; mv tmp /etc/hosts")
    return True

  def GetDscFilename(self):
    pathSrc="/var/lib/lbs/src/"+self.username
    if os.path.isdir(pathSrc + "/lbs-" + self.projectname + "/" + self.packagename):
      for file in os.listdir(pathSrc + "/lbs-" + self.projectname + "/" + self.packagename):
        if file.endswith(".dsc") and self.packagename.startswith(file.split('.')[0]):
          return file
    return self.packagename + ".dsc"

  def InstallRepositories(self, DownloadUrl):
    # first install required repos
    pathSrc="/var/lib/lbs/src/"+self.username
    configfile=pathSrc + "/lbs-" + self.projectname + "/config.yml"
    if os.path.isfile(configfile):
      stream = open(configfile, 'r')
      config = yaml.load(stream)
      if self.dist in config['lbs'] and self.container.release in config['lbs'][self.dist]:
        repos = config['lbs']['debian'][self.container.release]['repos']
        for repo in repos:
          self.run("cd /etc/apt/sources.list.d/; echo '" + repos[repo] + " ' > " + repo + ".list")
        if 'keys' in config['lbs'][self.dist][str(self.release)]:
          keys = config['lbs'][self.dist][str(self.release)]['keys']
          for key in keys:
            if not self.run("wget -O Release.key '" + key + "' && apt-key add Release.key && rm -rf Release.key"):
              return False

    # install own repo as well if it exists
    repofile="/var/www/repos/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + self.container.release + "/Packages.gz"
    if os.path.isfile(repofile):
      repopath=DownloadUrl + "/repos/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + self.container.release + "/"
      self.run("cd /etc/apt/sources.list.d/; echo 'deb " + repopath + " /' > lbs-" + self.username + "-" + self.projectname + ".list")
    repofile="/var/www/repos/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + self.container.release + "/db/packages.db"
    if os.path.isfile(repofile):
      repopath=DownloadUrl + "/repos/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + self.container.release
      self.run("cd /etc/apt/sources.list.d/; echo 'deb " + repopath + " " + self.container.release + " main' > lbs-" + self.username + "-" + self.projectname + ".list")

    # update the repository information
    self.run("apt-get update")
    return True

  def InstallRequiredPackages(self):
    pathSrc="/var/lib/lbs/src/"+self.username
    # now install required packages
    dscfile=pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetDscFilename()
    packages=None
    # force-yes for packages from our own repository, they are not signed at the moment
    aptInstallFlags="--force-yes "
    nextLineBuildDepends=False
    if os.path.isfile(dscfile):
      for line in open(dscfile):
        packagesWithVersions=None
        if line.startswith("Build-Depends:"):
          if not packages is None:
            if not self.run("apt-get install -y " + aptInstallFlags + " ".join(packages)):
              return False
          packages=[]
          packagesWithVersions=line[len("Build-Depends:"):].strip().split(',')
        if nextLineBuildDepends:
          packagesWithVersions=line.strip().split(',')
        if packagesWithVersions is not None:
          nextLineBuildDepends=line.strip().endswith(",") or line.strip().endswith(":")
          for word in packagesWithVersions:
              if "|" in word:
                onePackageSucceeded=False
                # try each of the packages, ignore failure
                optionalPackages=word.strip().split('|')
                for word2 in optionalPackages:
                  if onePackageSucceeded == False and len(word2.strip()) > 0:
                     onePackageSucceeded = self.run("apt-get install -y " + aptInstallFlags + word2.split()[0])
                if not onePackageSucceeded:
                  self.logger.print("cannot install at least one of these packages: " + word)
                  return False
              else:
                # only use package names, ignore space (>= 9)
                if len(word.strip()) > 0:
                  packages.append(word.split()[0])
      if not packages is None:
        if not self.run("apt-get install -y " + aptInstallFlags + " ".join(packages)):
         return False
    return True

  def BuildPackage(self, config):
    DownloadUrl = config['lbs']['DownloadUrl']
    pathSrc="/var/lib/lbs/src/"+self.username
    dscfile=pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetDscFilename()
    if os.path.isfile(dscfile):
      # unpack the sources
      # the sources have been downloaded according to instructions in config.yml. see BuildHelper::DownloadSources
      pathPackageSrc="/root/lbs-" + self.projectname + "/" + self.packagename
      self.run("cp /root/sources/* " + pathPackageSrc)
      self.run("rm -Rf tmpSource && mkdir tmpSource")
      self.run("for file in " + pathPackageSrc + "/*.tar.gz; do if [ -f \$file ]; then cd tmpSource && tar xzf \$file;rm " + pathPackageSrc + "/\`basename \$file\`; fi; done")
      self.run("for file in /root/sources/*.tar.xz; do if [ -f \$file ]; then cd tmpSource && tar xf \$file; rm " + pathPackageSrc + "/\`basename \$file\`; fi; done")
      self.run("for file in /root/sources/*.tar.gz; do if [ -f \$file ]; then cd tmpSource && tar xzf \$file;rm " + pathPackageSrc + "/\`basename \$file\`; fi; done")
      self.run("for file in /root/sources/*.tar.bz2; do if [ -f \$file ]; then cd tmpSource && tar xjf \$file; rm " + pathPackageSrc + "/\`basename \$file\`; fi; done")
      self.run("for dir in tmpSource/*; do if [ -d \$dir ]; then mv \$dir/* lbs-" + self.projectname + "/" + self.packagename + "; mv \$dir/.* lbs-" + self.projectname + "/" + self.packagename + "; fi; done")
      self.run("rm -Rf tmpSource")

      # read version from dsc file, that is on the build server
      # (setup.sh might overwrite the version number...)
      temppath = tempfile.mkdtemp()
      self.container.rsyncContainerGet("/root/lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetDscFilename(), temppath)
      buildversion = "1.0.0"
      for line in open(temppath + "/" + self.GetDscFilename()):
        if line.startswith("Version: "):
          buildversion=line[len("Version: "):].strip()
          if buildversion.find("-") > 0:
            buildversion=buildversion[:buildversion.find("-")]
          break
      shutil.rmtree(temppath)

      # build counter for automatically increasing the release number
      buildnumber=0
      arch=self.arch

      debfiles=[]
      myPath = self.username + "/" + self.projectname
      if 'Secret' in config['lbs']['Users'][self.username]:
        myPath = self.username + "/" + config['lbs']['Users'][self.username]['Secret'] + "/" + self.projectname
      repopath="/var/www/repos/" + myPath + "/" + self.dist + "/" + self.container.release + "/"
      if os.path.isdir(repopath + "/" + arch + "/binary"):
        for file in os.listdir(repopath + "/" + arch + "/binary"):
          # TODO use GetDscFilename, without dsc, instead of packagename
          if file.startswith(self.packagename + "_" + buildversion + "-") and file.endswith("_" + arch + ".deb"):
            try:	
              oldnumber=int(file[len(self.packagename + "_" + buildversion + "-"):-1*len("_" + arch + ".deb")])
              debfiles.append(str(oldnumber).zfill(6) + ":" + file)
              if oldnumber >= buildnumber:
                buildnumber = oldnumber + 1
            except ValueError:
              # ignore errors if the package version contains more than 0.1.0-0
              # avoiding ValueError: invalid literal for int() with base 10
              oldnumber=0
      self.run("sed -i -e 's/%{release}/" + str(buildnumber) + "/g' lbs-" + self.projectname + "/" + self.packagename + "/" + self.packagename + ".dsc")
      self.run("sed -i -e 's/%{release}/" + str(buildnumber) + "/g' lbs-" + self.projectname + "/" + self.packagename + "/debian/changelog")

      if not self.run("cd lbs-" + self.projectname + "/" + self.packagename + " && dpkg-buildpackage -rfakeroot -uc -b"):
        return False

      # import the private key for signing the package if the file privateLBSkey exists
      sshContainerPath = config['lbs']['SSHContainerPath']
      if os.path.isfile(sshContainerPath + '/' + self.username + '/' + self.projectname + '/privateLBSkey'):
        self.run("gpg --import < ~/.ssh/privateLBSkey; mkdir -p repo/conf; cp .ssh/distributions repo/conf")
        if not self.run("cd lbs-" + self.projectname + "; dpkg-sig --sign builder *.deb"):
          return False
        if not self.run("cd repo; for f in ~/lbs-" + self.projectname + "/*.deb; do pkgname=\`basename \$f\`; pkgname=\`echo \$pkgname | awk -F '_' '{print \$1}'\`; reprepro remove " + self.container.release + " \$pkgname; reprepro includedeb " + self.container.release + " ~/lbs-" + self.projectname + "/\`basename \$f\`; done"):
          return False
        self.run("rm -Rf repo/conf")
      else:
        # add result to repo
        self.run("mkdir -p ~/repo/" + self.container.arch + "/binary")
        self.run("cp lbs-" + self.projectname + "/*.deb repo/" + self.container.arch + "/binary")
        if not self.run("cd repo && dpkg-scanpackages -m . /dev/null | gzip -9c > Packages.gz"):
          return False

    return True

  def GetSrcInstructions(self, config, DownloadUrl, buildtarget):
    return None

  def GetRepoInstructions(self, config, DownloadUrl, buildtarget):
    buildtarget = buildtarget.split("/")

    keyinstructions = ""

    # check if there is such a package at all
    checkfile="/var/www/repos/" + self.username + "/" + self.projectname + "/" + self.dist + "/*/*/binary/" + self.GetDscFilename()[:-4] + "*"
    if glob.glob(checkfile):
      path = "/ /"
    else:
      # repo has been created with reprepro
      checkfile="/var/www/repos/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + buildtarget[1] + "/pool/main/*/*/" + self.GetDscFilename()[:-4].lower() + "*"
      if glob.glob(checkfile):
        path = " " + buildtarget[1] + " main"
        if 'PublicKey' in config['lbs']['Users'][self.username]['Projects'][self.projectname]:
          keyinstructions += "wget -O Release.key '" + config['lbs']['Users'][self.username]['Projects'][self.projectname]['PublicKey'] + "'\n"
          keyinstructions += "apt-key add Release.key; rm -rf Release.key\n"
      else:
        return None
   
    result = ""
    result += "apt-get install apt-transport-https\n"
    result += keyinstructions
    result += "echo 'deb " + DownloadUrl + "/repos/" + self.username + "/" 
    if 'Secret' in config['lbs']['Users'][self.username]:
        result += config['lbs']['Users'][self.username]['Secret'] + "/"
    result += self.projectname + "/" + buildtarget[0] + "/" + buildtarget[1] + path + "' >> /etc/apt/sources.list\n"
    result += "apt-get update\n"
    # packagename: name of dsc file, without .dsc at the end
    result += "apt-get install " + self.GetDscFilename()[:-4].lower()

    return result

  def GetDependanciesAndProvides(self):
    pathSrc="/var/lib/lbs/src/"+self.username
    dscfile=pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetDscFilename()
    builddepends=[]
    provides={}
    if os.path.isfile(dscfile):
      nextLineBuildDepends=False
      for line in open(dscfile):
        packagesWithVersions=None
        if line.startswith("Build-Depends:"):
          packagesWithVersions=line[len("Build-Depends:"):].strip().split(',')
        if nextLineBuildDepends:
          packagesWithVersions=line.strip().split(',')
        if packagesWithVersions is not None:
          nextLineBuildDepends=line.strip().endswith(",") or line.strip().endswith(":")
          for word in packagesWithVersions:
              if "|" in word:
                optionalPackages=word.strip().split('|')
                for word2 in optionalPackages:
                  if len(word2.strip()) > 0:
                     builddepends.append(word2.split()[0])
              else:
                # only use package names, ignore space (>= 9)
                if len(word.strip()) > 0:
                  builddepends.append(word.split()[0])

    controlfile=pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/debian/control"
    recentpackagename=self.packagename
    nextLineDepends=False
    if os.path.isfile(controlfile):
      for line in open(controlfile):
        packagesWithVersions=None
        if line.lower().startswith("package:"):
          recentpackagename=line[len("package:"):].strip()
          provides[recentpackagename] = []
        elif line.lower().startswith("depends:"):
          packagesWithVersions=line[len("depends:"):].strip().split(',')
        if nextLineDepends:
          packagesWithVersions=line.strip().split(',')
        if packagesWithVersions is not None:
          nextLineDepends=line.strip().endswith(",") or line.strip().endswith(":")
          for word in packagesWithVersions:
            for w2 in word.split('|'):
              if len(w2.strip()) > 0:
                provides[recentpackagename].append(w2.split()[0].strip())

    return (builddepends, provides)

