#!/usr/bin/env python3
"""Light Build Server: build packages for various distributions, using linux containers"""

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

from LXCContainer import LXCContainer
from BuildHelper import BuildHelper
from BuildHelperFactory import BuildHelperFactory
from time import gmtime, strftime
import yaml
import os
import shutil

class LightBuildServer:
  'light build server based on lxc and git'

  def __init__(self, logger):
    self.logger = logger
    self.container = None
    self.finished = False
    self.MachineAvailabilityPath="/var/lib/lbs/machines"
    configfile="../config.yml"
    stream = open(configfile, 'r')
    self.config = yaml.load(stream)

  def createbuildmachine(self, lxcdistro, lxcrelease, lxcarch, buildmachine):
    self.container = LXCContainer(buildmachine, self.logger)
    staticIP = self.config['lbs']['Machines'][buildmachine]
    result = self.container.createmachine(lxcdistro, lxcrelease, lxcarch, staticIP)
    return result

  def GetAvailableBuildMachine(self, buildjob):
    for buildmachine in self.config['lbs']['Machines']:
      if not os.path.exists(self.MachineAvailabilityPath + "/" + buildmachine):
        # init the machine
        os.makedirs(self.MachineAvailabilityPath + "/" + buildmachine, exist_ok=True)
        open(self.MachineAvailabilityPath + "/" + buildmachine + "/available", 'a').close()
      if os.path.isfile(self.MachineAvailabilityPath + "/" + buildmachine + "/available"):
        os.unlink(self.MachineAvailabilityPath + "/" + buildmachine + "/available")
        with open(self.MachineAvailabilityPath + "/" + buildmachine + "/building", 'a') as f:
          f.write(buildjob)
        return buildmachine
    return None

  def ReleaseMachine(self, buildmachine):
    if os.path.isfile(self.MachineAvailabilityPath + "/" + buildmachine + "/building"):
      LXCContainer(buildmachine, self.logger).stop()
      os.unlink(self.MachineAvailabilityPath + "/" + buildmachine + "/building")
    open(self.MachineAvailabilityPath + "/" + buildmachine + "/available", 'a').close()

  def GetBuildMachineState(self, buildmachine):
    if os.path.isfile(self.MachineAvailabilityPath + "/" + buildmachine + "/building"):
      with open(self.MachineAvailabilityPath + "/" + buildmachine + "/building", "r") as f:
        buildjob = f.read()
      return ("building", buildjob)
    if os.path.isfile(self.MachineAvailabilityPath + "/" + buildmachine + "/available"):
      return "available"
    return "undefined"

  def buildpackage(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildmachine):
    userconfig = self.config['lbs']['Users'][username]
    self.logger.startTimer()
    self.logger.print(" * Starting at " + strftime("%Y-%m-%d %H:%M:%S GMT%z"))
    self.logger.print(" * Preparing the machine...")
    if self.createbuildmachine(lxcdistro, lxcrelease, lxcarch, buildmachine):

      try:
        # install a mount for the project repo
        self.container.installmount("/root/repo", "/var/www/repos/" + username + "/" + projectname + "/" + lxcdistro + "/" + lxcrelease)
        self.container.installmount("/root/tarball", "/var/www/tarballs/" + username + "/" + projectname)
      
        # prepare container, install packages that the build requires; this is specific to the distro
        self.buildHelper = BuildHelperFactory.GetBuildHelper(lxcdistro, self.container, "lbs-" + projectname + "-master", username, projectname, packagename)
        if not self.buildHelper.PrepareMachineBeforeStart():
          raise Exception("Problem with PrepareMachineBeforeStart")
        if self.container.startmachine():
          self.logger.print("container has been started successfully")
        if not self.buildHelper.PrepareMachineAfterStart():
          raise Exception("Problem with PrepareMachineAfterStart")
        if not self.buildHelper.PrepareForBuilding():
          raise Exception("Problem with PrepareForBuilding")

        # get the sources of the packaging instructions
        lbsproject=userconfig['GitURL'] + 'lbs-' + projectname
        pathSrc="/var/lib/lbs/src/"+username+"/"
        os.makedirs(pathSrc, exist_ok=True)
        if os.path.isdir(pathSrc+'lbs-'+projectname):
          #we want a clean clone
          shutil.rmtree(pathSrc+'lbs-'+projectname)
        self.container.executeshell("cd " + pathSrc + "; git clone " + lbsproject)
        if not os.path.isdir(pathSrc+'lbs-'+projectname):
          raise Exception("Problem with cloning the git repo")
        # copy the repo to the container
        shutil.copytree(pathSrc+'lbs-'+projectname, self.container.getrootfs() + "/root/lbs-"+projectname)

        if not self.buildHelper.InstallRequiredPackages(self.config['lbs']['LBSUrl']):
          raise Exception("Problem with InstallRequiredPackages")
        if not self.buildHelper.DownloadSources():
          raise Exception("Problem with DownloadSources")
        if not self.buildHelper.SetupEnvironment(branchname):
          raise Exception("Setup script did not succeed")
        if not self.buildHelper.BuildPackage(self.config['lbs']['LBSUrl']):
          raise Exception("Problem with building the package")
        self.logger.print("Success!")
      except Exception as e:
        self.logger.print("LBSERROR: "+str(e))
      finally:  
        # destroy the container
        self.container.stop()
        # self.container.destroy()
        self.ReleaseMachine(buildmachine)
    else:
      self.logger.print("LBSERROR: There is a problem with creating the container!")
    self.finished = True
    logpath=self.logger.getLogPath(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch)
    buildnumber=self.logger.store(self.config['lbs']['DeleteLogAfterDays'], self.config['lbs']['KeepMinimumLogs'], logpath)
    self.logger.email(self.config['lbs']['EmailFromAddress'], userconfig['EmailToAddress'], "LBS Result for " + projectname + "/" + packagename, self.config['lbs']['LBSUrl'] + "/logs/" + logpath + "/" + str(buildnumber))
    return self.logger.get()

