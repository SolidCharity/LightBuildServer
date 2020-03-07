#!/usr/bin/env python3
"""Light Build Server: build packages for various distributions, using linux containers"""

# Copyright (c) 2014-2020 Timotheus Pokorra

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
from LXDContainer import LXDContainer
from CoprContainer import CoprContainer
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
import requests
from Shell import Shell
import logging
from threading import Thread, Lock
from collections import deque
from Database import Database

class LightBuildServer:
  'light build server based on lxc and git'

  def __init__(self):
    self.config = Config.LoadConfig()
    con = Database(self.config)
    con.createOrUpdate()

    con.execute("DELETE FROM machine")
    # keep WAITING build jobs
    con.execute("DELETE FROM build WHERE status='BUILDING'")
    con.execute("DELETE FROM log")
    for buildmachine in self.config['lbs']['Machines']:
      conf=self.config['lbs']['Machines'][buildmachine]
      if 'enabled' in conf and conf['enabled'] == False:
        continue
      if not 'type' in conf:
        # default to docker
        conf['type'] = 'docker'
      type=conf['type']
      static=('t' if ('static' in conf and conf['static'] == True) else 'f')
      priority=100
      if 'priority' in self.config['lbs']['Machines'][buildmachine]:
        priority=self.config['lbs']['Machines'][buildmachine]['priority']
      port = None
      if 'port' in self.config['lbs']['Machines'][buildmachine]:
        port = self.config['lbs']['Machines'][buildmachine]['port']
      cid = None
      if 'cid' in self.config['lbs']['Machines'][buildmachine]:
        cid = self.config['lbs']['Machines'][buildmachine]['cid']
      local = None
      if 'local' in self.config['lbs']['Machines'][buildmachine]:
        local = ('t' if (self.config['lbs']['Machines'][buildmachine]['local'] == True) else 'f')
      if type == "copr" and 'maxinstances' in conf:
        for c in range(0, conf['maxinstances']):
          # copr machines are always static
          con.execute("INSERT INTO machine(name, status, type, static, priority) VALUES(?,?,?,?,?)", (buildmachine + str(c), 'AVAILABLE', 'copr', 't', priority))
      else:
        # init the machine
        con.execute("INSERT INTO machine(name, status, type, static, priority, port, cid, local) VALUES(?,?,?,?,?,?,?,?)", (buildmachine, 'AVAILABLE', type, static, priority, port, cid, local))
    con.commit()
    con.close()

  def GetLbsName(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
    return username+"/"+projectname+"/"+packagename+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease+"/"+lxcarch

  def GetMachines(self):
    con = Database(self.config)
    stmt = "SELECT name FROM machine"
    cursor = con.execute(stmt)
    data = cursor.fetchall()
    cursor.close()
    con.close()
    result = []
    for row in data:
      result.append(row['name'])
    return result

  def GetAvailableBuildMachine(self, con, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, AvoidDocker, AvoidLXC, SpecificMachine):
    buildjob=username+"/"+projectname+"/"+packagename+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease+"/"+lxcarch
    queue=username+"/"+projectname+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease
    machineToUse=None
    machinePriorityToUse=101
    stmt = "SELECT * FROM machine WHERE status = 'AVAILABLE' "
    if AvoidDocker:
      stmt += " AND type <> 'docker'"
    if AvoidLXC:
      stmt += " AND type <> 'lxc' AND type <> 'lxd'"
    if SpecificMachine is None or SpecificMachine == '':
      stmt += " and static='f'"
      cursor = con.execute(stmt)
    else:
      stmt += " AND (name = ? OR (type = 'copr' AND name LIKE ? AND static='t'))"
      cursor = con.execute(stmt, (SpecificMachine, SpecificMachine + "%"))
    data = cursor.fetchall()
    cursor.close()
    for row in data:
      buildmachine=row['name']
      buildmachinePriority=row['priority']
      if buildmachinePriority < machinePriorityToUse:
        machinePriorityToUse = buildmachinePriority
        machineToUse = buildmachine
    if machineToUse is not None:
      stmt = "UPDATE machine SET status=?,buildjob=?,queue=?,username=?,projectname=?,packagename=? WHERE name=? AND status='AVAILABLE'"
      cursor = con.execute(stmt, ('BUILDING', buildjob, queue, username, projectname, packagename, machineToUse))
      if cursor.rowcount == 0:
        con.commit()
        return None
      con.commit()
      print("GetAvailableBuildMachine found a free machine: " + machineToUse)
      return machineToUse
    return None

  def CheckForHangingBuild(self):
      # check for hanging build (BuildingTimeout in config.yml)
      con = Database(self.config)
      stmt = "SELECT * FROM build "
      stmt += "WHERE status = 'BUILDING' and hanging = 0 "
      stmt += "AND datetime(started,'+" + str(self.config['lbs']['BuildingTimeout']) + " seconds') < '" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "'"
      stmt += " ORDER BY id DESC"
      cursor = con.execute(stmt)
      data = cursor.fetchall()
      cursor.close()
      for row in data:
        stmt = "SELECT * FROM log WHERE buildid=? AND datetime(created,'+" + str(self.config['lbs']['BuildingTimeout']) + " seconds') > '" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "'"
        cursor = con.execute(stmt, (row['id'],))
        if cursor.fetchone() is None:
          # mark the build as hanging, so that we don't try to release the machine several times
          stmt = "UPDATE build SET hanging = 1 WHERE id = ?"
          cursor = con.execute(stmt, (row['id'],))
          con.commit()
          # check if the machine is still occupied with that build
          #stmt = "SELECT * FROM machine WHERE username = ? and projectname = ? and packagename = ? AND name = ?"
          #cursor = con.execute(stmt, (row['username'], row['projectname'], row['packagename'], row['buildmachine']))
          #if cursor.fetchone() is None:
          #  # TODO mark build as stopped. do not release the machine, it might already build something else?
          #  con.close()
          #  return
          print("stopping machine %s because of hanging build %d" % (row["buildmachine"], row["id"]))
          print("current time: %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
          print("sql statement: %s" % (stmt))
          con.close()
          self.ReleaseMachine(row["buildmachine"], True)
          # when the build job realizes that the buildmachine is gone:
          #   the log will be written, email sent, and logs cleared
          #   the build will be marked as failed as well
          return
      con.close()

  def CancelPlannedBuild(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
      con = Database(self.config)
      cursor = con.execute("SELECT * FROM build WHERE status='WAITING' AND username=? AND projectname=? AND packagename=? AND branchname=? AND distro=? AND release=? AND arch=? ORDER BY id ASC", (username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch))
      data = cursor.fetchall()
      for row in data:
        cursor = con.execute("UPDATE build SET status = 'CANCELLED' WHERE id=?", (row['id'],))
        # only remove one build job from the queue
        break;
      con.commit()
      cursor.close()
      con.close()

  def CancelWaitingJobsInQueue(self, queue):
      con = Database(self.config)
      # TODO: add arch to the queue as well?
      # queue=username+"/"+projectname+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease
      cursor = con.execute("SELECT * FROM build WHERE status='WAITING' AND CONCAT_WS('/', username, projectname, branchname, distro, release) = ?", (queue,))
      data = cursor.fetchall()
      for row in data:
        cursor = con.execute("UPDATE build SET status = 'CANCELLED' WHERE id=?", (row['id'],))
      con.commit()
      cursor.close()
      con.close()

  def ReleaseMachine(self, buildmachine, jobFailed):
    print("ReleaseMachine %s" % (buildmachine))
    status = self.GetBuildMachineState(buildmachine)

    # only release the machine when it is building. if it is already being stopped, do nothing
    if status["status"] == 'BUILDING':
      if jobFailed:
        self.CancelWaitingJobsInQueue(status["queue"])
      con = Database(self.config)
      stmt = "UPDATE machine SET status='STOPPING' WHERE name = ?"
      cursor = con.execute(stmt, (buildmachine,))
      con.commit()

      stmt = "SELECT * FROM machine WHERE name = ?"
      cursor = con.execute(stmt, (buildmachine,))
      machine = cursor.fetchone()
      con.close()

      if machine['type'] == 'lxc':
        LXCContainer(buildmachine, machine, Logger(), '').stop()
      elif machine['type'] == 'lxd':
        LXDContainer(buildmachine, machine, Logger(), '').stop()
      elif machine['type'] == 'docker':
        DockerContainer(buildmachine, machine, Logger(), '').stop()
      elif machine['type'] == 'copr':
        CoprContainer(buildmachine, machine, Logger(), '').stop()

      con = Database(self.config)
      stmt = "UPDATE machine SET status='AVAILABLE' WHERE name = ?"
      cursor = con.execute(stmt, (buildmachine,))
      con.commit()
      con.close()

  def GetBuildMachineState(self, buildmachine):
    con = Database(self.config)
    stmt = "SELECT status, buildjob, queue, type, static, packagename FROM machine WHERE name = ?"
    cursor = con.execute(stmt, (buildmachine,))
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

  def CanFindDependanciesBuilding(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
    queue=username+"/"+projectname+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease
    con = Database(self.config)
    stmt = "SELECT status, buildjob, queue, type, static, packagename FROM machine WHERE status = 'BUILDING' AND queue = ?"
    cursor = con.execute(stmt, (queue,))
    data = cursor.fetchall()
    for row in data:
      # there is a machine building a package on the same queue (same user, project, branch, distro, release, arch)
      # does this package actually depend on that other package?
      dependantpackageid = self.GetPackageId(con, username, projectname, packagename, branchname)
      requiredpackageid = self.GetPackageId(con, username, projectname, row['packagename'], branchname)
      result = self.DoesPackageDependOnOtherPackage(con, dependantpackageid, requiredpackageid)
      if result:
        print("cannot build " + packagename + " because it depends on another package")
        con.close()
        return True
    con.close()
    return False

  def CanFindMachineBuildingProject(self, username, projectname):
    con = Database(self.config)
    stmt = "SELECT * FROM machine WHERE status = ? AND username = ? AND projectname = ?"
    cursor = con.execute(stmt, ('BUILDING', username, projectname))
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
    gitbranchname = "master"
    if 'GitProjectName' in userconfig['Projects'][projectname]:
      gitprojectname = userconfig['Projects'][projectname]['GitProjectName']
    if 'GitBranchName' in userconfig['Projects'][projectname]:
      gitbranchname = userconfig['Projects'][projectname]['GitBranchName']
    lbsproject=userconfig['GitURL'] + 'lbs-' + gitprojectname
    pathSrc=self.config['lbs']['GitSrcPath']+"/"+username+"/"

    # first try with git branch master, to see if the branch is decided in the setup.sh. then there must be a config.yml
    self.getPackagingInstructionsInternal(userconfig, username, projectname, gitbranchname, gitprojectname, lbsproject, pathSrc)

    if not os.path.isfile(pathSrc+'lbs-'+projectname+"/config.yml"):
      self.getPackagingInstructionsInternal(userconfig, username, projectname, branchname, gitprojectname, lbsproject, pathSrc)
    return pathSrc

  def getPackagingInstructionsInternal(self, userconfig, username, projectname, branchname, gitprojectname, lbsproject, pathSrc):
    os.makedirs(pathSrc, exist_ok=True)

    needToDownload = True

    #we want a clean clone
    #but do not delete the tree if it is being used by another build
    t = None
    if os.path.isfile(pathSrc+'lbs-'+projectname+'-lastused'):
      t = os.path.getmtime(pathSrc+'lbs-'+projectname+'-lastused')
      # delete the tree only if it has not been used within the last 3 minutes
      if (time.time() - t) < 3*60:
        needToDownload = False
      # update the timestamp
      os.utime(pathSrc+'lbs-'+projectname+'-lastused')
    else:
      open(pathSrc+'lbs-'+projectname+'-lastused', 'a').close()

    headers = {}
    if not 'GitType' in userconfig or userconfig['GitType'] == 'github':
      url=lbsproject + "/archive/" + branchname + ".tar.gz"
    elif userconfig['GitType'] == 'gitlab':
      url=lbsproject + "/repository/archive.tar.gz?ref=" + branchname
      tokenfilename=self.config["lbs"]["SSHContainerPath"] + "/" + username + "/" + projectname + "/gitlab_token"
      if os.path.isfile(tokenfilename):
        with open (tokenfilename, "r") as myfile:
          headers['PRIVATE-TOKEN'] = myfile.read().strip()

    # check if the version we have is still uptodate
    etagFile = pathSrc+'lbs-'+projectname+'-etag'
    if needToDownload and os.path.isfile(etagFile):
      with open(etagFile, 'r') as content_file:
        Etag = content_file.read()
        headers['If-None-Match'] = Etag
      r = requests.get(url, headers=headers)
      if 'Etag' in r.headers and r.headers['Etag'] == '"' + Etag + '"':
         needToDownload = False

    if not needToDownload and os.path.isdir(pathSrc+'lbs-'+projectname):
      # we can reuse the existing source, it was used just recently, or has not changed on the server
      self.StorePackageHashes(pathSrc+'lbs-'+projectname, username, projectname, branchname)
      return

    # delete the working tree
    if os.path.isdir(pathSrc+'lbs-'+projectname):
      shutil.rmtree(pathSrc+'lbs-'+projectname)

    sourceFile = pathSrc + "/" + branchname + ".tar.gz"
    if os.path.isfile(sourceFile):
      os.remove(sourceFile)
    r = requests.get(url, headers=headers)
    if r.status_code == 401:
      raise Exception("problem downloading the repository, access denied")
    elif not r.status_code == 200:
      raise Exception("problem downloading the repository " + url + ", HTTP error code " + str(r.status_code))

    chunk_size = 100000
    with open(sourceFile, 'wb') as fd:
      for chunk in r.iter_content(chunk_size):
        fd.write(chunk)
    if 'Etag' in r.headers:
      Etag = r.headers['Etag']
      with open(etagFile, 'w') as fd:
        fd.write(Etag.strip('"'))

    shell = Shell(Logger())
    if not 'GitType' in userconfig or userconfig['GitType'] == 'github':
      cmd="cd " + pathSrc + ";"
      cmd+="tar xzf " + branchname + ".tar.gz; mv lbs-" + gitprojectname + "-" + branchname + " lbs-" + projectname
      shell.executeshell(cmd)
    elif userconfig['GitType'] == 'gitlab':
      cmd="cd " + pathSrc + ";"
      cmd+="tar xzf " + branchname + ".tar.gz; mv lbs-" + gitprojectname + "-" + branchname + "-* lbs-" + projectname
      shell.executeshell(cmd)

    if os.path.isfile(sourceFile):
      os.remove(sourceFile)
    if not os.path.isdir(pathSrc+'lbs-'+projectname):
      raise Exception("Problem with cloning the git repo")

    self.StorePackageHashes(pathSrc+'lbs-'+projectname, username, projectname, branchname)

  def StorePackageHashes(self, projectPathSrc, username, projectname, branchname):
    shell = Shell(Logger())
    con = Database(self.config)
    for dir in os.listdir(projectPathSrc):
      if os.path.isdir(projectPathSrc + "/" + dir):
        packagename = os.path.basename(dir)
        # update hash of each package
        cmd = "find " + projectPathSrc + "/" + dir + " -type f -print0 | sort -z | xargs -0 sha1sum | sha1sum | awk '{print $1}'"
        hash = shell.evaluateshell(cmd)
        # print(packagename + " " + hash)
        cursor = con.execute("SELECT * FROM package WHERE username = ? AND projectname = ? AND packagename = ? AND branchname = ?", (username, projectname, packagename, branchname))
        row = cursor.fetchone()
        alreadyuptodate = False
        idToUpdate = None
        if row is not None:
          if row['sourcehash'] == hash:
            alreadyuptodate = True
          else:
            idToUpdate = row['id']
        if not alreadyuptodate:
          if idToUpdate is None:
            stmt = "INSERT INTO package(username, projectname, packagename, branchname, sourcehash) VALUES(?,?,?,?,?)"
            cursor = con.execute(stmt, (username, projectname, packagename, branchname, hash))
          else:
            stmt = "UPDATE package SET sourcehash = ? WHERE id = ?"
            cursor = con.execute(stmt, (hash, idToUpdate))
            self.MarkPackageAsDirty(con, idToUpdate)
          con.commit()
    con.close()

  # this changes the status of the package, and requires itself and all depending packages to be rebuilt
  def MarkPackageAsDirty(self, con, packageid):
    # invalidate the package on all distros/release/arch combinations
    stmt = "UPDATE packagebuildstatus SET dirty = 1 WHERE packageid = ?"
    cursor = con.execute(stmt, (packageid,))

    # find all packages depending on it, and invalidate their builds as well
    stmt = "SELECT dependantpackage FROM packagedependancy WHERE requiredpackage = ?"
    cursor = con.execute(stmt, (packageid,))
    data = cursor.fetchall()
    for row in data:
      self.MarkPackageAsDirty(con, row['dependantpackage'])

  def MarkProjectAsDirty(self, username, projectname, branchname, distro, release, arch):
    con = Database(self.config)
    cursor = con.execute("SELECT * FROM package WHERE username = ? AND projectname = ? AND branchname = ?",  (username, projectname, branchname))
    data = cursor.fetchall()
    for row in data:
      packageid = row['id']
      stmt = "UPDATE packagebuildstatus SET dirty = 1 WHERE packageid = ? AND distro = ? AND release = ? AND arch = ?"
      con.execute(stmt, (packageid, distro, release, arch))
    con.commit()
    con.close()

  def MarkPackageAsBuilt(self, username, projectname, packagename, branchname, distro, release, arch):
    con = Database(self.config)
    cursor = con.execute("SELECT * FROM package WHERE username = ? AND projectname = ? AND packagename = ? AND branchname = ?",  (username, projectname, packagename, branchname))
    row = cursor.fetchone()
    if row is not None:
      packageid = row['id']
      stmt = "SELECT id FROM packagebuildstatus WHERE packageid = ? AND distro = ? AND release = ? AND arch = ?"
      cursor = con.execute(stmt, (packageid, distro, release, arch))
      row = cursor.fetchone()
      if row is not None:
        stmt = "UPDATE packagebuildstatus SET dirty = 0 WHERE id = ?"
        cursor = con.execute(stmt, (row['id'],))
      else:
        stmt = "INSERT INTO packagebuildstatus(packageid, distro, release, arch, dirty) VALUES(?,?,?,?,0)"
        cursor = con.execute(stmt, (packageid, distro, release, arch))
      con.commit()
    con.close()

  def GetPackageId(self, con, username, projectname, packagename, branchname):
    stmt = "SELECT id FROM package WHERE username = ? AND projectname = ? AND packagename = ? AND branchname = ?"
    cursor = con.execute(stmt, (username, projectname, packagename, branchname))
    row = cursor.fetchone()
    if row is not None:
      return row['id']
    return None

  def DoesPackageDependOnOtherPackage(self, con, dependantpackageid, requiredpackageid):
    if requiredpackageid is not None and dependantpackageid is not None:
      # find all packages that this package depends on, recursively
      stmt = "SELECT requiredpackage FROM packagedependancy WHERE dependantpackage = ?"
      cursor = con.execute(stmt, (dependantpackageid,))
      data = cursor.fetchall()
      if not data is None:
        for row in data:
          if row['requiredpackage'] == requiredpackageid:
            print("DoesPackageDependOnOtherPackage: " + dependantpackageid + " depends on " + requiredpackageid)
            return True
          if self.DoesPackageDependOnOtherPackage(con, row['requiredpackage'], requiredpackageid):
            return True
    return False

  # Returns True or False
  def NeedToRebuildPackage(self, username, projectname, packagename, branchname, distro, release, arch):
    result = True
    con = Database(self.config)
    cursor = con.execute("SELECT * FROM package WHERE username = ? AND projectname = ? AND packagename = ? AND branchname = ?", (username, projectname, packagename, branchname))
    row = cursor.fetchone()
    if row is not None:
      packageid = row['id']
      stmt = "SELECT dirty FROM packagebuildstatus WHERE packageid = ? AND distro = ? AND release = ? AND arch = ? AND dirty = 0"
      cursor = con.execute(stmt, (packageid, distro, release, arch))
      row = cursor.fetchone()
      if row is not None:
        print(" no need to rebuild " + packagename + " " + str(packageid))
        result = False
    con.close()
    return result

  def CalculatePackageOrder(self, username, projectname, branchname, lxcdistro, lxcrelease, lxcarch):
    userconfig = self.config['lbs']['Users'][username]

    # get the sources of the packaging instructions
    self.getPackagingInstructions(userconfig, username, projectname, branchname)

    buildHelper = BuildHelperFactory.GetBuildHelper(lxcdistro, None, username, projectname, None, branchname)
    return buildHelper.CalculatePackageOrder(lxcdistro, lxcrelease, lxcarch)

  def AddToBuildQueue(self, username, projectname, packagename, branchname, distro, release, arch):
    # find if this project depends on other projects
    DependsOnOtherProjects={}
    proj=self.config['lbs']['Users'][username]['Projects'][projectname]
    if packagename in self.config['lbs']['Users'][username]['Projects'][projectname]:
      pkg=self.config['lbs']['Users'][username]['Projects'][projectname][packagename]
    else:
      pkg=self.config['lbs']['Users'][username]['Projects'][projectname]['Packages'][packagename]
    if 'DependsOn' in proj:
      DependsOnOtherProjects=proj['DependsOn']
    dependsOnString=','.join(DependsOnOtherProjects)
    avoiddocker = False if ("UseDocker" not in proj) else (proj["UseDocker"] == False)
    if not avoiddocker:
      avoiddocker = False if (pkg is None or "UseDocker" not in pkg) else (pkg["UseDocker"] == False)
    avoidlxc = False if ("UseLXC" not in proj) else (proj["UseLXC"] == False)
    if not avoidlxc:
      avoidlxc = False if (pkg is None or "UseLXC" not in pkg) else (pkg["UseLXC"] == False)
    if distro == "fedora" and avoiddocker == False:
      # we have issues with Fedora LXC containers (see https://github.com/tpokorra/lxc-scripts/issues/28)
      avoidlxc = True
    buildmachine = None if ("Machine" not in proj) else proj["Machine"]
    if buildmachine is None:
      buildmachine = None if (pkg is None or "Machine" not in pkg) else pkg["Machine"]

    con = Database(self.config)
    stmt = "INSERT INTO build(status,username,projectname,packagename,branchname,distro,release,arch,avoiddocker,avoidlxc,buildmachine,dependsOnOtherProjects) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)"
    cursor = con.execute(stmt, ('WAITING', username, projectname, packagename, branchname, distro, release, arch, avoiddocker, avoidlxc, buildmachine, dependsOnString))
    con.commit()
    con.close()

  def BuildProject(self, username, projectname, branchname, lxcdistro, lxcrelease, lxcarch, reset = False):
    if reset == True:
      self.MarkProjectAsDirty(username, projectname, branchname, lxcdistro, lxcrelease, lxcarch)

    packages=self.CalculatePackageOrder(username, projectname, branchname, lxcdistro, lxcrelease, lxcarch)

    if packages is None:
      message="Error: circular dependancy!"
    else:
      message=""
      for packagename in packages:

        if not self.NeedToRebuildPackage(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
          continue

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
      return True
    return False

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
    SpecificMachine = item["buildmachine"]

    # 1: check if there is a package building that this package depends on => return False
    if self.CanFindDependanciesBuilding(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch):
      return False
      
    # 2: check if any project that this package depends on is still building or waiting => return False
    for DependantProjectName in DependsOnOtherProjects:
      if self.CanFindMachineBuildingProject(username, DependantProjectName):
        return False

    lbs = Build(self, Logger(item['id']))
    lbsName=self.GetLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
    # get name of available slot
    buildmachine=self.GetAvailableBuildMachine(con,username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch,AvoidDocker,AvoidLXC, SpecificMachine)
    if buildmachine is not None:
      stmt = "UPDATE build SET status='BUILDING', started=?, buildmachine=? WHERE id = ?"
      cursor = con.execute(stmt, (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), buildmachine, item['id']))
      con.commit()
      thread = Thread(target = lbs.buildpackage, args = (username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildmachine, item['id']))
      thread.start()
      return True
    return False

  # needs to be called regularly from outside
  def ProcessBuildQueue(self):
      # loop from left to right
      # check if a project might be ready to build
      con = Database(self.config)
      cursor = con.execute("SELECT * FROM build WHERE status='WAITING' ORDER BY id ASC")
      data = cursor.fetchall()
      for row in data:
        self.attemptToFindBuildMachine(con, row)
        time.sleep(10);
      cursor.close()
      con.close()
      self.CheckForHangingBuild()

  def LiveLog(self, username, projectname, packagename, branchname, distro, release, arch):
      data = self.GetJob(username, projectname, packagename, branchname, distro, release, arch, "")
      if data is None:
        return ("No build is planned for this package at the moment...", -1)
      elif data['status'] == 'BUILDING':
        rowsToShow=40
        con = Database(self.config)
        stmt = "SELECT * FROM log WHERE buildid = ? ORDER BY id DESC LIMIT ?"
        cursor = con.execute(stmt, (data['id'], rowsToShow))
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
      con = Database(self.config)
      stmt = "SELECT * FROM build "
      stmt += "WHERE username = ? AND projectname = ? AND packagename = ? AND branchname = ? AND distro = ? AND release = ? AND arch = ? "
      stmt += "AND hanging = 0 "
      stmt += where
      stmt += " ORDER BY id DESC"
      cursor = con.execute(stmt, (username, projectname, packagename, branchname, distro, release, arch))
      data = cursor.fetchone()
      cursor.close()
      con.close()
      return data

  def GetBuildQueue(self):
      con = Database(self.config)
      cursor = con.execute("SELECT * FROM build WHERE status='WAITING' ORDER BY id ASC")
      data = cursor.fetchall()
      con.close()
      result = deque()
      for row in data:
        result.append(row)
      return result

  def GetFinishedQueue(self):
      con = Database(self.config)
      cursor = con.execute("SELECT *, TIMEDIFF(finished,started) as duration FROM build WHERE status='FINISHED' ORDER BY finished DESC LIMIT ?", (self.config['lbs']['ShowNumberOfFinishedJobs'],))
      data = cursor.fetchall()
      con.close()
      result = deque()
      for row in data:
        result.append(row)
      return result

