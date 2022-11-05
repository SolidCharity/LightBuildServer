#!/usr/bin/env python3
"""Light Build Server: build packages for various distributions, using linux containers"""

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

from time import gmtime, strftime
import datetime
import os
import traceback
import shutil
import logging
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from lib.RemoteContainer import RemoteContainer
from lib.DockerContainer import DockerContainer
from lib.CoprContainer import CoprContainer
from lib.LXCContainer import LXCContainer
from lib.LXDContainer import LXDContainer
from lib.BuildHelper import BuildHelper
from lib.BuildHelperFactory import BuildHelperFactory
from lib.Shell import Shell
from lib.Logger import Logger

from machines.models import Machine
from projects.models import Project

class Builder:
  'run one specific build of one package'

  def __init__(self, LBS, logger):
    self.LBS = LBS
    self.logger = logger
    self.container = None
    self.finished = False
    self.buildmachine = None

  def createbuildmachine(self, distro, release, arch, buildmachine, packageSrcPath):
    self.buildmachine = buildmachine
    # create a container on a remote machine
    machine = Machine.objects.filter(host=buildmachine).first()
    if machine.type == 'lxc':
      self.container = LXCContainer(buildmachine, machine, self.logger, packageSrcPath)
    elif machine.type == 'lxd':
      self.container = LXDContainer(buildmachine, machine, self.logger, packageSrcPath)
    elif machine.type == 'docker':
      self.container = DockerContainer(buildmachine, machine, self.logger, packageSrcPath)
    elif machine.type == 'copr':
      self.container = CoprContainer(buildmachine, machine, self.logger, packageSrcPath)
    return self.container.createmachine(distro, release, arch, buildmachine)

  def buildpackageOnCopr(self, build, packageSrcPath):
    project = Project.objects.filter(user = build.user, name=build.project).first()

    # connect to copr
    SSHContainerPath = f"{settings.SSH_TMP_PATH}/{build.user.username}/{build.project}"
    Path(self.SSHContainerPath).mkdir(parents=True, exist_ok=True)
    if not project.copr_token:
        raise Exception("problem connecting to copr, we are missing the copr token")
    coprtoken_filename = self.SSHContainerPath + '/copr'
    with open(coprtoken_filename, 'w') as f:
        f.write(project.copr_token)

    copr_projectname =  build.project
    if project.copr_project_name:
      copr_projectname = project.copr_project_name
    copr_username = build.user.username
    if project.copr_user_name:
      copr_username = project.copr_user_name

    if not self.container.connectToCopr(coprtoken_filename, copr_username, copr_projectname):
      raise Exception("problem connecting to copr, does the project " + copr_projectname + " already exist?")

    # calculate the release number
    release = self.container.getLatestReleaseFromCopr(build.package)
    if release is not None:
      if release.find('.') > -1:
        releasenumber = int(release[:release.find('.')])
        afterreleasenumber = release[release.find('.'):]
        release = str(releasenumber+1)+afterreleasenumber
      else:
        release = str(int(release)+1)

    # build the src rpm locally, and move to public directory
    # simplification: tarball must be in the git repository
    self.shell = Shell(self.logger)
    rpmbuildpath = "/run/uwsgi/rpmbuild_" + build.user.username + "_" + build.project + "_" + build.package
    self.shell.executeshell("mkdir -p " + rpmbuildpath + "/SOURCES; mkdir -p " + rpmbuildpath + "/SPECS")
    self.shell.executeshell("cp -R " + packageSrcPath + "/* " + rpmbuildpath + "/SOURCES; mv " + rpmbuildpath + "/SOURCES/*.spec " + rpmbuildpath + "/SPECS")
    if release is not None:
      self.shell.executeshell("sed -i 's/^Release:.*/Release: " + release + "/g' " + rpmbuildpath + "/SPECS/*.spec")
    if not self.shell.executeshell("rpmbuild --define '_topdir " + rpmbuildpath + "' -bs " + rpmbuildpath + "/SPECS/" + packagename + ".spec"):
      raise Exception("Problem with building the source rpm file for package " + build.package)
    myPath = build.user.username + "/" + build.project
    if project.secret:
      raise Exception("You cannot use a secret path when you are working with Copr")
    repoPath=settings.REPOS_PATH + "/" + myPath + "/" + build.distro + "/" + build.release + "/src"
    files = os.listdir(rpmbuildpath + "/SRPMS")
    if files is not None and len(files) == 1:
      srcrpmfilename = files[0]
    else:
      raise Exception("cannot find the source rpm, no files in " + rpmbuildpath + "/SRPMS")
    if not os.path.isfile(rpmbuildpath + "/SRPMS/" + srcrpmfilename):
      raise Exception("cannot find the source rpm, " + rpmbuildpath + "/SRPMS/" + srcrpmfilename + " is not a file")
    if not self.shell.executeshell("mkdir -p " + repoPath + " && mv " + rpmbuildpath + "/SRPMS/" + srcrpmfilename + " " + repoPath + " && rm -Rf " + rpmbuildpath):
      raise Exception("Problem moving the source rpm file")

    # tell copr to build this srpm. raise an exception if the build failed.
    if not self.container.buildProject(settings.DOWNLOAD_URL + "/repos/" + myPath + "/" + build.distro + "/" + build.release + "/src/" + srcrpmfilename):
      raise Exception("problem building the package on copr")

  def buildpackageOnContainer(self, build, pathSrc):
        # install a mount for the project repo
        myPath = build.user.username + "/" + build.project
        project = Project.objects.filter(user = build.user, name=build.project).first()
        if project.secret:
          myPath = build.user.username + "/" + project.secret + "/" + build.project
        mountPath=settings.REPOS_PATH + "/" + myPath + "/" + build.distro + "/" + build.release
        if not self.container.installmount(mountPath, "/mnt" + mountPath, "/root/repo"):
          raise Exception("Problem with installmount")
        mountPath=settings.TARBALLS_PATH + "/" + myPath
        if not self.container.installmount(mountPath, "/mnt" + mountPath, "/root/tarball"):
          raise Exception("Problem with installmount")
 
        # prepare container, install packages that the build requires; this is specific to the distro
        self.buildHelper = BuildHelperFactory.GetBuildHelper(build.distro, self.container, build)
        if not self.buildHelper.PrepareMachineBeforeStart():
          raise Exception("Problem with PrepareMachineBeforeStart")
        if self.container.startmachine():
          self.logger.print("container has been started successfully")
        else:
          raise Exception("Problem with startmachine")
        if not self.buildHelper.PrepareMachineAfterStart():
          raise Exception("Problem with PrepareMachineAfterStart")
        if not self.buildHelper.PrepareForBuilding():
          raise Exception("Problem with PrepareForBuilding")

        # copy the repo to the container
        self.container.rsyncContainerPut(pathSrc+'lbs-'+build.project, "/root/lbs-"+build.project)
        # copy the keys to the container
        SSHContainerPath = f"{settings.SSH_TMP_PATH}/{build.user.username}/{build.project}"
        Path(SSHContainerPath).mkdir(parents=True, exist_ok=True)
        # TODO: store keys and other files in this directory
        self.container.rsyncContainerPut(SSHContainerPath + '/*', '/root/.ssh/')
        self.container.executeInContainer('chmod 600 /root/.ssh/*')

        if not self.buildHelper.DownloadSources():
          raise Exception("Problem with DownloadSources")
        if not self.buildHelper.InstallRepositories(settings.DOWNLOAD_URL):
          raise Exception("Problem with InstallRepositories")
        if not self.buildHelper.SetupEnvironment(build.branchname):
          raise Exception("Setup script did not succeed")
        if not self.buildHelper.InstallRequiredPackages():
          raise Exception("Problem with InstallRequiredPackages")
        # disable the network, so that only code from the tarball is being used
        if not self.buildHelper.DisableOutgoingNetwork():
          raise Exception("Problem with disabling the network")
        if not self.buildHelper.BuildPackage():
          raise Exception("Problem with building the package")
        myPath = build.user.username + "/" + build.project
        if project.secret:
          myPath = build.user.username + "/" + project.secret + "/" + build.project
        srcPath=settings.REPOS_PATH + "/" + myPath + "/" + build.distro + "/" + build.release
        destPath=srcPath[:srcPath.rindex("/")]
        srcPath="/mnt"+srcPath
        if not self.container.rsyncHostGet(srcPath, destPath):
          raise Exception("Problem with syncing repos")
        srcPath=settings.TARBALLS_PATH + "/" + myPath
        destPath=srcPath[:srcPath.rindex("/")]
        srcPath="/mnt"+srcPath
        if not self.container.rsyncHostGet(srcPath, destPath):
          raise Exception("Problem with syncing tarballs")
        # create repo file
        self.buildHelper.CreateRepoFile()

  def buildpackage(self, build):
    self.logger.startTimer()
    self.logger.print(" * Starting at " + strftime("%Y-%m-%d %H:%M:%S GMT%z"))
    self.logger.print(" * Preparing the machine...")

    # get the sources of the packaging instructions
    gotPackagingInstructions = False
    try:
      pathSrc=self.LBS.getPackagingInstructions(build)
      packageSrcPath=pathSrc + '/lbs-' + build.project + '/' + build.package
      gotPackagingInstructions = True
    except Exception as e:
      self.logger.print("LBSERROR: "+str(e)+ "; for more details see the server log")
      traceback.print_exc()

    jobFailed = True
    if not gotPackagingInstructions:
      self.LBS.ReleaseMachine(build.buildmachine, jobFailed)
    elif self.createbuildmachine(build.distro, build.release, build.arch, build.buildmachine, packageSrcPath):
      try:
        if type(self.container) is CoprContainer:
          self.buildpackageOnCopr(build, packageSrcPath)
        else:
          self.buildpackageOnContainer(build, pathSrc)
        self.logger.print("Success!")
        self.LBS.MarkPackageAsBuilt(build)
        jobFailed = False
      except Exception as e:
        self.logger.print("LBSERROR: "+str(e), 0)
        traceback.print_exc()
      finally:
        self.LBS.ReleaseMachine(build.buildmachine, jobFailed)
    else:
      self.logger.print("LBSERROR: There is a problem with creating the container!")
      self.LBS.ReleaseMachine(build.buildmachine, jobFailed)
    self.finished = True
    logpath=self.logger.getLogPath(build)
    buildnumber=self.logger.store(settings.DELETE_LOG_AFTER_DAYS, settings.KEEP_MINIMUM_LOGS, logpath)
    if self.logger.hasLBSERROR() or settings.SEND_EMAIL_ON_SUCCESS:
      if settings.EMAIL_FROM_ADDRESS == 'lbs@example.org':
        self.logger.print("Please configure the email settings for sending notification emails")
      else:
        try:
          self.logger.email(settings.EMAIL_FROM_ADDRESS, build.user.email, \
            "LBS Result for " + build.project + "/" + build.package, \
            settings.LBS_URL + "/logs/" + logpath + "/" + str(buildnumber))
        except Exception as e:
          self.logger.print("ERROR: we could not send the email")
          traceback.print_exc()

    # now mark the build finished
    build.status = 'FINISHED'
    build.finished = timezone.now()
    build.buildsuccess = Logger(build).getBuildResult()
    build.save()

    self.logger.clean()
    return self.logger.get()

