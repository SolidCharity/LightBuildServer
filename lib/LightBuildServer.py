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

  def __init__(self, logger, username):
    self.logger = logger
    self.container = None
    self.finished = False
    configfile="../config.yml"
    stream = open(configfile, 'r')
    self.config = yaml.load(stream)
    self.username=username
    self.userconfig = self.config['lbs']['Users'][username]

  def createbuildmachine(self, lxcdistro, lxcrelease, lxcarch, buildmachine, staticIP):
    self.container = LXCContainer(buildmachine, self.logger)
    result = self.container.createmachine(lxcdistro, lxcrelease, lxcarch, staticIP)
    return result

  def buildpackage(self, projectname, packagename, lxcdistro, lxcrelease, lxcarch, buildmachine, staticIP):
    self.logger.print(" * Starting at " + strftime("%Y-%m-%d %H:%M:%S GMT%z"));
    self.logger.print(" * Preparing the machine...");
    if self.createbuildmachine(lxcdistro, lxcrelease, lxcarch, buildmachine, staticIP):

      # install a mount for the project repo
      self.container.installmount("/root/repo", "/var/www/repos/" + projectname + "/" + lxcdistro + "/" + lxcrelease + "/" + lxcarch)
      self.container.installmount("/root/tarball", "/var/www/tarballs/" + projectname)
      
      # prepare container, install packages that the build requires; this is specific to the distro
      self.buildHelper = BuildHelperFactory.GetBuildHelper(lxcdistro, self.container, "lbs-" + projectname + "-master", projectname, packagename)
      self.buildHelper.PrepareMachineBeforeStart() 
      if self.container.startmachine():
        self.logger.print("container has been started successfully")
      self.buildHelper.PrepareForBuilding()

      # get the sources of the packaging instructions
      lbsproject=self.userconfig['GitURL'] + 'lbs-' + projectname
      pathSrc="/var/lib/lbs/src/"+self.username+"/"
      os.makedirs(pathSrc, exist_ok=True)
      if os.path.isdir(pathSrc+'lbs-'+projectname):
        #we want a clean clone
        shutil.rmtree(pathSrc+'lbs-'+projectname)
      self.container.executeshell("cd " + pathSrc + "; git clone " + lbsproject)
      if not os.path.isdir(pathSrc+'lbs-'+projectname):
        self.logger.print("Problem with cloning the git repo")
        return self.logger.get()
      # copy the repo to the container
      shutil.copytree(pathSrc+'lbs-'+projectname, self.container.getrootfs() + "/root/lbs-"+projectname)

      self.buildHelper.InstallRequiredPackages()
      self.buildHelper.DownloadSources()
      self.buildHelper.SetupEnvironment()
      self.buildHelper.BuildPackage()
      # destroy the container
      self.container.stop();
      # self.container.destroy();
      self.logger.print("Success!")
    else:
      self.logger.print("There is a problem with creating the container!")
    self.finished = True
    logpath=self.username + "/" + projectname + "/" + packagename + "/" + lxcdistro + "/" + lxcrelease + "/" + lxcarch
    buildnumber=self.logger.store(self.config['lbs']['DeleteLogAfterDays'], logpath)
    self.logger.email(self.config['lbs']['EmailFromAddress'], self.userconfig['EmailToAddress'], "LBS Result for " + projectname + "/" + packagename, self.config['lbs']['LBSUrl'] + "/logs/" + logpath + "/" + str(buildnumber))
    return self.logger.get()

