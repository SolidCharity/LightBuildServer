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
import os
import shutil
import time
import datetime
import requests
import logging
from threading import Thread, Lock
from collections import deque

from django.conf import settings
from django.db.models import Q

from lib.RemoteContainer import RemoteContainer
from lib.DockerContainer import DockerContainer
from lib.LXCContainer import LXCContainer
from lib.LXDContainer import LXDContainer
from lib.CoprContainer import CoprContainer
from lib.BuildHelper import BuildHelper
from lib.BuildHelperFactory import BuildHelperFactory
from lib.Logger import Logger
from lib.Build import Build
from lib.Shell import Shell

from projects.models import Project, Package, PackageDependancy
from machines.models import Machine
from builder.models import Build, Log

class LightBuildServer:
  'light build server based on lxc and git'

  def __init__(self):
    # keep WAITING build jobs
    Build.objects.filter(status='BUILDING').delete()
    Log.objects.all().delete()

  def GetLbsName(self, build):
    return build.username+"/"+build.projectname+"/"+build.packagename+"/"+build.branchname+"/"+build.distro+"/"+build.release+"/"+build.arch


  def GetAvailableBuildMachine(self, build):
    machineToUse=None
    machinePriorityToUse=101

    m = Machine.objects.filter(status='AVAILABLE')
    if build.avoiddocker:
      m = m.exclude(type='docker')
    if build.avoidlxc:
      m = m.exclude(type='lxc').exclude(type='lxd')
    if not build.buildmachine:
      m = m.filter(static=False)
    else:
      m = m.filter(Q(name=build.buildmachine) | Q(Q(type='copr') & Q(name__startswith=build.buildmachine) & Q(static=True)))

    for row in m:
      buildmachine=row.name
      buildmachinePriority=row.priority
      if buildmachinePriority < machinePriorityToUse:
        machinePriorityToUse = buildmachinePriority
        machineToUse = buildmachine
    if machineToUse is not None:
      m = Machine.objects.filter(name=machineToUse).filter(status='AVAILABLE').first()
      if m:
        m.status = 'BUILDING'
        m.build = build
        m.save()
        print("GetAvailableBuildMachine found a free machine: " + machineToUse)
        return machineToUse
    return None

  def CheckForHangingBuild(self):
      # check for hanging build (BuildingTimeout in config.yml)
      builds = Build.objects.filter(status='BUILDING'). \
        filter(hanging=False). \
        filter(Q(started__lt=datetime.datetime.now()-datetime.timedelta(seconds=settings.BUILDING_TIMEOUT))). \
        order_by(id).reverse()
      for row in builds:
        log = Log.objects.filter(build_id=row.id).filter(Q(created__gt=datetime.datetime.now()-datetime.timedelta(seconds=settings.BUILDING_TIMEOUT)))
        if not log.exists():
          # mark the build as hanging, so that we don't try to release the machine several times
          row.hanging = 1
          row.save()
          self.ReleaseMachine(row.buildmachine, True)
          # when the build job realizes that the buildmachine is gone:
          #   the log will be written, email sent, and logs cleared
          #   the build will be marked as failed as well
          return

  def CancelPlannedBuild(self, username, projectname, packagename, branchname, distro, release, arch):
      builds = Build.objects.filter(status='WAITING').filter(username=username). \
            filter(projectname=projectname).filter(packagename=packagename). \
            filter(branchname=branchname).filter(distro=distro).filter(release=release).filter(arch=arch). \
            order_by(id)
      for row in builds:
        row.status = 'CANCELLED'
        row.save()
        # only remove one build job from the queue
        break

  def CancelWaitingJobsInQueue(self, queue):
      # TODO: add arch to the queue as well?
      # queue=username+"/"+projectname+"/"+branchname+"/"+distro+"/"+release
      q = queue.split('/')
      builds = Build.objects.filter(status='WAITING').filter(username=q[0]). \
            filter(projectname=q[1]).filter(packagename=q[2]). \
            filter(branchname=q[3]).filter(distro=q[4]).filter(release=q[5])
      for row in builds:
        row.status = 'CANCELLED'
        row.save()

  def ReleaseMachine(self, buildmachine, jobFailed):
    print("ReleaseMachine %s" % (buildmachine))
    machine = Machine.filter(name=buildmachine).first()

    # only release the machine when it is building. if it is already being stopped, do nothing
    if machine.status == 'BUILDING':
      if jobFailed:
        self.CancelWaitingJobsInQueue(machine.queue)

      machine.status = 'STOPPING'
      machine.save()

      if machine.type == 'lxc':
        LXCContainer(buildmachine, machine, Logger(), '').stop()
      elif machine.type == 'lxd':
        LXDContainer(buildmachine, machine, Logger(), '').stop()
      elif machine.type == 'docker':
        DockerContainer(buildmachine, machine, Logger(), '').stop()
      elif machine.type == 'copr':
        CoprContainer(buildmachine, machine, Logger(), '').stop()

      machine.status = 'AVAILABLE'
      machine.save()

  def CanFindDependanciesBuilding(self, build):
    queue=build.username+"/"+build.projectname+"/"+build.branchname+"/"+build.distro+"/"+build.release
    machines = Machine.objects.filter(status='BUILDING').filter(queue=queue)
    for row in machines:
      # there is a machine building a package on the same queue (same user, project, branch, distro, release, arch)
      # does this package actually depend on that other package?
      dependantpackage = self.GetPackage(build.username, build.projectname, build.packagename, build.branchname)
      requiredpackage = self.GetPackage(build.username, build.projectname, row.packagename, build.branchname)
      result = self.DoesPackageDependOnOtherPackage(dependantpackage, requiredpackage)
      if result:
        print("cannot build " + build.packagename + " because it depends on another package")
        return True
    return False

  def CanFindMachineBuildingProject(self, username, projectname):
    machine = Machine.objects.filter(status='BUILDING').filter(username=username).filter(projectname=projectname)

    if machine.exists():
          # there is a machine building a package of the specified project
          return True
    return False

  # this is called from Build.py buildpackage, and from LightBuildServer.py CalculatePackageOrder
  def getPackagingInstructions(self, username, projectname, branchname):
    gitprojectname = projectname
    gitbranchname = "master"
    project = Project.objects.filter(name=projectname).filter(username=username)
    if 'GitProjectName' in userconfig['Projects'][projectname]:
      gitprojectname = userconfig['Projects'][projectname]['GitProjectName']
    if 'GitBranchName' in userconfig['Projects'][projectname]:
      gitbranchname = userconfig['Projects'][projectname]['GitBranchName']
    lbsproject=userconfig['GitURL'] + 'lbs-' + gitprojectname
    pathSrc=self.config['lbs']['GitSrcPath']+"/"+username+"/"

    # first try with git branch master, to see if the branch is decided in the setup.sh. then there must be a config.yml
    self.getPackagingInstructionsInternal(username, projectname, gitbranchname, gitprojectname, lbsproject, pathSrc)

    if not os.path.isfile(pathSrc+'lbs-'+projectname+"/config.yml"):
      self.getPackagingInstructionsInternal(username, projectname, branchname, gitprojectname, lbsproject, pathSrc)
    return pathSrc

  def getPackagingInstructionsInternal(self, username, projectname, branchname, gitprojectname, lbsproject, pathSrc):
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

  # this changes the status of the package, and requires itself and all depending packages to be rebuilt
  def MarkPackageAsDirty(self, packageid):
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

  def GetPackage(self, username, projectname, packagename, branchname):
    package = Package.objects.filter(username=username).filter(projectname=projectname).filter(packagename=packagename).filter(branchname=branchname).first()
    return package

  def DoesPackageDependOnOtherPackage(self, dependantpackage, requiredpackage):
    if requiredpackage is not None and dependantpackage is not None:
      # find all packages that this package depends on, recursively
      dep = PackageDependancy.objects.filter(dependantpackage=dependantpackage)
      if not dep is None:
        for row in dep:
          if row.requiredpackage == requiredpackage:
            print("DoesPackageDependOnOtherPackage: " + dependantpackage.id + " depends on " + requiredpackage.id)
            return True
          if self.DoesPackageDependOnOtherPackage(row.requiredpackage, requiredpackage):
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

  def CalculatePackageOrder(self, project, branchname, lxcdistro, lxcrelease, lxcarch):
    # get the sources of the packaging instructions
    self.getPackagingInstructions(project, branchname)

    buildHelper = BuildHelperFactory.GetBuildHelper(lxcdistro, None, project, None, branchname)
    return buildHelper.CalculatePackageOrder(lxcdistro, lxcrelease, lxcarch)

  def AddToBuildQueue(self, project, packagename, branchname, distro, release, arch):
    # find if this project depends on other projects
    DependsOnOtherProjects={}
    print(project)
    pkgs = Package.objects.filter(project = project).all()
    for pkg in pkgs:
        print(pkg.name)
    print(packagename)
    pkg = Package.objects.filter(project = project).filter(name=packagename).first()
    avoiddocker = project.use_docker == False
    avoidlxc = project.use_lxc == False
    buildmachine = pkg.machine
    if buildmachine is None:
      buildmachine = project.machine

    build = Build(status='WAITING', user=project.user, project=project.name, secret=not project.visible, \
        package=packagename, branchname=branchname, distro=distro, release=release, arch=arch, \
        avoiddocker=avoiddocker, avoidlxc=avoidlxc, designated_build_machine=buildmachine)
    build.save()

  def BuildProject(self, project, branchname, distro, release, arch, reset = False):
    if reset == True:
      self.MarkProjectAsDirty(project, branchname, distro, release, arch)

    packages=self.CalculatePackageOrder(project, branchname, distro, release, arch)

    if packages is None:
      message="Error: circular dependancy!"
    else:
      message=""
      for packagename in packages:

        if not self.NeedToRebuildPackage(project, packagename, branchname, distro, release, arch):
          continue

        # add package to build queue
        message += packagename + ", "
        job = self.GetJob(project, packagename, branchname, distro, release, arch, True)
        if job is None:
          self.AddToBuildQueue(project, packagename, branchname, distro, release, arch)

    return message

  def BuildProjectWithBranch(self, project, packagename, branchname, distro, release, arch):
    job = self.GetJob(project, packagename, branchname, distro, release, arch, True)
    if job is None:
      self.AddToBuildQueue(project, packagename, branchname, distro, release, arch)
      return True
    return False

  def attemptToFindBuildMachine(self, build):

    # 1: check if there is a package building that this package depends on => return False
    if self.CanFindDependanciesBuilding(build):
      return False
      
    # 2: check if any project that this package depends on is still building or waiting => return False
    for DependantProjectName in build.dependsOnOtherProjects:
      if self.CanFindMachineBuildingProject(build.username, DependantProjectName):
        return False

    lbs = Build(self, Logger(build.id))
    lbsName=self.GetLbsName(build)
    # get name of available slot
    buildmachine=self.GetAvailableBuildMachine(build)
    if buildmachine is not None:
      build.status = 'BUILDING'
      build.started = datetime.datetime.now()
      build.buildmachine = buildmachine
      build.save()
      thread = Thread(target = lbs.buildpackage, args = (build,))
      thread.start()
      return True
    return False

  # needs to be called regularly from outside
  def ProcessBuildQueue(self):
      # loop from left to right
      # check if a project might be ready to build
      builds = Build.objects.filter(status='WAITING')
      for build in builds:
        self.attemptToFindBuildMachine(build)
        time.sleep(10)
      self.CheckForHangingBuild()

  def LiveLog(self, username, projectname, packagename, branchname, distro, release, arch):
      data = self.GetJob(username, projectname, packagename, branchname, distro, release, arch, False)
      if data is None:
        return ("No build is planned for this package at the moment...", -1)
      elif data.status == 'BUILDING':
        rowsToShow=40
        logs = Log.objects.filter(buildid=data.id).reverse()[:rowsToShow]
        output = ""
        for row in data:
          output = row.line + output
        timeout = 2
      elif data.status == 'CANCELLED':
        return ("This build has been removed from the build queue...", -1)
      elif data.status == 'WAITING':
        return ("We are waiting for a build machine to become available...", 10)
      elif data.status == 'FINISHED':
        output = Logger().getLog(username, projectname, packagename, branchname, distro, release, arch, data.buildnumber)
        # stop refreshing
        timeout=-1

      return (output, timeout)

  def GetJob(self, project, packagename, branchname, distro, release, arch, only_waiting_or_building):
      build = Build.objects.filter(project=project). \
        filter(package=packagename).filter(branchname=branchname).filter(distro=distro). \
        filter(release=release).filter(arch=arch).filter(hanging=False)
      if only_waiting_or_building:
        build = build.filter(Q(Q(status='WAITING') | Q(status='BUILDING')))
      return build.first()

  def GetBuildQueue(self, auth_username):
      builds = Build.objects.filter(status='WAITING')
      if auth_username is None:
        builds = builds.filter(secret=False)
      else:
        builds = builds.filter(Q(Q(username=auth_username) | Q(secret=False)))
      return builds

  def GetFinishedQueue(self, auth_username):
      builds = Build.objects.filter(status='FINISHED')
      if auth_username is None:
        builds = builds.filter(secret=False)
      else:
        builds = builds.filter(Q(Q(username=auth_username) | Q(secret=False)))
      builds = builds.order_by('finished').reverse()[:settings.SHOW_NUMBER_OF_FINISHED_JOBS]
      return builds
