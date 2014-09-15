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

from RemoteContainer import RemoteContainer
from BuildHelper import BuildHelper
from BuildHelperFactory import BuildHelperFactory
from Logger import Logger
from Build import Build
from time import gmtime, strftime
import yaml
import os
import shutil
import time
from Shell import Shell
import logging
from threading import Thread
from collections import deque

class LightBuildServer:
  'light build server based on lxc and git'

  def __init__(self):
    self.MachineAvailabilityPath="/var/lib/lbs/machines"
    configfile="../config.yml"
    stream = open(configfile, 'r')
    self.config = yaml.load(stream)

    self.lbsList = {}
    self.recentlyFinishedLbsList = {}
    self.buildqueue = deque()
    self.ToBuild = deque()
    thread = Thread(target = self.buildqueuethread, args=())
    thread.start()

  def GetLbsName(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
    return username+"-"+projectname+"-"+packagename+"-"+branchname+"-"+lxcdistro+"-"+lxcrelease+"-"+lxcarch

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
      # check for hanging build (BuildingTimeout in config.yml)
      for lbsName in self.lbsList:
        lbs = self.lbsList[lbsName]
        if (lbs.buildmachine == buildmachine) and (lbs.logger.lastTimeUpdate + self.config['lbs']['BuildingTimeout'] < int(time.time())):
          self.ReleaseMachine(buildmachine)
    return None

  def ReleaseMachine(self, buildmachine):
    os.makedirs(self.MachineAvailabilityPath + "/" + buildmachine, exist_ok=True)
    staticIP = self.config['lbs']['Machines'][buildmachine]
    if not staticIP == None:
      LXCContainer(buildmachine, Logger()).stop()
    else:
      RemoteContainer(buildmachine, Logger()).stop()
    if os.path.isfile(self.MachineAvailabilityPath + "/" + buildmachine + "/building"):
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

  def getPackagingInstructions(self, userconfig, username, projectname):
    lbsproject=userconfig['GitURL'] + 'lbs-' + projectname
    pathSrc="/var/lib/lbs/src/"+username+"/"
    os.makedirs(pathSrc, exist_ok=True)
    if os.path.isdir(pathSrc+'lbs-'+projectname):
        #we want a clean clone
        shutil.rmtree(pathSrc+'lbs-'+projectname)
    shell = Shell(Logger())
    shell.executeshell("cd " + pathSrc + "; git clone " + lbsproject)
    if not os.path.isdir(pathSrc+'lbs-'+projectname):
      raise Exception("Problem with cloning the git repo")
    return pathSrc

  def CalculatePackageOrder(self, username, projectname, lxcdistro, lxcrelease, lxcarch):
    userconfig = self.config['lbs']['Users'][username]

    # get the sources of the packaging instructions
    self.getPackagingInstructions(userconfig, username, projectname)

    buildHelper = BuildHelperFactory.GetBuildHelper(lxcdistro, None, None, username, projectname, None)
    return buildHelper.CalculatePackageOrder(self.config, lxcdistro, lxcrelease, lxcarch)

  def BuildProject(self, username, projectname, lxcdistro, lxcrelease, lxcarch):
    packages=self.CalculatePackageOrder(username, projectname, lxcdistro, lxcrelease, lxcarch)

    if packages is None:
      message="Error: circular dependancy!"
    else:
      message=""
      branchname="master"
      for packagename in packages:
        # add package to build queue
        message += packagename + ", "
        lbsName=self.GetLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
        if lbsName in self.recentlyFinishedLbsList:
          del self.recentlyFinishedLbsList[lbsName]
        if not lbsName in self.lbsList:
          self.ToBuild.append(lbsName)
          self.buildqueue.append((username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch))

    return message

  def BuildProjectWithBranch(self, username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch):
    lbsName=self.GetLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
    if lbsName in self.recentlyFinishedLbsList:
      del self.recentlyFinishedLbsList[lbsName]
    if not lbsName in self.lbsList:
       self.ToBuild.append(lbsName)
       self.buildqueue.append((username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch))

  def BuildProjectWithBranchAndPwd(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, auth_username, password):
    lbsName=self.GetLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
    if not lbsName in self.lbsList:
      self.ToBuild.append(lbsName)
      self.buildqueue.append((username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch))
      return "Build for {{lbsName}} has been triggered."
    else:
      return "{{lbsName}} is already in the build queue."

  def WaitForBuildJobFinish(self, thread, lbsName):
      thread.join()
      self.recentlyFinishedLbsList[lbsName] = self.lbsList[lbsName]
      del self.lbsList[lbsName]

  def buildqueuethread(self):
      while True:
        if len(self.buildqueue) > 0:
          # peek at the leftmost item
          item = self.buildqueue[0]
          username = item[0]
          projectname = item[1]
          packagename = item[2]
          branchname = item[3]
          lxcdistro = item[4]
          lxcrelease = item[5]
          lxcarch = item[6]
          lbs = Build(self, Logger())
          lbsName=self.GetLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
          # get name of available slot
          buildmachine=self.GetAvailableBuildMachine(buildjob=username+"/"+projectname+"/"+packagename+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease+"/"+lxcarch)
          if not buildmachine == None:
            self.lbsList[lbsName] = lbs
            thread = Thread(target = lbs.buildpackage, args = (username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildmachine))
            thread.start()
            threadWait = Thread(target = self.WaitForBuildJobFinish, args = (thread, lbsName))
            threadWait.start()
            self.ToBuild.remove(lbsName)
            self.buildqueue.remove(item)
        # sleep two seconds before looping through buildqueue again
        time.sleep(2)

  def LiveLog(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
        lbsName=self.GetLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
        if lbsName in self.lbsList:
          lbs = self.lbsList[lbsName]
        elif lbsName in self.recentlyFinishedLbsList:
          lbs = self.recentlyFinishedLbsList[lbsName]
        else:
          if lbsName in self.ToBuild:
            return ("We are waiting for a build machine to become available...", 10)
          else:
            return ("No build is planned for this package at the moment...", -1)

        if lbs.finished:
          output = lbs.logger.get()
          # stop refreshing
          timeout=-1
        else:
          output = lbs.logger.get(4000)
          timeout = 2

        return (output, timeout)

