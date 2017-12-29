#!/usr/bin/env python3
"""Light Build Server: build packages for various distributions, using linux containers"""

# Copyright (c) 2014-2016 Timotheus Pokorra

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

from RemoteContainer import RemoteContainer
from DockerContainer import DockerContainer
from CoprContainer import CoprContainer
from LXCContainer import LXCContainer
from BuildHelper import BuildHelper
from BuildHelperFactory import BuildHelperFactory
import Config
from time import gmtime, strftime
import datetime
import os
import shutil
from Shell import Shell
import logging
from Logger import Logger
from Database import Database

class Build:
  'run one specific build of one package'

  def __init__(self, LBS, logger):
    self.LBS = LBS
    self.logger = logger
    self.container = None
    self.finished = False
    self.buildmachine = None
    self.config = Config.LoadConfig()

  def createbuildmachine(self, lxcdistro, lxcrelease, lxcarch, buildmachine, packageSrcPath):
    # create a container on a remote machine
    self.buildmachine = buildmachine
    con = Database(self.config)
    stmt = "SELECT * FROM machine WHERE name = ?"
    cursor = con.execute(stmt, (buildmachine,))
    machine = cursor.fetchone()
    con.close()
    if machine['type'] == 'lxc':
      self.container = LXCContainer(buildmachine, machine, self.logger, packageSrcPath)
    elif machine['type'] == 'docker':
      self.container = DockerContainer(buildmachine, machine, self.logger, packageSrcPath)
    elif machine['type'] == 'copr':
      self.container = CoprContainer(buildmachine, machine, self.logger, packageSrcPath)
    return self.container.createmachine(lxcdistro, lxcrelease, lxcarch, buildmachine)

  def buildpackageOnCopr(self, username, projectname, packagename, branchname, packageSrcPath, lxcdistro, lxcrelease, lxcarch):
    # connect to copr
    coprtoken_filename = self.config['lbs']['SSHContainerPath'] + '/' + username + '/' + projectname + '/copr'
    if not os.path.isfile(coprtoken_filename):
      raise Exception("please download a token file from copr and save in " + coprtoken_filename)

    userconfig = self.config['lbs']['Users'][username]
    copr_projectname =  projectname
    if 'CoprProjectName' in userconfig['Projects'][projectname]:
      copr_projectname = userconfig['Projects'][projectname]['CoprProjectName']

    if not self.container.connectToCopr(coprtoken_filename, copr_projectname):
      raise Exception("problem connecting to copr, does the project " + copr_projectname + " already exist?")

    # calculate the release number
    release = self.container.getLatestReleaseFromCopr(packagename)
    if release is not None:
      if release.find('.') > -1:
        releasenumber = int(release[:release.find('.')])
        afterreleasenumber = release[release.find('.'):]
        release = str(releasenumber+1)+afterreleasenumber
      else:
        release = str(int(release)+1)

    # build the src rpm locally, and move to public directory
    # simplification: tarball must be in the git repository
    # simplification: lbs must run on Fedora
    self.shell = Shell(self.logger)
    rpmbuildpath = "/run/uwsgi/rpmbuild_" + username + "_" + projectname + "_" + packagename
    self.shell.executeshell("mkdir -p " + rpmbuildpath + "/SOURCES; mkdir -p " + rpmbuildpath + "/SPECS")
    self.shell.executeshell("cp -R " + packageSrcPath + "/* " + rpmbuildpath + "/SOURCES; mv " + rpmbuildpath + "/SOURCES/*.spec " + rpmbuildpath + "/SPECS")
    if release is not None:
      self.shell.executeshell("sed -i 's/^Release:.*/Release: " + release + "/g' " + rpmbuildpath + "/SPECS/*.spec")
    if not self.shell.executeshell("rpmbuild --define '_topdir " + rpmbuildpath + "' -bs " + rpmbuildpath + "/SPECS/" + packagename + ".spec"):
      raise Exception("Problem with building the source rpm file for package " + packagename)
    myPath = username + "/" + projectname
    if 'Secret' in self.config['lbs']['Users'][username]:
      raise Exception("You cannot use a secret path when you are working with Copr")
    repoPath=self.config['lbs']['ReposPath'] + "/" + myPath + "/" + lxcdistro + "/" + lxcrelease + "/src"
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
    if not self.container.buildProject(self.config['lbs']['DownloadUrl'] + "/repos/" + myPath + "/" + lxcdistro + "/" + lxcrelease + "/src/" + srcrpmfilename):
      raise Exception("problem building the package on copr")

  def buildpackageOnContainer(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, pathSrc):
        # install a mount for the project repo
        myPath = username + "/" + projectname
        if 'Secret' in self.config['lbs']['Users'][username]:
          myPath = username + "/" + self.config['lbs']['Users'][username]['Secret'] + "/" + projectname
        mountPath=self.config['lbs']['ReposPath'] + "/" + myPath + "/" + lxcdistro + "/" + lxcrelease
        if not self.container.installmount(mountPath, "/mnt" + mountPath, "/root/repo"):
          raise Exception("Problem with installmount")
        mountPath=self.config['lbs']['TarballsPath'] + "/" + myPath
        if not self.container.installmount(mountPath, "/mnt" + mountPath, "/root/tarball"):
          raise Exception("Problem with installmount")
 
        # prepare container, install packages that the build requires; this is specific to the distro
        self.buildHelper = BuildHelperFactory.GetBuildHelper(lxcdistro, self.container, username, projectname, packagename, branchname)
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
        self.container.rsyncContainerPut(pathSrc+'lbs-'+projectname, "/root/lbs-"+projectname)
        # copy the keys to the container
        sshContainerPath = self.config['lbs']['SSHContainerPath']
        if os.path.exists(sshContainerPath + '/' + username + '/' + projectname):
          self.container.rsyncContainerPut(sshContainerPath + '/' + username + '/' + projectname + '/*', '/root/.ssh/');

        if not self.buildHelper.DownloadSources():
          raise Exception("Problem with DownloadSources")
        if not self.buildHelper.InstallRepositories(self.config['lbs']['DownloadUrl']):
          raise Exception("Problem with InstallRepositories")
        if not self.buildHelper.SetupEnvironment(branchname):
          raise Exception("Setup script did not succeed")
        if not self.buildHelper.InstallRequiredPackages():
          raise Exception("Problem with InstallRequiredPackages")
        # disable the network, so that only code from the tarball is being used
        if not self.buildHelper.DisableOutgoingNetwork():
          raise Exception("Problem with disabling the network")
        if not self.buildHelper.BuildPackage():
          raise Exception("Problem with building the package")
        myPath = username + "/" + projectname
        if 'Secret' in self.config['lbs']['Users'][username]:
          myPath = username + "/" + self.config['lbs']['Users'][username]['Secret'] + "/" + projectname
        srcPath=self.config['lbs']['ReposPath'] + "/" + myPath + "/" + lxcdistro + "/" + lxcrelease
        destPath=srcPath[:srcPath.rindex("/")]
        srcPath="/mnt"+srcPath
        if not self.container.rsyncHostGet(srcPath, destPath):
          raise Exception("Problem with syncing repos")
        srcPath=self.config['lbs']['TarballsPath'] + "/" + myPath
        destPath=srcPath[:srcPath.rindex("/")]
        srcPath="/mnt"+srcPath
        if not self.container.rsyncHostGet(srcPath, destPath):
          raise Exception("Problem with syncing tarballs")
        # create repo file
        self.buildHelper.CreateRepoFile()

  def buildpackage(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildmachine, jobId):
    userconfig = self.config['lbs']['Users'][username]
    self.logger.startTimer()
    self.logger.print(" * Starting at " + strftime("%Y-%m-%d %H:%M:%S GMT%z"))
    self.logger.print(" * Preparing the machine...")

    # get the sources of the packaging instructions
    gotPackagingInstructions = False
    try:
      pathSrc=self.LBS.getPackagingInstructions(userconfig, username, projectname, branchname)
      packageSrcPath=pathSrc + '/lbs-'+projectname + '/' + packagename
      gotPackagingInstructions = True
    except Exception as e:
      print(e)
      self.logger.print("LBSERROR: "+str(e)+ "; for more details see /var/log/uwsgi.log")

    jobFailed = True
    if not gotPackagingInstructions:
      self.LBS.ReleaseMachine(buildmachine, jobFailed)
    elif self.createbuildmachine(lxcdistro, lxcrelease, lxcarch, buildmachine, packageSrcPath):
      try:
        if type(self.container) is CoprContainer:
          self.buildpackageOnCopr(username, projectname, packagename, branchname, packageSrcPath, lxcdistro, lxcrelease, lxcarch)
        else:
          self.buildpackageOnContainer(username, projectname, packagename, branchname, lxcdistro, lxcrelease, pathSrc)
        self.logger.print("Success!")
        self.LBS.MarkPackageAsBuilt(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch)
        jobFailed = False
      except Exception as e:
        # TODO: logging to log file does not work yet?
        logging.basicConfig(level=logging.DEBUG, filename='/var/log/lbs.log')
        logging.exception("Error happened...")
        self.logger.print("LBSERROR: "+str(e))
      finally:  
        self.LBS.ReleaseMachine(buildmachine, jobFailed)
    else:
      self.logger.print("LBSERROR: There is a problem with creating the container!")
      self.LBS.ReleaseMachine(buildmachine, jobFailed)
    self.finished = True
    logpath=self.logger.getLogPath(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch)
    buildnumber=self.logger.store(self.config['lbs']['DeleteLogAfterDays'], self.config['lbs']['KeepMinimumLogs'], logpath)
    if self.logger.hasLBSERROR() or not self.config['lbs']['SendEmailOnSuccess'] == False:
      if self.config['lbs']['EmailFromAddress'] == 'lbs@example.org':
        self.logger.print("Please configure the email settings for sending notification emails")
      else:
        self.logger.email(self.config['lbs']['EmailFromAddress'], userconfig['EmailToAddress'], "LBS Result for " + projectname + "/" + packagename, self.config['lbs']['LBSUrl'] + "/logs/" + logpath + "/" + str(buildnumber))

    # now mark the build finished
    con = Database(self.config)
    stmt = "UPDATE build SET status='FINISHED', finished=?, buildsuccess=?, buildnumber=? WHERE id = ?"
    lastBuild = Logger().getLastBuild(username, projectname, packagename, branchname, lxcdistro+"/"+lxcrelease+"/"+lxcarch)
    con.execute(stmt, (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), lastBuild["resultcode"], lastBuild["number"], jobId))
    con.commit()
    con.close()

    self.logger.clean()
    return self.logger.get()

