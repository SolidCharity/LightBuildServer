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

class LightBuildServer:
  'light build server based on lxc and git'

  def __init__(self, logger):
    self.logger = logger
    self.container = None
    self.finished = False

  def createbuildmachine(self, lxcdistro, lxcrelease, lxcarch, buildmachine, staticIP):
    self.container = LXCContainer(buildmachine, self.logger)
    result = self.container.createmachine(lxcdistro, lxcrelease, lxcarch, staticIP)
    return result

  def buildpackage(self, projectname, packagename, lxcdistro, lxcrelease, lxcarch, buildmachine, staticIP):
    self.logger.print(" * Preparing the machine...");
    # TODO pick up github url from database
    lbsproject='https://github.com/tpokorra/lbs-' + projectname
    if self.createbuildmachine(lxcdistro, lxcrelease, lxcarch, buildmachine, staticIP):

      # install a mount for the project repo
      self.container.installmount("/root/repo", "/var/www/repos/" + projectname + "/" + lxcdistro + "/" + lxcrelease + "/" + lxcarch)
      
      # prepare container, install packages that the build requires; this is specific to the distro
      self.buildHelper = BuildHelperFactory.GetBuildHelper(lxcdistro, self.container, "lbs-" + projectname + "-master", projectname, packagename)
      self.buildHelper.PrepareMachineBeforeStart() 
      if self.container.startmachine():
        self.logger.print("container has been started successfully")
      self.buildHelper.PrepareForBuilding()

      # get the sources of the packaging instructions
      if not self.buildHelper.run("wget -O master.tar.gz " + lbsproject + "/archive/master.tar.gz"):
        return self.logger.get()
      if not self.buildHelper.run ("tar xzf master.tar.gz"):
        return self.logger.get()
      self.buildHelper.InstallRequiredPackages()
      self.buildHelper.DownloadSources()
      self.buildHelper.BuildPackage()
      # destroy the container
      self.container.stop();
      self.container.destroy();
      self.logger.print("Success!")
    else:
      self.logger.print("There is a problem with creating the container!")
    self.finished = True
    return self.logger.get()

  def runtests(self, projectname, packagename, lxcdistro, lxcrelease, lxcarch, buildmachine, staticIP):
    self.logger.print(" * Preparing the machine...");
    # TODO pick up github url from database
    lbsproject='https://github.com/tpokorra/lbs-' + projectname
    if self.createbuildmachine(lxcdistro, lxcrelease, lxcarch, buildmachine, staticIP):

      # prepare container, install packages that the build requires; this is specific to the distro
      self.buildHelper = BuildHelperFactory.GetBuildHelper(lxcdistro, self.container, "lbs-" + projectname + "-master", projectname, packagename)
      self.buildHelper.PrepareMachineBeforeStart() 
      if self.container.startmachine():
        self.logger.print("container has been started successfully")
      
      self.buildHelper.PrepareForBuilding()

      # get instructions for the test
      if not self.buildHelper.run("wget -O master.tar.gz " + lbsproject + "/archive/master.tar.gz"):
        return self.logger.get()
      if not self.buildHelper.run ("tar xzf master.tar.gz"):
        return self.logger.get()

      self.buildHelper.InstallTestEnvironment()
      self.buildHelper.RunTests()

      # destroy the container
      self.container.stop();
      self.container.destroy();
      self.logger.print("Success!")
    else:
      self.logger.print("There is a problem with creating the container!")
    self.finished = True
    return self.logger.get()
