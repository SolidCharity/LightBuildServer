#!/usr/bin/env python3
"""Light Build Server: build packages for various distributions, using linux containers"""

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

from RemoteContainer import RemoteContainer
from DockerContainer import DockerContainer
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
    conf = self.config['lbs']['Machines'][buildmachine]
    if 'type' in conf and conf['type'] == 'lxc':
      self.container = LXCContainer(buildmachine, conf, self.logger, packageSrcPath)
    else:
      self.container = DockerContainer(buildmachine, conf, self.logger, packageSrcPath)
    return self.container.createmachine(lxcdistro, lxcrelease, lxcarch, buildmachine)

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
      self.logger.print("LBSERROR: "+str(e))

    jobFailed = True
    if not gotPackagingInstructions:
      self.LBS.ReleaseMachine(buildmachine, jobFailed)
    elif self.createbuildmachine(lxcdistro, lxcrelease, lxcarch, buildmachine, packageSrcPath):

      try:
        # install a mount for the project repo
        myPath = username + "/" + projectname
        if 'Secret' in self.config['lbs']['Users'][username]:
          myPath = username + "/" + self.config['lbs']['Users'][username]['Secret'] + "/" + projectname
        self.container.installmount("/root/repo", self.config['lbs']['ReposPath'] + "/" + myPath + "/" + lxcdistro + "/" + lxcrelease)
        self.container.installmount("/root/tarball", self.config['lbs']['TarballsPath'] + "/" + myPath)
      
        # prepare container, install packages that the build requires; this is specific to the distro
        self.buildHelper = BuildHelperFactory.GetBuildHelper(lxcdistro, self.container, username, projectname, packagename)
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
        if not self.buildHelper.BuildPackage(self.config):
          raise Exception("Problem with building the package")
        myPath = username + "/" + projectname
        if 'Secret' in self.config['lbs']['Users'][username]:
          myPath = username + "/" + self.config['lbs']['Users'][username]['Secret'] + "/" + projectname
        if not self.container.rsyncHostGet(self.config['lbs']['ReposPath'] + "/" + myPath + "/" + lxcdistro + "/" + lxcrelease):
          raise Exception("Problem with syncing repos")
        if not self.container.rsyncHostGet(self.config['lbs']['TarballsPath'] + "/" + myPath):
          raise Exception("Problem with syncing tarballs")
        # create repo file
        self.buildHelper.CreateRepoFile(self.config)
        self.logger.print("Success!")
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

