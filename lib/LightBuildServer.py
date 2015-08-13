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
from Logger import Logger
import Config
from Build import Build
from time import gmtime, strftime
import os
import shutil
import time
import datetime
from Shell import Shell
import logging
from threading import Thread, Lock
from collections import deque
import sqlite3

class LightBuildServer:
  'light build server based on lxc and git'

  def __init__(self):
    self.config = Config.LoadConfig()
 
    if not os.path.isfile(self.config['lbs']['SqliteFile']):
      con = sqlite3.connect(self.config['lbs']['SqliteFile'])
      createTableStmt = """
CREATE TABLE build (
  id INTEGER PRIMARY KEY,
  status char(20) NOT NULL,
  username char(100) NOT NULL,
  projectname char(100) NOT NULL,
  packagename char(100) NOT NULL,
  branchname char(100) NOT NULL,
  distro char(20) NOT NULL,
  release char(20) NOT NULL,
  arch char(10) NOT NULL,
  dependsOnOtherProjects char(400) NOT NULL,
  started DATETIME,
  finished DATETIME)
"""
      con.execute(createTableStmt)
      createTableStmt = """
CREATE TABLE machine (
  id INTEGER PRIMARY KEY,
  name char(100) NOT NULL,
  status char(40) NOT NULL,
  buildjob char(400),
  queue char(400),
  username char(100),
  projectname char(100),
  packagename char(100))
"""
      con.execute(createTableStmt)
      con.commit()
    else:
      con = sqlite3.connect(self.config['lbs']['SqliteFile'])

    con.execute("DELETE FROM machine")
    con.execute("DELETE FROM build WHERE status = 'WAITING' OR status='BUILDING'")
    for buildmachine in self.config['lbs']['Machines']:
      # init the machine
      con.execute("INSERT INTO machine('name', 'status') VALUES(?, ?)", (buildmachine, 'AVAILABLE'))
    con.commit()
    con.close()

# TODO still needed?
    self.lbsList = {}
