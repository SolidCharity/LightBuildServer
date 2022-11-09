#!/usr/bin/env python3
"""BuildHelper for Debian: knows how to build packages for Debian"""

# Copyright (c) 2014-2022 Timotheus Pokorra

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

import tempfile
import shutil
import re
import os
import glob
import yaml
from pathlib import Path

from django.conf import settings

from lib.BuildHelper import BuildHelper
from projects.models import Project

class BuildHelperDebian(BuildHelper):
  'build packages for Debian'

  def __init__(self, container, build):
    self.dist='debian'
    BuildHelper.__init__(self, container, build)

  def PrepareMachineBeforeStart(self):
    print("not implemented")
    return True

  def PrepareForBuilding(self):
    if not self.run("apt-get update"):
      return False
    if not self.run("DEBIAN_FRONTEND=noninteractive apt-get -y upgrade"):
      return False
    if not self.run("apt-get -y install build-essential ca-certificates iptables curl apt-transport-https dpkg-sig reprepro wget rsync devscripts equivs iproute2"):
      #apt-utils
      return False
    # make sure we have a fully qualified hostname
    self.run("echo '127.0.0.1     " + self.container.containername + "' > tmp; cat /etc/hosts >> tmp; mv tmp /etc/hosts")
    return True

  def GetDscFilename(self):
    filename = self.packagename + ".dsc"
    path = self.pathSrc + "/lbs-" + self.projectname + "/" + self.packagename
    if os.path.isdir(path):
      for file in os.listdir(path):
        if file.endswith(".dsc") and self.packagename.lower().startswith(file.lower().split('.')[0]):
          filename = file
      # special case: php-net-ldap3.dsc in package php-pear-Net-LDAP3
      if not os.path.isfile(path + "/" + filename):
        for file in os.listdir(path):
          if file.endswith(".dsc"):
            filename = file
    if filename != filename.lower():
      if os.path.isfile(path + "/" + filename):
        os.rename(path + "/" + filename, path + "/" + filename.lower())
      filename = filename.lower()
    return filename

  def InstallRepositories(self, DownloadUrl):
    # first install required repos
    configfile=self.pathSrc + "/lbs-" + self.projectname + "/config.yml"
    if os.path.isfile(configfile):
      stream = open(configfile, 'r')
      prjconfig = yaml.load(stream)
      if self.dist in prjconfig['lbs'] and self.container.release in prjconfig['lbs'][self.dist]:
        repos = prjconfig['lbs']['debian'][self.container.release]['repos']
        for repo in repos:
          self.run(f"cd /etc/apt/sources.list.d/; echo '{repos[repo]}' > {repo}.list")
        # TODO: keys must belong to a repository
        if 'keys' in prjconfig['lbs'][self.dist][str(self.release)]:
          keys = prjconfig['lbs'][self.dist][str(self.release)]['keys']
          for key in keys:
            if not self.run(f"gpg --no-default-keyring --keyring /usr/share/keyrings/lbs-keyring.gpg --keyserver hkp://{settings.PUBLIC_KEY_SERVER}:80 --recv-keys {key}"):
              return False

    # install own repo as well if it exists
    repofile=settings.REPOS_PATH + "/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + self.container.release + "/Packages.gz"
    if os.path.isfile(repofile):
      repopath=DownloadUrl + "/repos/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + self.container.release + "/"
      self.run(f"cd /etc/apt/sources.list.d/; echo 'deb [signed-by=/usr/share/keyrings/{self.username}-{self.projectname}-keyring.gpg] {repopath} /' > lbs-{self.username}-{self.projectname}.list")
      DownloadUrlServer = DownloadUrl.replace('https://', '').replace('http://', '')
      self.run("mkdir -p /etc/apt/preferences.d && echo 'Package: *' > /etc/apt/preferences.d/lbs && echo 'Pin: origin " + DownloadUrlServer + "' >> /etc/apt/preferences.d/lbs && echo 'Pin-Priority: 501' >> /etc/apt/preferences.d/lbs")
    repofile=settings.REPOS_PATH + "/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + self.container.release + "/db/packages.db"
    if os.path.isfile(repofile):
      repopath=DownloadUrl + "/repos/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + self.container.release
      self.run(f"cd /etc/apt/sources.list.d/; echo 'deb [signed-by=/usr/share/keyrings/{self.username}-{self.projectname}-keyring.gpg] {repopath} {self.container.release} main' > lbs-{self.username}-{self.projectname}.list")
    project = Project.objects.filter(user__username=self.username).filter(name=self.projectname).first()
    if project.public_key_id:
      self.run("gpg --no-default-keyring --keyring /usr/share/keyrings/{self.username}-{self.projectname}-keyring.gpg --keyserver hkp://{settings.PUBLIC_KEY_SERVER}:80 --recv-keys {project.public_key_id}")

    # update the repository information
    self.run("apt-get update")
    return True

  def InstallRequiredPackages(self):
    # now install required packages
    dscfile=self.pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetDscFilename()
    packages=None
    # force-yes for packages from our own repository, they are not signed at the moment
    aptInstallFlags="--force-yes "
    nextLineBuildDepends=False
    if os.path.isfile(dscfile):
      self.run("cp -R lbs-" + self.projectname + "/" + self.packagename + "/* /tmp");
      self.run("sed -i 's/%{release}/0/g' " + "/tmp/" + self.GetDscFilename())
      self.run("sed -i 's/%{release}/0/g' " + "/tmp/debian/control")
      self.run("sed -i 's/%{release}/0/g' " + "/tmp/debian/changelog")
      if not self.run("cd /tmp; " +
              "mk-build-deps " + self.GetDscFilename() + "; dpkg -i *.deb; apt-get install -f -y " + aptInstallFlags + " && dpkg -i *.deb"):
        return False
    return True

  def BuildPackage(self):
    project = Project.objects.filter(user__username=self.username).filter(name=self.projectname).first()
    DownloadUrl = settings.DOWNLOAD_URL
    dscfile=self.pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetDscFilename()
    if os.path.isfile(dscfile):
      pathPackageSrc="/root/lbs-" + self.projectname + "/" + self.packagename

      # if debian.tar.gz exists, assume the sources come from OBS
      if os.path.isfile(self.pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/debian.tar.gz"):
        self.run("cd " + pathPackageSrc + " && mkdir -p debian && tar xzf debian.tar.gz && rm debian.tar.gz");
        self.run("cd " + pathPackageSrc + " && (for f in debian.*; do mv \$f debian/\${f:7}; done)")
        # make sure that we only have lowercase letters in the dsc filename
        self.run("cd " + pathPackageSrc + " && (for f in *.dsc; do mv \$f \${f,,}; done)")

      # if *debian.tar.xz exists, the files might come from Debian Launchpad
      if len(glob.glob(self.pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/*debian.tar.xz")) > 0:
        self.run("cd " + pathPackageSrc + " && tar xf *debian.tar.xz && rm *debian.tar.xz");

      # unpack the sources
      # the sources have been downloaded according to instructions in config.yml. see BuildHelper::DownloadSources
      self.run("cp /root/sources/* " + pathPackageSrc)
      self.run("rm -Rf tmpSource && mkdir tmpSource")
      self.run("for file in " + pathPackageSrc + "/*.tar.gz; do if [ -f \$file ]; then cd tmpSource && tar xzf \$file;rm " + pathPackageSrc + "/\`basename \$file\`; fi; done")
      self.run("for file in " + pathPackageSrc + "/*.tar.xz; do if [ -f \$file ]; then cd tmpSource && tar xf \$file;rm " + pathPackageSrc + "/\`basename \$file\`; fi; done")
      self.run("for file in " + pathPackageSrc + "/*.tgz; do if [ -f \$file ]; then cd tmpSource && tar xzf \$file;rm " + pathPackageSrc + "/\`basename \$file\`; fi; done")
      self.run("for file in /root/sources/*.tar.xz; do if [ -f \$file ]; then cd tmpSource && tar xf \$file; rm " + pathPackageSrc + "/\`basename \$file\`; fi; done")
      self.run("for file in /root/sources/*.tar.gz; do if [ -f \$file ]; then cd tmpSource && tar xzf \$file;rm " + pathPackageSrc + "/\`basename \$file\`; fi; done")
      self.run("for file in /root/sources/*.tgz; do if [ -f \$file ]; then cd tmpSource && tar xzf \$file;rm " + pathPackageSrc + "/\`basename \$file\`; fi; done")
      self.run("for file in /root/sources/*.tar.bz2; do if [ -f \$file ]; then cd tmpSource && tar xjf \$file; rm " + pathPackageSrc + "/\`basename \$file\`; fi; done")
      self.run("for dir in tmpSource/*; do if [ -d \$dir ]; then mv \$dir/* lbs-" + self.projectname + "/" + self.packagename + "; mv \$dir/.* lbs-" + self.projectname + "/" + self.packagename + "; fi; done")
      self.run("rm -Rf tmpSource")

      # read version from dsc file, that is on the build server
      # (setup.sh might overwrite the version number...)
      temppath = tempfile.mkdtemp()
      self.container.rsyncContainerGet(pathPackageSrc + "/" + self.GetDscFilename(), temppath)
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
      if project.secret:
        myPath = self.username + "/" + project.secret + "/" + self.projectname
      repopath=settings.REPOS_PATH + "/" + myPath + "/" + self.dist + "/" + self.container.release + "/"
      binarypath = repopath + "/" + arch + "/binary"
      if not os.path.isdir(binarypath):
        binarypath = repopath + "/pool/main/" + self.packagename[0] + "/" + self.packagename
      if os.path.isdir(binarypath):
        for file in os.listdir(binarypath):
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
      SSHContainerPath = f"{settings.SSH_TMP_PATH}/{self.username}/{self.projectname}"
      Path(SSHContainerPath).mkdir(parents=True, exist_ok=True)
      privateLBSkey_filename = SSHContainerPath + '/privateLBSkey'
      if os.path.isfile(privateLBSkey_filename):
        if not self.run("gpg --import < ~/.ssh/privateLBSkey && mkdir -p repo/conf && cp .ssh/distributions repo/conf && sed -i -e 's/bionic/" + self.release + "/g' repo/conf/distributions"):
          return False
        if not self.run("cd lbs-" + self.projectname + "; dpkg-sig --sign builder *.deb"):
          return False
        if not self.run("cd repo; for f in ~/lbs-" + self.projectname + "/*.deb; do pkgname=\`basename \$f\`; pkgname=\`echo \$pkgname | awk -F '_' '{print \$1}'\`; reprepro --delete clearvanished; reprepro remove " + self.container.release + " \$pkgname; reprepro includedeb " + self.container.release + " ~/lbs-" + self.projectname + "/\`basename \$f\`; done"):
          return False
        self.run("rm -Rf repo/conf")
      else:
        # add result to repo
        self.run("mkdir -p ~/repo/" + self.container.arch + "/binary")
        self.run("cp lbs-" + self.projectname + "/*.deb repo/" + self.container.arch + "/binary")
      if not self.run("cd repo && dpkg-scanpackages -m . /dev/null | gzip -9c > Packages.gz"):
        return False

    return True

  def GetSrcInstructions(self, DownloadUrl, buildtarget):
    return None

  def GetRepoInstructions(self, DownloadUrl, buildtarget):
    buildtarget = buildtarget.split("/")

    keyinstructions = ""
    project = Project.objects.filter(user__username=self.username).filter(name=self.projectname).first()

    # check if there is such a package at all
    checkfile=settings.REPOS_PATH + "/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + buildtarget[1] + "/pool/main/*/*/" + self.GetDscFilename()[:-4].lower() + "*"
    if glob.glob(checkfile):
      # repo has been created with reprepro
      path = " " + buildtarget[1] + " main"
      if project.public_key_id:
        keyinstructions += f"gpg --no-default-keyring --keyring /usr/share/keyrings/{self.username}-{self.projectname}-keyring.gpg --keyserver hkp://{settings.PUBLIC_KEY_SERVER}:80 --recv-keys {project.public_key_id}\n"
    else:
      checkfile=settings.REPOS_PATH + "/" + self.username + "/" + self.projectname + "/" + self.dist + "/*/*/binary/" + self.GetDscFilename()[:-4] + "*"
      if glob.glob(checkfile):
        path = "/ /"
      else:
        return None
   
    result = ""
    result += "apt install apt-transport-https gnupg ca-certificates\n"
    result += keyinstructions
    if keyinstructions:
      result += f"echo 'deb [arch={buildtarget[2]} signed-by=/usr/share/keyrings/{self.username}-{self.projectname}-keyring.gpg] {DownloadUrl}/repos/{self.username}/"
    else:
      result += f"echo 'deb [arch={buildtarget[2]}] {DownloadUrl}/repos/{self.username}/"
    if project.secret:
        result += project.secret + "/"
    result += self.projectname + "/" + buildtarget[0] + "/" + buildtarget[1] + path + "' >> " + f"/etc/apt/sources.list.d/{self.username}-{self.projectname}.list\n"
    result += "apt update\n"
    # packagename: name of dsc file, without .dsc at the end
    result += "apt install " + self.GetDscFilename()[:-4].lower()

    return result

  def GetDependanciesAndProvides(self):
    dscfile=self.pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetDscFilename()
    builddepends=[]
    deliverables={}
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

    controlfile=self.pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/debian/control"
    recentpackagename=self.packagename
    nextLineDepends=False
    if os.path.isfile(controlfile):
      for line in open(controlfile):
        packagesWithVersions=None
        if line.lower().startswith("package:"):
          recentpackagename=line[len("package:"):].strip()
          deliverables[recentpackagename] = {}
          deliverables[recentpackagename]['provides'] = []
          deliverables[recentpackagename]['requires'] = []
        elif line.lower().startswith("depends:"):
          packagesWithVersions=line[len("depends:"):].strip().split(',')
        if nextLineDepends:
          packagesWithVersions=line.strip().split(',')
        if packagesWithVersions is not None:
          nextLineDepends=line.strip().endswith(",") or line.strip().endswith(":")
          for word in packagesWithVersions:
            for w2 in word.split('|'):
              if len(w2.strip()) > 0:
                deliverables[recentpackagename]['requires'].append(w2.split()[0].strip())

    return (builddepends, deliverables)

