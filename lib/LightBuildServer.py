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
    dbversion=4
 
    if not os.path.isfile(self.config['lbs']['SqliteFile']):
      con = self.ConnectDatabase()
      createTableStmt = """
CREATE TABLE build (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  status char(20) NOT NULL,
  username char(100) NOT NULL,
  projectname char(100) NOT NULL,
  packagename char(100) NOT NULL,
  branchname char(100) NOT NULL,
  distro char(20) NOT NULL,
  release char(20) NOT NULL,
  arch char(10) NOT NULL,
  avoidlxc INTEGER NOT NULL DEFAULT 0,
  avoiddocker INTEGER NOT NULL DEFAULT 0,
  dependsOnOtherProjects char(400) NOT NULL,
  buildmachine char(100),
  started TIMESTAMP,
  finished TIMESTAMP,
  hanging INTEGER default 0,
  buildsuccess char(20),
  buildnumber INTEGER)
"""
      con.execute(createTableStmt)
      createTableStmt = """
CREATE TABLE machine (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name char(100) NOT NULL,
  status char(40) NOT NULL,
  type char(20) NOT NULL DEFAULT 'docker',
  buildjob char(400),
  queue char(400),
  username char(100),
  projectname char(100),
  packagename char(100))
"""
      con.execute(createTableStmt)
      createTableStmt = """
CREATE TABLE log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  buildid INTEGER,
  line TEXT,
  created TIMESTAMP DEFAULT (datetime('now','localtime')))
"""
      con.execute(createTableStmt)
      con.execute("CREATE TABLE dbversion ( version INTEGER )")
      con.execute("INSERT INTO dbversion(version) VALUES(%d)" % (dbversion))
      con.commit()
    else:
      con = self.ConnectDatabase()
      cursor = con.cursor()
      cursor.execute("SELECT version FROM dbversion")
      currentdbversion = cursor.fetchone()[0]
      if currentdbversion != dbversion:
        if currentdbversion < 2:
          con.execute("ALTER TABLE build ADD COLUMN hanging INTEGER DEFAULT 0")
        if currentdbversion < 3:
          con.execute("ALTER TABLE machine ADD COLUMN type CHAR(20) NOT NULL DEFAULT 'docker'")
        if currentdbversion < 4:
          con.execute("ALTER TABLE build ADD COLUMN avoidlxc INTEGER NOT NULL DEFAULT 0")
          con.execute("ALTER TABLE build ADD COLUMN avoiddocker INTEGER NOT NULL DEFAULT 0")
        con.execute("UPDATE dbversion SET version = %d" % (dbversion))
        con.commit()

    con.execute("DELETE FROM machine")
    # keep WAITING build jobs
    con.execute("DELETE FROM build WHERE status='BUILDING'")
    con.execute("DELETE FROM log")
    for buildmachine in self.config['lbs']['Machines']:
      conf=self.config['lbs']['Machines'][buildmachine]
      if 'enabled' in conf and conf['enabled'] == False:
        continue
      type=('lxc' if ('type' in conf and conf['type'] == 'lxc') else 'docker')
      # init the machine
      con.execute("INSERT INTO machine('name', 'status', 'type') VALUES(?, ?, ?)", (buildmachine, 'AVAILABLE', type))
    con.commit()
    con.close()

  def ConnectDatabase(self):
    con = sqlite3.connect(
               self.config['lbs']['SqliteFile'],
               detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES, 
               timeout=self.config['lbs']['WaitForDatabase'])
    con.row_factory = sqlite3.Row
    return con

  def GetLbsName(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
    return username+"/"+projectname+"/"+packagename+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease+"/"+lxcarch

  def GetMachines(self):
    con = self.ConnectDatabase()
    cursor = con.cursor()
    stmt = "SELECT name FROM machine"
    cursor.execute(stmt)
    data = cursor.fetchall()
    cursor.close()
    con.close()
    result = []
    for row in data:
      result.append(row['name'])
    return result

  def GetAvailableBuildMachine(self, con, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, AvoidDocker, AvoidLXC):
    buildjob=username+"/"+projectname+"/"+packagename+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease+"/"+lxcarch
    queue=username+"/"+projectname+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease
    machineToUse=None
    machinePriorityToUse=101
    cursor = con.cursor()
    stmt = "SELECT * FROM machine WHERE status = 'AVAILABLE'"
    if AvoidDocker:
      stmt += " AND type <> 'docker'"
    if AvoidLXC:
      stmt += " AND type <> 'lxc'"
    cursor.execute(stmt)
    data = cursor.fetchall()
    cursor.close()
    for row in data:
      buildmachine=row['name']
      buildmachinePriority=100
      if 'priority' in self.config['lbs']['Machines'][buildmachine]:
        buildmachinePriority=self.config['lbs']['Machines'][buildmachine]['priority']
      if buildmachinePriority < machinePriorityToUse:
        machinePriorityToUse = buildmachinePriority
        machineToUse = buildmachine
    if machineToUse is not None:
      stmt = "UPDATE machine SET status=?,buildjob=?,queue=?,username=?,projectname=?,packagename=? WHERE name=? AND status='AVAILABLE'"
      cursor = con.cursor()
      cursor.execute(stmt, ('BUILDING', buildjob, queue, username, projectname, packagename, machineToUse))
      if cursor.rowcount == 0:
        con.commit()
        return None
      con.commit()
      print("GetAvailableBuildMachine found a free machine")
      return machineToUse
    return None

  def CheckForHangingBuild(self):
      # check for hanging build (BuildingTimeout in config.yml)
      con = self.ConnectDatabase()
      cursor = con.cursor()
      stmt = "SELECT * FROM build "
      stmt += "WHERE status = 'BUILDING' and hanging = 0 "
      stmt += "AND datetime(started,'+" + str(self.config['lbs']['BuildingTimeout']) + " seconds') < '" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "'"
      stmt += " ORDER BY id DESC"
      cursor.execute(stmt)
      data = cursor.fetchall()
      cursor.close()
      for row in data:
        stmt = "SELECT * FROM log WHERE buildid=? AND datetime(created,'+" + str(self.config['lbs']['BuildingTimeout']) + " seconds') > '" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "'"
        cursor = con.cursor()
        cursor.execute(stmt, (row['id'],))
        if cursor.fetchone() is None:
          # mark the build as hanging, so that we don't try to release the machine several times
          stmt = "UPDATE build SET hanging = 1 WHERE id = ?"
          cursor = con.cursor()
          cursor.execute(stmt, (row['id'],))
          con.commit()
          # check if the machine is still occupied with that build
          #stmt = "SELECT * FROM machine WHERE username = ? and projectname = ? and packagename = ? AND name = ?"
          #cursor = con.cursor()
          #cursor.execute(stmt, (row['username'], row['projectname'], row['packagename'], row['buildmachine']))
          #if cursor.fetchone() is None:
          #  # TODO mark build as stopped. do not release the machine, it might already build something else?
          #  con.close()
          #  return
          print("stopping machine %s because of hanging build %d" % (row["buildmachine"], row["id"]))
          print("current time: %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
          print("sql statement: %s", (stmt))
          con.close()
          self.ReleaseMachine(row["buildmachine"])
          # when the build job realizes that the buildmachine is gone:
          #   the log will be written, email sent, and logs cleared
          #   the build will be marked as failed as well
          return
      con.close()

  def CancelPlannedBuild(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
      con = self.ConnectDatabase()
      cursor = con.cursor()
      cursor.execute("SELECT * FROM build WHERE status='WAITING' AND username=? AND projectname=? AND packagename=? AND branchname=? AND distro=? AND release=? AND arch=? ORDER BY id ASC", (username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch))
      data = cursor.fetchall()
      for row in data:
        con.execute("UPDATE build SET status = 'CANCELLED' WHERE id=?", (row['id'],))
        # only remove one build job from the queue
        break;
      con.commit()
      cursor.close()
      con.close()

  def ReleaseMachine(self, buildmachine):
    print("ReleaseMachine %s" % (buildmachine))
    status = self.GetBuildMachineState(buildmachine)

    # only release the machine when it is building. if it is already being stopped, do nothing
    if status["status"] == 'BUILDING' or status["status"] == 'STOPPING':
      con = self.ConnectDatabase()
      stmt = "UPDATE machine SET status='STOPPING' WHERE name = ?"
      con.execute(stmt, (buildmachine,))
      con.commit()
      con.close()

      conf=self.config['lbs']['Machines'][buildmachine]
      if 'type' in conf and conf['type'] == 'lxc':
        LXCContainer(buildmachine, conf, Logger(), '').stop()
      else:
        DockerContainer(buildmachine, conf, Logger(), '').stop()

      con = self.ConnectDatabase()
      stmt = "UPDATE machine SET status='AVAILABLE' WHERE name = ?"
      con.execute(stmt, (buildmachine,))
      con.commit()
      con.close()

  def GetBuildMachineState(self, buildmachine):
    con = self.ConnectDatabase()
    cursor = con.cursor()
    stmt = "SELECT status, buildjob, queue, type FROM machine WHERE name = ?"
    cursor.execute(stmt, (buildmachine,))
    data = cursor.fetchone()
    cursor.close()
    con.close()

    if data:
      if data["status"] == 'BUILDING':
        return data
      if data["status"] == 'AVAILABLE':
        return data
      if data["status"] == 'STOPPING':
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
    con = self.ConnectDatabase()
    cursor = con.cursor()
    stmt = "SELECT * FROM machine WHERE status = ? AND username = ? AND projectname = ?"
    cursor.execute(stmt, ('BUILDING', username, projectname))
    data = cursor.fetchone()
    cursor.close()
    con.close()

    if data is not None:
          # there is a machine building a package of the specified project
          return True
    return False

  # this is called from Build.py buildpackage, and from LightBuildServer.py CalculatePackageOrder
  def getPackagingInstructions(self, userconfig, username, projectname, branchname):
    gitprojectname = projectname
    if 'GitProjectName' in userconfig['Projects'][projectname]:
      gitprojectname = userconfig['Projects'][projectname]['GitProjectName']
    lbsproject=userconfig['GitURL'] + 'lbs-' + gitprojectname
    pathSrc=self.config['lbs']['GitSrcPath']+"/"+username+"/"

    # first try with git branch master, to see if the branch is decided in the setup.sh. then there must be a config.yml
    self.getPackagingInstructionsInternal(userconfig, username, projectname, "master", gitprojectname, lbsproject, pathSrc)

    if not os.path.isfile(pathSrc+'lbs-'+projectname+"/config.yml"):
      self.getPackagingInstructionsInternal(userconfig, username, projectname, branchname, gitprojectname, lbsproject, pathSrc)
    return pathSrc

  def getPackagingInstructionsInternal(self, userconfig, username, projectname, branchname, gitprojectname, lbsproject, pathSrc):
    os.makedirs(pathSrc, exist_ok=True)
    if os.path.isdir(pathSrc+'lbs-'+projectname):
        #we want a clean clone
        #but do not delete the tree if it is being used by another build
        if os.path.isfile(pathSrc+'lbs-'+projectname+'-lastused'):
          t = os.path.getmtime(pathSrc+'lbs-'+projectname+'-lastused')
          # delete the tree only if the last access was more than 2 minutes ago
          if (time.time() - t) > 120:
            shutil.rmtree(pathSrc+'lbs-'+projectname)
        else:
          # for existing projects, that did not have the lastused file yet
          shutil.rmtree(pathSrc+'lbs-'+projectname)

    # update the timestamp
    if os.path.isfile(pathSrc+'lbs-'+projectname+'-lastused'):
      os.utime(pathSrc+'lbs-'+projectname+'-lastused')
    else:
      open(pathSrc+'lbs-'+projectname+'-lastused', 'a').close()

    if os.path.isdir(pathSrc+'lbs-'+projectname):
      # we can reuse the existing source, it was used just recently
      return

    shell = Shell(Logger())
    if not 'GitType' in userconfig or userconfig['GitType'] == 'github':
      url=lbsproject + "/archive/" + branchname + ".tar.gz"
      cmd="cd " + pathSrc + ";";
      cmd+="rm -f " + branchname + ".tar.gz && curl --retry 10 --retry-delay 30 -f -L -o " + branchname + ".tar.gz \"" + url + "\" && "
      cmd+="tar xzf " + branchname + ".tar.gz; mv lbs-" + gitprojectname + "-" + branchname + " lbs-" + projectname
      shell.executeshell(cmd)
    elif userconfig['GitType'] == 'gitlab':
      url=lbsproject + "/repository/archive.tar.gz?ref=" + branchname
      tokenfilename=self.config["lbs"]["SSHContainerPath"] + "/" + username + "/" + projectname + "/gitlab_token"
      if os.path.isfile(tokenfilename):
        with open (tokenfilename, "r") as myfile:
          url+="&private_token="+myfile.read().strip()
      cmd="cd " + pathSrc + ";";
      cmd+="rm -f source.tar.gz lbs-" + gitprojectname + "* && curl --retry 10 --retry-delay 30 -f -o source.tar.gz \"" + url + "\" && "
      cmd+="tar xzf source.tar.gz; mv lbs-" + gitprojectname + "* lbs-" + projectname
      shell.executeshell(cmd)
    if not os.path.isdir(pathSrc+'lbs-'+projectname):
      raise Exception("Problem with cloning the git repo")

  def CalculatePackageOrder(self, username, projectname, branchname, lxcdistro, lxcrelease, lxcarch):
    userconfig = self.config['lbs']['Users'][username]

    # get the sources of the packaging instructions
    self.getPackagingInstructions(userconfig, username, projectname, branchname)

    buildHelper = BuildHelperFactory.GetBuildHelper(lxcdistro, None, username, projectname, None)
    return buildHelper.CalculatePackageOrder(self.config, lxcdistro, lxcrelease, lxcarch)

  def AddToBuildQueue(self, username, projectname, packagename, branchname, distro, release, arch):
    # find if this project depends on other projects
    DependsOnOtherProjects={}
    proj=self.config['lbs']['Users'][username]['Projects'][projectname]
    if 'DependsOn' in proj:
      DependsOnOtherProjects=proj['DependsOn']
    dependsOnString=','.join(DependsOnOtherProjects)
    avoiddocker = False if ("UseDocker" not in proj) else (proj["UseDocker"] == False)
    avoidlxc = False if ("UseLXC" not in proj) else (proj["UseLXC"] == False)

    con = self.ConnectDatabase()
    stmt = "INSERT INTO build(status,username,projectname,packagename,branchname,distro,release,arch,avoiddocker,avoidlxc,dependsOnOtherProjects) VALUES(?,?,?,?,?,?,?,?,?,?,?)"
    con.execute(stmt, ('WAITING', username, projectname, packagename, branchname, distro, release, arch, avoiddocker, avoidlxc, dependsOnString))
    con.commit()
    con.close()

  def BuildProject(self, username, projectname, branchname, lxcdistro, lxcrelease, lxcarch):
    packages=self.CalculatePackageOrder(username, projectname, branchname, lxcdistro, lxcrelease, lxcarch)

    if packages is None:
      message="Error: circular dependancy!"
    else:
      message=""
      for packagename in packages:
        # add package to build queue
        message += packagename + ", "
        job = self.GetJob(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch, "AND (status = 'WAITING' OR status='BUILDING')")
        if job is None:
          self.AddToBuildQueue(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch)

    return message

  def BuildProjectWithBranch(self, username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch):
    job = self.GetJob(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch, "AND (status = 'WAITING' OR status='BUILDING')")
    if job is None:
      self.AddToBuildQueue(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch)

  def BuildProjectWithBranchAndPwd(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, auth_username, password):
    job = self.GetJob(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch, "AND (status = 'WAITING' OR status='BUILDING')")
    if job is None:
      self.AddToBuildQueue(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch)
      return "Build for {{lbsName}} has been triggered."
    else:
      return "{{lbsName}} is already in the build queue."

  def attemptToFindBuildMachine(self, con, item):
    username = item["username"]
    projectname = item["projectname"]
    packagename = item["packagename"]
    branchname = item["branchname"]
    lxcdistro = item["distro"]
    lxcrelease = item["release"]
    lxcarch = item["arch"]
    DependsOnOtherProjects = item["dependsOnOtherProjects"]
    AvoidDocker = item["avoiddocker"]
    AvoidLXC = item["avoidlxc"]

    # 1: check if there is a package building or waiting from the same user and buildtarget => return False
    if self.CanFindMachineBuildingOnSameQueue(username,projectname,branchname,lxcdistro,lxcrelease,lxcarch):
      return False
      
    # 2: check if any project that this package depends on is still building or waiting => return False
    for DependantProjectName in DependsOnOtherProjects:
      if self.CanFindMachineBuildingProject(username, DependantProjectName):
        return False

    lbs = Build(self, Logger(item['id']))
    lbsName=self.GetLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
    # get name of available slot
    buildmachine=self.GetAvailableBuildMachine(con,username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch,AvoidDocker,AvoidLXC)
    if not buildmachine == None:
      stmt = "UPDATE build SET status='BUILDING', started=?, buildmachine=? WHERE id = ?"
      con.execute(stmt, (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), buildmachine, item['id']))
      con.commit()
      thread = Thread(target = lbs.buildpackage, args = (username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildmachine, item['id']))
      thread.start()
      return True
    return False

  # needs to be called regularly from outside
  def ProcessBuildQueue(self):
      # loop from left to right
      # check if a project might be ready to build
      con = self.ConnectDatabase()
      cursor = con.cursor()
      cursor.execute("SELECT * FROM build WHERE status='WAITING' ORDER BY id ASC")
      data = cursor.fetchall()
      for row in data:
        self.attemptToFindBuildMachine(con, row)
      cursor.close()
      con.close()
      self.CheckForHangingBuild()

  def LiveLog(self, username, projectname, packagename, branchname, distro, release, arch):
      data = self.GetJob(username, projectname, packagename, branchname, distro, release, arch, "")
      if data is None:
        return ("No build is planned for this package at the moment...", -1)
      elif data['status'] == 'BUILDING':
        rowsToShow=40
        con = self.ConnectDatabase()
        cursor = con.cursor()
        stmt = "SELECT * FROM log WHERE buildid = ? ORDER BY id DESC LIMIT ?"
        cursor.execute(stmt, (data['id'], rowsToShow))
        data = cursor.fetchall()
        con.close()
        output = ""
        for row in data:
          output = row['line'] + output
        timeout = 2
      elif data['status'] == 'CANCELLED':
        return ("This build has been removed from the build queue...", -1)
      elif data['status'] == 'WAITING':
        return ("We are waiting for a build machine to become available...", 10)
      elif data['status'] == 'FINISHED':
        output = Logger().getLog(username, projectname, packagename, branchname, distro, release, arch, data['buildnumber'])
        # stop refreshing
        timeout=-1

      return (output, timeout)

  def GetJob(self,username, projectname, packagename, branchname, distro, release, arch, where):
      con = self.ConnectDatabase()
      cursor = con.cursor()
      stmt = "SELECT * FROM build "
      stmt += "WHERE username = ? AND projectname = ? AND packagename = ? AND branchname = ? AND distro = ? AND release = ? AND arch = ? "
      stmt += where
      stmt += " ORDER BY id DESC"
      cursor.execute(stmt, (username, projectname, packagename, branchname, distro, release, arch))
      data = cursor.fetchone()
      cursor.close()
      con.close()
      return data

  def GetBuildQueue(self):
      con = self.ConnectDatabase()
      cursor = con.cursor()
      cursor.execute("SELECT * FROM build WHERE status='WAITING' ORDER BY id ASC")
      data = cursor.fetchall()
      con.close()
      result = deque()
      for row in data:
        result.append(row)
      return result

  def GetFinishedQueue(self):
      con = self.ConnectDatabase()
      cursor = con.cursor()
      cursor.execute("SELECT * FROM build WHERE status='FINISHED' ORDER BY finished DESC LIMIT ?", (self.config['lbs']['ShowNumberOfFinishedJobs'],))
      data = cursor.fetchall()
      con.close()
      result = deque()
      for row in data:
        result.append(row)
      return result