# TODO    self.buildqueue = deque()
# TODO    self.finishedqueue = deque()

    thread = Thread(target = self.buildqueuethread, args=())
    thread.start()

  def GetLbsName(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
    return username+"/"+projectname+"/"+packagename+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease+"/"+lxcarch

  def GetAvailableBuildMachine(self, con, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
    buildjob=username+"/"+projectname+"/"+packagename+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease+"/"+lxcarch
    queue=username+"/"+projectname+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease
    machineToUse=None
    machinePriorityToUse=101
    for buildmachine in self.config['lbs']['Machines']:
      state = self.GetBuildMachineState(buildmachine)
      if state['status'] == 'AVAILABLE':
        buildmachinePriority=100
        if 'priority' in self.config['lbs']['Machines'][buildmachine]:
          buildmachinePriority=self.config['lbs']['Machines'][buildmachine]['priority']
        if buildmachinePriority < machinePriorityToUse:
          machinePriorityToUse = buildmachinePriority
          machineToUse = buildmachine
    if machineToUse is not None:
      stmt = "UPDATE machine SET status=?,buildjob=?,queue=?,username=?,projectname=?,packagename=? WHERE name=?"
      con.execute(stmt, ('BUILDING', buildjob, queue, username, projectname, packagename, machineToUse))
      con.commit()
      return machineToUse
    return None

  def CheckForHangingBuild(self):
      # check for hanging build (BuildingTimeout in config.yml)
      for lbsName in self.lbsList:
        lbs = self.lbsList[lbsName]
        if (lbs.logger.lastTimeUpdate + self.config['lbs']['BuildingTimeout'] < int(time.time())):
          self.ReleaseMachine(lbs.buildmachine)

  def ReleaseMachine(self, buildmachine):
    conf=self.config['lbs']['Machines'][buildmachine]
    if 'type' in conf and conf['type'] == 'lxc':
      LXCContainer(buildmachine, conf, Logger()).stop()
    else:
      DockerContainer(buildmachine, conf, Logger()).stop()
    con = sqlite3.connect(self.config['lbs']['SqliteFile'])
    stmt = "UPDATE machine SET status='AVAILABLE' WHERE name = ?"
    con.execute(stmt, (buildmachine,))
    con.commit()
    con.close()

  def GetBuildMachineState(self, buildmachine):
    con = sqlite3.connect(self.config['lbs']['SqliteFile'])
    con.row_factory = sqlite3.Row
    cursor = con.cursor()
    stmt = "SELECT status, buildjob, queue FROM machine WHERE name = ?"
    cursor.execute(stmt, (buildmachine,))
    data = cursor.fetchone()
    cursor.close()
    con.close()

    if data:
      if data["status"] == 'BUILDING':
        return data
      if data["status"] == 'AVAILABLE':
        return data
    undefined = {}
    undefined["status"] = "undefined"
    return undefined

  def CanFindMachineBuildingOnSameQueue(self, username, projectname, branchname, lxcdistro, lxcrelease, lxcarch):
    queue=username+"/"+projectname+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease
    for buildmachine in self.config['lbs']['Machines']:
      state = self.GetBuildMachineState(buildmachine)
      if state['status'] == 'BUILDING':
        if state['queue'] == queue:
          # there is a machine building a package on the same queue (same user, project, branch, distro, release, arch)
          return True
    return False

  def CanFindMachineBuildingProject(self, username, projectname):
    for buildmachine in self.config['lbs']['Machines']:
      if self.machines[buildmachine]['status'] == 'BUILDING':
        if self.machines[buildmachine]['username'] == username and self.machines[buildmachine]['projectname'] == projectname:
          # there is a machine building a package of the specified project
          return True
    return False

  def getPackagingInstructions(self, userconfig, username, projectname):
    gitprojectname = projectname
    if 'GitProjectName' in userconfig['Projects'][projectname]:
      gitprojectname = userconfig['Projects'][projectname]['GitProjectName']
    lbsproject=userconfig['GitURL'] + 'lbs-' + gitprojectname
    pathSrc="/var/lib/lbs/src/"+username+"/"
    os.makedirs(pathSrc, exist_ok=True)
    if os.path.isdir(pathSrc+'lbs-'+projectname):
        #we want a clean clone
        shutil.rmtree(pathSrc+'lbs-'+projectname)
    shell = Shell(Logger())
    if not 'GitType' in userconfig or userconfig['GitType'] == 'github':
      url=lbsproject + "/archive/master.tar.gz"
      cmd="cd " + pathSrc + ";";
      cmd+="curl --retry 10 --retry-delay 30 -f -L -o master.tar.gz \"" + url + "\";"
      cmd+="tar xzf master.tar.gz; mv lbs-" + gitprojectname + "-master lbs-" + projectname
      shell.executeshell(cmd)
    elif userconfig['GitType'] == 'gitlab':
      url=lbsproject + "/repository/archive.tar.gz?ref=master"
      tokenfilename=self.config["lbs"]["SSHContainerPath"] + "/" + username + "/" + projectname + "/gitlab_token"
      if os.path.isfile(tokenfilename):
        with open (tokenfilename, "r") as myfile:
          url+="&private_token="+myfile.read().strip()
      cmd="cd " + pathSrc + ";";
      cmd+="curl --retry 10 --retry-delay 30 -f -o source.tar.gz \"" + url + "\";"
      cmd+="tar xzf source.tar.gz; mv lbs-" + gitprojectname + ".git lbs-" + projectname
      shell.executeshell(cmd)
    if not os.path.isdir(pathSrc+'lbs-'+projectname):
      raise Exception("Problem with cloning the git repo")
    return pathSrc

  def CalculatePackageOrder(self, username, projectname, lxcdistro, lxcrelease, lxcarch):
    userconfig = self.config['lbs']['Users'][username]

    # get the sources of the packaging instructions
    self.getPackagingInstructions(userconfig, username, projectname)

    buildHelper = BuildHelperFactory.GetBuildHelper(lxcdistro, None, username, projectname, None)
    return buildHelper.CalculatePackageOrder(self.config, lxcdistro, lxcrelease, lxcarch)

  def AddToBuildQueue(self, username, projectname, packagename, branchname, distro, release, arch):
    # find if this project depends on other projects
    DependsOnOtherProjects={}
    if 'DependsOn' in self.config['lbs']['Users'][username]['Projects'][projectname]:
      DependsOnOtherProjects=self.config['lbs']['Users'][username]['Projects'][projectname]['DependsOn']
    dependsOnString=','.join(DependsOnOtherProjects)

    con = sqlite3.connect(self.config['lbs']['SqliteFile'])
    stmt = "INSERT INTO build(status,username,projectname,packagename,branchname,distro,release,arch,dependsOnOtherProjects) VALUES(?,?,?,?,?,?,?,?,?)"
    con.execute(stmt, ('WAITING', username, projectname, packagename, branchname, distro, release, arch, dependsOnString))
    con.commit()
    con.close()

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
        if not lbsName in self.lbsList:
          self.AddToBuildQueue(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch)

    return message

  def BuildProjectWithBranch(self, username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch):
    lbsName=self.GetLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
    if not lbsName in self.lbsList:
       self.AddToBuildQueue(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch)

  def BuildProjectWithBranchAndPwd(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, auth_username, password):
    lbsName=self.GetLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
    if not lbsName in self.lbsList:
      self.AddToBuildQueue(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch)
      return "Build for {{lbsName}} has been triggered."
    else:
      return "{{lbsName}} is already in the build queue."

  def WaitForBuildJobFinish(self, thread, lbsName, jobId):
      thread.join()
      con = sqlite3.connect(self.config['lbs']['SqliteFile'])
      stmt = "UPDATE build SET status='FINISHED', finished=? WHERE id = ?"
      con.execute(stmt, (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), jobId))
      con.commit()
      del self.lbsList[lbsName]

  def attemptToFindBuildMachine(self, con, item):
    username = item["username"]
    projectname = item["projectname"]
    packagename = item["packagename"]
    branchname = item["branchname"]
    lxcdistro = item["distro"]
    lxcrelease = item["release"]
    lxcarch = item["arch"]
    DependsOnOtherProjects = item["dependsOnOtherProjects"]

    # 1: check if there is a package building or waiting from the same user and buildtarget => return False
    if self.CanFindMachineBuildingOnSameQueue(username,projectname,branchname,lxcdistro,lxcrelease,lxcarch):
      return False
      
    # 2: check if any project that this package depends on is still building or waiting => return False
    for DependantProjectName in DependsOnOtherProjects:
      if self.CanFindMachineBuildingProject(username, DependantProjectName):
        return False

    lbs = Build(self, Logger())
    lbsName=self.GetLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
    # get name of available slot
    buildmachine=self.GetAvailableBuildMachine(con,username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
    if not buildmachine == None:
      self.lbsList[lbsName] = lbs
      thread = Thread(target = lbs.buildpackage, args = (username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildmachine))
      thread.start()
      threadWait = Thread(target = self.WaitForBuildJobFinish, args = (thread, lbsName, item['id']))
      threadWait.start()
      stmt = "UPDATE build SET status='BUILDING', started=? WHERE id = ?"
      con.execute(stmt, (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), item['id']))
      con.commit()
      return True
    return False

  def buildqueuethread(self):
      con = sqlite3.connect(self.config['lbs']['SqliteFile'])
      con.row_factory = sqlite3.Row
      cursor = con.cursor()

      while True:
        # loop from left to right
        # check if a project might be ready to build
        cursor.execute("SELECT * FROM build WHERE status='WAITING' ORDER BY id ASC")
        data = cursor.fetchall()
        for row in data:
          if self.attemptToFindBuildMachine(con, row):
            break
        self.CheckForHangingBuild()
        # sleep two seconds before looping through buildqueue again
        time.sleep(2)

      cursor.close()
      con.close()

  def LiveLog(self, username, projectname, packagename, branchname, distro, release, arch):
      lbsName=self.GetLbsName(username,projectname,packagename,branchname,distro,release,arch)

      if lbsName in self.lbsList:
        lbs = self.lbsList[lbsName]
        output = lbs.logger.get(4000)
        timeout = 2
      else:
        con = sqlite3.connect(self.config['lbs']['SqliteFile'])
        con.row_factory = sqlite3.Row
        cursor = con.cursor()
        stmt = """
SELECT * FROM build 
WHERE username = ? 
AND projectname = ?
AND packagename = ?
AND branchname = ?
AND distro = ?
AND release = ?
AND arch = ?
ORDER BY id DESC
"""
        cursor.execute(stmt, (username, projectname, packagename, branchname, distro, release, arch))
        data = cursor.fetchone()
        cursor.close()
        con.close()
        if data is None:
          return ("No build is planned for this package at the moment...", -1)
        elif data['status'] == 'WAITING':
          return ("We are waiting for a build machine to become available...", 10)
        elif data['status'] == 'FINISHED':
          output = Logger().getLastBuildLog(username, projectname, packagename, branchname, distro, release, arch)
          # stop refreshing
          timeout=-1

      return (output, timeout)

  def GetBuildQueue(self):
      # TODO
      return deque()

  def GetFinishedQueue(self):
      # TODO
      # only get last jobs that have finished, self.config['lbs']['ShowNumberOfFinishedJobs']
      return deque()

