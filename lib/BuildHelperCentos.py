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
import time
import os
import yaml
import tempfile
import shutil
import re
import logging

class BuildHelperCentos(BuildHelper):
  'build packages for CentOS'

  def __init__(self, container, pathInsideContainer, username, projectname, packagename):
    self.dist='centos'
    BuildHelper.__init__(self, container, pathInsideContainer, username, projectname, packagename)

  def PrepareMachineBeforeStart(self):
    return True

  def PrepareForBuilding(self):
    #self.run("yum clean headers dbcache rpmdb")
    if not self.run("yum -y update"):
      if not self.run("yum clean all && yum -y update"):
        return False
    if not self.run("yum -y install tar createrepo gcc rpm-build yum-utils"):
      return False
    # CentOS5: /root/rpmbuild should point to /usr/src/redhat
    if self.dist == "centos" and self.release == "5":
      self.run("mkdir -p /usr/src/redhat; ln -s /usr/src/redhat rpmbuild")
      self.run("yum -y install make")
    self.run("mkdir -p rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}")
    return True

  def GetSpecFilename(self):
    pathSrc="/var/lib/lbs/src/"+self.username
    if os.path.isdir(pathSrc + "/lbs-" + self.projectname + "/" + self.packagename):
      for file in os.listdir(pathSrc + "/lbs-" + self.projectname + "/" + self.packagename):
        if file.endswith(".spec") and self.packagename.startswith(file.split('.')[0]):
          return file
    return self.packagename + ".spec"

  def InstallRequiredPackages(self, DownloadUrl):
    # first install required repos
    pathSrc="/var/lib/lbs/src/"+self.username
    configfile=pathSrc + "/lbs-" + self.projectname + "/config.yml"
    if os.path.isfile(configfile):
      stream = open(configfile, 'r')
      config = yaml.load(stream)
      if self.dist in config['lbs'] and str(self.release) in config['lbs'][self.dist]:
        repos = config['lbs'][self.dist][str(self.release)]['repos']
        for repo in repos:
          if repo.endswith('.repo'):
            self.run("cd /etc/yum.repos.d/; curl -L " + repo + " -o `basename " + repo + "`")
          elif repo.endswith('.rpm'):
            if not self.run("yum -y install " + repo):
              return False

    # install own repo as well if it exists
    repofile="/var/www/repos/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + self.release + "/lbs-" + self.username + "-" + self.projectname + ".repo"
    if os.path.isfile(repofile):
      self.container.copytree(repofile,"/etc/yum.repos.d/")

    self.run("yum clean metadata")

    # now install required packages
    specfile=pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetSpecFilename()
    remoteSpecName="lbs-" + self.projectname + "/" + self.packagename + "/" + self.packagename + ".spec"
    self.run("sed -e 's/%{release}/0/g' " + remoteSpecName + " > /tmp/" + self.packagename + ".spec")
    if not self.run("yum-builddep -y /tmp/" + self.packagename + ".spec"):
      return False
    return True

  def BuildPackage(self, config):
    DownloadUrl = config['lbs']['DownloadUrl']
    DeletePackagesAfterDays = config['lbs']['DeletePackagesAfterDays']
    KeepMinimumPackages = config['lbs']['KeepMinimumPackages']
    repopath="/var/www/repos/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + self.release
    pathSrc="/var/lib/lbs/src/"+self.username
    specfile=pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetSpecFilename()
    if os.path.isfile(specfile):
      remoteSpecName="lbs-" + self.projectname + "/" + self.packagename + "/" + self.packagename + ".spec"
      self.run('sed -i "s/0%{?suse_version}/' + str(self.suse_version) + '/g" ' + remoteSpecName)
      self.run('sed -i "s/0%{?rhel}/' + str(self.rhel) + '/g" ' + remoteSpecName)
      self.run('sed -i "s/0%{?fedora}/' + str(self.fedora) + '/g" ' + remoteSpecName)
      self.run("cp " + remoteSpecName + " rpmbuild/SPECS")

      # copy patches, and other files (eg. env.sh for mono-opt)
      self.run("cp lbs-" + self.projectname + "/" + self.packagename + "/* rpmbuild/SOURCES")

      # move the sources that have been downloaded according to instructions in config.yml. see BuildHelper::DownloadSources
      self.run("mv sources/* rpmbuild/SOURCES")

      # read version from spec file, that is on the build server
      # (setup.sh might overwrite the version number...)
      temppath = tempfile.mkdtemp()
      self.container.rsyncContainerGet("/root/lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetSpecFilename(), temppath)
      buildversion = "1.0.0"
      for line in open(temppath + "/" + self.GetSpecFilename()):
        if line.startswith("%define version "):
          buildversion=line[len("%define version "):].strip()
          break
      shutil.rmtree(temppath)

      # build counter for automatically increasing the release number
      buildnumber=0
      arch=self.arch
      if arch == "amd64":
        arch="x86_64"
      elif arch == "i686":
        arch="i386"

      rpmfiles=[]
      if os.path.isdir(repopath + "/" + arch):
        for file in os.listdir(repopath + "/" + arch):
          # TODO use GetSpecFilename, without spec, instead of packagename
          if file.startswith(self.packagename + "-" + buildversion + "-") and file.endswith("." + arch + ".rpm"):
            oldnumber=int(file[len(self.packagename + "-" + buildversion + "-"):-1*len("." + arch + ".rpm")])
            rpmfiles.append(str(oldnumber).zfill(6) + ":" + file)
            if oldnumber >= buildnumber:
              buildnumber = oldnumber + 1
      self.run("sed -i -e 's/Release: %{release}/Release: " + str(buildnumber) + "/g' rpmbuild/SPECS/" + self.packagename + ".spec")
      if not self.run("rpmbuild -ba rpmbuild/SPECS/" + self.packagename + ".spec"):
        return False

      # add result to repo
      self.run("mkdir -p ~/repo/src")
      self.run("cp ~/rpmbuild/SRPMS/*.src.rpm ~/repo/src")
      self.run("cp -R ~/rpmbuild/RPMS/* ~/repo")

      # clean up old packages
      MaximumAgeInSeconds=time.time() - (DeletePackagesAfterDays*24*60*60)
      rpmfiles=sorted(rpmfiles)
      if (len(rpmfiles) > KeepMinimumPackages):
        for i in range(1, len(rpmfiles) - KeepMinimumPackages + 1):
          file=rpmfiles[i - 1][7:]
          # delete older rpm files, depending on DeletePackagesAfterDays
          if os.path.getmtime(repopath + "/" + arch + "/" + file) < MaximumAgeInSeconds:
            self.run("rm -f " + "/root/repo/" + arch + "/" + file)
            self.run("rm -f " + "/root/repo/" + arch + "/" + str.replace(file, self.packagename + "-", self.packagename + "-debuginfo-"))
            # TODO: what about other packages provided by that source package
            self.run("rm -f " + "/root/repo/src/" + str.replace(file, arch+".rpm", "src.rpm"))

      if not self.run("cd repo && createrepo ."):
        return False
    return True

  def CreateRepoFile(self, config):
    DownloadUrl = config['lbs']['DownloadUrl']
    repopath="/var/www/repos/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + self.release
    if os.path.isdir(repopath + "/repodata"):
      repoFileContent="[lbs-"+self.username + "-"+self.projectname +"]\n"
      repoFileContent+="name=LBS-"+self.username + "-"+self.projectname +"\n"
      repoFileContent+="baseurl=" + DownloadUrl + "/repos/" + self.username + "/" + self.projectname + "/" + self.dist + "/" + self.release + "\n"
      repoFileContent+="enabled=1\n"
      repoFileContent+="gpgcheck=0\n"
      repofile="lbs-"+self.username + "-"+self.projectname +".repo"
      with open(repopath + "/" + repofile, 'w') as f:
        f.write(repoFileContent)
    return True

  def GetRepoInstructions(self, DownloadUrl, buildtarget):
    buildtarget = buildtarget.split("/")
    result = "cd /etc/yum.repos.d/\n"
    result += "wget " + DownloadUrl + "/repos/" + self.username + "/" + self.projectname + "/" + buildtarget[0] + "/" + buildtarget[1] + "/lbs-"+self.username + "-"+self.projectname +".repo\n"
    # packagename: name of spec file, without .spec at the end
    result += "yum install " + self.GetSpecFilename()[:-5]
    return result

  def GetDependanciesAndProvides(self):
    pathSrc="/var/lib/lbs/src/"+self.username
    specfile=pathSrc + "/lbs-" + self.projectname + "/" + self.packagename + "/" + self.GetSpecFilename()
    builddepends=[]
    provides={}
    if os.path.isfile(specfile):
      for line in open(specfile):
        if line.lower().startswith("buildrequires: "):
          if line.count(",") > 0:
            packagesWithVersions=line[len("BuildRequires: "):].split(",")
          else:
            packagesWithVersions=line[len("BuildRequires: "):].split()
          ignoreNext=False
          for word in packagesWithVersions:
            if not ignoreNext:
              # filter >= 3.0, only use package names
              if word[0] == '>' or word[0] == '<' or word[0] == '=':
                ignoreNext=True
              else:
                builddepends.append(word.strip())
            else:
              ignoreNext=False

      name = self.packagename
      recentpackagename=name
      for line in open(specfile):
        if line.lower().startswith("name:"):
          name = line[len("name:"):].strip()
          recentpackagename=name
          provides[name] = []
        elif line.lower().startswith("%package -n"):
          recentpackagename=line[len("%package -n"):].strip()
          provides[recentpackagename] = []
        elif line.lower().startswith("%package"):
          recentpackagename=self.packagename + "-" + line[len("%package"):].strip()
          provides[recentpackagename] = []
        elif line.lower().startswith("requires:"):
          r = line[len("requires:"):].strip().replace("(", "-").replace(")", "")
          provides[recentpackagename].append(r.split()[0])

    return (builddepends, provides)
