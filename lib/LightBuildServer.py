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
from django.utils import timezone

from lib.RemoteContainer import RemoteContainer
from lib.DockerContainer import DockerContainer
from lib.LXCContainer import LXCContainer
from lib.LXDContainer import LXDContainer
from lib.CoprContainer import CoprContainer
from lib.BuildHelper import BuildHelper
from lib.BuildHelperFactory import BuildHelperFactory
from lib.Logger import Logger
from lib.Builder import Builder
from lib.Shell import Shell

from projects.models import Project, Package, PackageDependancy, PackageSrcHash, PackageBuildStatus
from machines.models import Machine
from builder.models import Build, Log

class LightBuildServer:
  'light build server based on lxc and git'

  def __init__(self):
    machines = Machine.objects.all()
    for m in machines:
        m.build = None
        m.status = "AVAILABLE"
        m.save()
    # keep WAITING build jobs
    Build.objects.filter(status='BUILDING').delete()
    Log.objects.all().delete()

  def GetLbsName(self, build):
    return build.user.username+"/"+build.project+"/"+build.package+"/"+build.branchname+"/"+build.distro+"/"+build.release+"/"+build.arch


  def GetAvailableBuildMachine(self, build):
    machineToUse=None
    machinePriorityToUse=101

    m = Machine.objects.filter(status='AVAILABLE')
    if build.avoiddocker:
      m = m.exclude(type='docker')
    if build.avoidlxc:
      m = m.exclude(type='lxc').exclude(type='lxd')
    if not build.designated_build_machine:
      m = m.filter(static=False)
    else:
      m = m.filter(Q(host=build.designated_build_machine) | Q(Q(type='copr') & Q(host__startswith=build.designated_build_machine) & Q(static=True)))

    for row in m:
      buildmachine=row.host
      buildmachinePriority=row.priority
      if buildmachinePriority < machinePriorityToUse:
        machinePriorityToUse = buildmachinePriority
        machineToUse = buildmachine
    if machineToUse is not None:
      m = Machine.objects.filter(host=machineToUse).filter(status='AVAILABLE').first()
      if m:
        m.status = 'BUILDING'
        m.build = build
        m.save()
        print("GetAvailableBuildMachine found a free machine: " + machineToUse)
        return machineToUse

    print("GetAvailableBuildMachine cannot find a machine")
    return None

  def CheckForHangingBuild(self):

      # check for hanging build (BuildingTimeout in config.yml)
      builds = Build.objects.filter(status='BUILDING'). \
        filter(hanging=False). \
        filter(Q(started__lt=timezone.now()-datetime.timedelta(seconds=settings.BUILDING_TIMEOUT))). \
        order_by('id').reverse()
      for row in builds:
        log = Log.objects.filter(build=row).filter(Q(created__gt=datetime.datetime.now()-datetime.timedelta(seconds=settings.BUILDING_TIMEOUT)))
        if not log.exists():
          # mark the build as hanging, so that we don't try to release the machine several times
          row.hanging = 1
          row.save()
          self.ReleaseMachine(row.buildmachine, True)
          # when the build job realizes that the buildmachine is gone:
          #   the log will be written, email sent, and logs cleared
          #   the build will be marked as failed as well
          return

  def CancelPlannedBuild(self, project, packagename, branchname, distro, release, arch):
      build = Build.objects.filter(status='WAITING'). \
            filter(user=project.user). \
            filter(project=project.name).filter(package=packagename). \
            filter(branchname=branchname).filter(distro=distro).filter(release=release).filter(arch=arch). \
            first()
      if build:
        build.status = 'CANCELLED'
        build.save()
      else:
        raise Exception(f"cannot find build {project} {packagename} {branchname} {distro} {release} {arch}")

  def CancelWaitingJobsInQueue(self, build):
      builds = Build.objects.filter(status='WAITING').filter(user=build.user). \
            filter(project=build.project).filter(package=build.package). \
            filter(branchname=build.branchname). \
            filter(distro=build.distro).filter(release=build.release).filter(arch=build.arch)
      for row in builds:
        row.status = 'CANCELLED'
        row.save()

  def ReleaseMachine(self, buildmachine, jobFailed):
    print("ReleaseMachine %s" % (buildmachine))
    machine = Machine.objects.filter(host=buildmachine).first()

    # only release the machine when it is building. if it is already being stopped, do nothing
    if machine.status == 'BUILDING':
      if jobFailed:
        self.CancelWaitingJobsInQueue(machine.build)

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
    machines = Machine.objects.filter(status='BUILDING'). \
        filter(build__user__username=build.user.username). \
        filter(build__project=build.project). \
        filter(build__branchname=build.branchname). \
        filter(build__distro=build.distro). \
        filter(build__release=build.release). \
        filter(build__arch=build.arch)
    for row in machines:
      # there is a machine building a package on the same queue (same user, project, branch, distro, release, arch)
      # does this package actually depend on that other package?
      dependantpackage = self.GetPackage(build.user.username, build.projectname, build.packagename, build.branchname)
      requiredpackage = self.GetPackage(build.user.username, build.projectname, row.packagename, build.branchname)
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
  def getPackagingInstructions(self, build):
    project = Project.objects.filter(name=build.project).filter(user=build.user).first()
    lbsproject = project.git_url + '/lbs-' + project.name
    pathSrc = settings.GIT_SRC_PATH+"/"+build.user.username+"/"

    # first try with git branch master, to see if the branch is decided in the setup.sh. then there must be a config.yml
    self.getPackagingInstructionsInternal(project, build, project.git_branch, lbsproject, pathSrc)

    if not os.path.isfile(pathSrc+'lbs-'+build.project+"/config.yml"):
      self.getPackagingInstructionsInternal(project, build, build.branchname, lbsproject, pathSrc)
    return pathSrc

  def getPackagingInstructionsInternal(self, project, build, branchname, lbsproject, pathSrc):
    os.makedirs(pathSrc, exist_ok=True)

    needToDownload = True

    #we want a clean clone
    #but do not delete the tree if it is being used by another build
    t = None
    if os.path.isfile(pathSrc+'lbs-'+build.project+'-lastused'):
      t = os.path.getmtime(pathSrc+'lbs-'+build.project+'-lastused')
      # delete the tree only if it has not been used within the last 3 minutes
      if (time.time() - t) < 3*60:
        needToDownload = False
      # update the timestamp
      os.utime(pathSrc+'lbs-'+build.project+'-lastused')
    else:
      open(pathSrc+'lbs-'+build.project+'-lastused', 'a').close()

    headers = {}
    url = None
    if project.git_type == 'github':
      url = lbsproject + "/archive/" + branchname + ".tar.gz"
    elif project.git_type == 'gitlab':
      url = lbsproject + "/repository/archive.tar.gz?ref=" + branchname
      if project.git_private_token:
        headers['PRIVATE-TOKEN'] = project.git_private_token

    # check if the version we have is still uptodate
    etagFile = pathSrc+'lbs-'+build.project+'-etag'
    if needToDownload and os.path.isfile(etagFile):
      with open(etagFile, 'r') as content_file:
        Etag = content_file.read()
        headers['If-None-Match'] = Etag
      r = requests.get(url, headers=headers)
      if 'Etag' in r.headers and r.headers['Etag'] == '"' + Etag + '"':
         needToDownload = False

    if not needToDownload and os.path.isdir(pathSrc+'lbs-'+build.project):
      # we can reuse the existing source, it was used just recently, or has not changed on the server
      self.StorePackageHashes(pathSrc+'lbs-'+build.project, project, branchname)
      return

    # delete the working tree
    if os.path.isdir(pathSrc+'lbs-'+build.project):
      shutil.rmtree(pathSrc+'lbs-'+build.project)

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
    if project.git_type == 'github':
      cmd="cd " + pathSrc + ";"
      cmd+="tar xzf " + branchname + ".tar.gz; mv lbs-" + build.project + "-" + branchname + " lbs-" + build.project
      shell.executeshell(cmd)
    elif project.git_type == 'gitlab':
      cmd="cd " + pathSrc + ";"
      cmd+="tar xzf " + branchname + ".tar.gz; mv lbs-" + build.project + "-" + branchname + "-* lbs-" + build.project
      shell.executeshell(cmd)

    if os.path.isfile(sourceFile):
      os.remove(sourceFile)
    if not os.path.isdir(pathSrc+'lbs-'+build.project):
      raise Exception("Problem with cloning the git repo")

    self.StorePackageHashes(pathSrc+'lbs-'+build.project, project, branchname)

  def StorePackageHashes(self, projectPathSrc, project, branchname):
    shell = Shell(Logger())
    for dir in os.listdir(projectPathSrc):
      if os.path.isdir(projectPathSrc + "/" + dir):
        packagename = os.path.basename(dir)
        # update hash of each package
        cmd = "find " + projectPathSrc + "/" + dir + " -type f -print0 | sort -z | xargs -0 sha1sum | sha1sum | awk '{print $1}'"
        sourcehash = shell.evaluateshell(cmd)
        # print(packagename + " " + hash)
        package = Package.objects.filter(project = project).filter(name=packagename).first()
        if package:
          hash, created = PackageSrcHash.objects.get_or_create(package=package,branchname=branchname)
          if not hash.sourcehash == sourcehash:
            hash.sourcehash = sourcehash
            hash.save()
            if not created:
                self.MarkPackageAsDirty(package, branchname)

  # this changes the status of the package, and requires itself and all depending packages to be rebuilt
  def MarkPackageAsDirty(self, package, branchname):
    # invalidate the package on all distros/release/arch combinations
    packagebuildstatus = PackageBuildStatus.objects.filter(package=package).filter(branchname=branchname)
    for p in packagebuildstatus:
        p.dirty = True
        p.save()

    # find all packages depending on it, and invalidate their builds as well
    packagedependancy = PackageDependancy.objects.filter(requiredpackage=package)
    for p in packagedependancy:
      otherpackagebuildstatus = PackageBuildStatus.objects.filter(package = p.dependantpackage). \
        filter(branchname=packagebuildstatus.branchname).first()
      if otherpackagebuildstatus:
        self.MarkPackageAsDirty(otherpackagebuildstatus, branchname)

  def MarkProjectAsDirty(self, username, projectname, branchname, distro, release, arch):
    project = Project.objects.filter(user__username=username).filter(name=projectname).first()
    packagebuildstatus = PackageBuildStatus.objects.filter(package=project.package). \
        filter(branchname=branchname). \
        filter(distro=distro).filter(release=release).filter(arch=arch)
    for p in packagebuildstatus:
      packagebuildstatus.dirty = True
      packagebuildstatus.save()

  def MarkPackageAsBuilt(self, build):
    project = Project.objects.filter(user__username=build.user.username).filter(name=build.project).first()
    package = Package.objects.filter(project=project).filter(name=build.package).first()
    packagebuildstatus = PackageBuildStatus.objects.filter(package=package). \
        filter(branchname=build.branchname). \
        filter(distro=build.distro).filter(release=build.release).filter(arch=build.arch).first()
    if packagebuildstatus:
        packagebuildstatus.dirty = False;
        packagebuildstatus.save()
    else:
        packagebuildstatus = PackageBuildStatus(package=package, branchname=build.branchname,
            distro=build.distro, release=build.release, arch=build.arch, dirty=False)
        packagebuildstatus.save()

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
            print(f"DoesPackageDependOnOtherPackage: {dependantpackage.id} depends on {requiredpackage.id}")
            return True
          if self.DoesPackageDependOnOtherPackage(row.requiredpackage, requiredpackage):
            return True
    return False

  # Returns True or False
  def NeedToRebuildPackage(self, username, projectname, packagename, branchname, distro, release, arch):
    result = True
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
    return result

  def CalculatePackageOrder(self, project, branchname, distro, release, arch):
    # get the sources of the packaging instructions
    self.getPackagingInstructions(project, branchname)

    build = Build(project=project, package=None, branchname=branchname, distro=distro, release=release, arch=arch)
    buildHelper = BuildHelperFactory.GetBuildHelper(distro, None, build)
    return buildHelper.CalculatePackageOrder(distro, release, arch)

  def AddToBuildQueue(self, project, packagename, branchname, distro, release, arch):
    # find if this project depends on other projects
    DependsOnOtherProjects={}
    pkgs = Package.objects.filter(project = project).all()
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
    if build.dependsOnOtherProjects:
      for DependantProjectName in build.dependsOnOtherProjects:
        if self.CanFindMachineBuildingProject(build.username, DependantProjectName):
          return False

    lbs = Builder(self, Logger(build))
    lbsName=self.GetLbsName(build)
    # get name of available slot
    buildmachine=self.GetAvailableBuildMachine(build)
    if buildmachine:
      build.status = 'BUILDING'
      build.started = timezone.now()
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
      first = True
      for build in builds:
        if not first:
            time.sleep(10)
        first = False
        self.attemptToFindBuildMachine(build)

      self.CheckForHangingBuild()

  def LiveLog(self, username, project, packagename, branchname, distro, release, arch):
      build = self.GetJob(project, packagename, branchname, distro, release, arch, False)
      if build is None:
        return ("No build is planned for this package at the moment...", -1)
      elif build.status == 'BUILDING':
        rowsToShow=40
        logs = Log.objects.filter(buildid=build.id).reverse()[:rowsToShow]
        output = ""
        for row in logs:
          output = row.line + output
        timeout = 2
      elif build.status == 'CANCELLED':
        return ("This build has been removed from the build queue...", -1)
      elif build.status == 'WAITING':
        return ("We are waiting for a build machine to become available...", 10)
      elif build.status == 'FINISHED':
        output = Logger().getLog(build)
        # stop refreshing
        timeout=-1

      return (output, timeout)

  def GetJob(self, project, packagename, branchname, distro, release, arch, only_waiting_or_building):
      build = Build.objects.filter(user=project.user).filter(project=project.name). \
        filter(package=packagename).filter(branchname=branchname).filter(distro=distro). \
        filter(release=release).filter(arch=arch).filter(hanging=False)
      if only_waiting_or_building:
        build = build.filter(Q(Q(status='WAITING') | Q(status='BUILDING')))
      return build.first()

  def GetBuildQueue(self, auth_user):
      builds = Build.objects.filter(status='WAITING')
      if auth_user is None:
        builds = builds.filter(secret=False)
      else:
        builds = builds.filter(Q(Q(user=auth_user) | Q(secret=False)))
      return builds

  def GetFinishedQueue(self, auth_user):
      builds = Build.objects.filter(status='FINISHED')
      if auth_user is None:
        builds = builds.filter(secret=False)
      else:
        builds = builds.filter(Q(Q(user=auth_user) | Q(secret=False)))
      builds = builds.order_by('finished').reverse()[:settings.SHOW_NUMBER_OF_FINISHED_JOBS]
      return builds
