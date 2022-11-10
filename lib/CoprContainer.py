#!/usr/bin/env python3
"""Dummy Wrapper for building packages on Copr"""

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

from lib.RemoteContainer import RemoteContainer
from lib.Logger import Logger
from copr.v3 import Client as CoprClient
import time

class CoprContainer(RemoteContainer):
  def __init__(self, containername, configBuildMachine, logger, packageSrcPath):
    RemoteContainer.__init__(self, containername, configBuildMachine, logger, packageSrcPath, "copr")
    self.build = None

  def createmachine(self, distro, release, arch, staticIP):
    return True

  def connectToCopr(self, coprtoken_filename, copr_username, copr_project):
    # establish connection to copr
    self.cl = CoprClient.create_from_file_config(coprtoken_filename)
    projects = self.cl.projects.get_list(name=copr_project, owner=copr_username)
    self.project = projects.projects[0]
    return self.project is not None

  def getLatestReleaseFromCopr(self, packagename):
    if self.project is not None:
      builds = self.project.get_builds(limit=500)
      maxbuildid=-1
      version=None
      for build in builds:
        if build.state == "succeeded" and build.package_name == packagename:
          #self.logger.print("build " + str(build.id) + " state: " + build.state + " v: " + str(build.package_version))
          if build.id > maxbuildid:
            maxbuildid = build.id
            version = build.package_version
      if version is not None:
        version = version[version.find("-")+1:]
      return version

  def buildProject(self, urlsrcrpm):
    # TODO: only build for the current chroot?
    # http://python-copr.readthedocs.io/en/latest/client_v2/resource_info/project.html#access-project-chroots
    chroots = self.project.get_project_chroot_list()
    print("\n".join(map(str, chroots)))
    # see http://python-copr.readthedocs.io/en/latest/client_v2/handlers.html#copr.client_v2.handlers.BuildHandle.create_from_url
    # see http://python-copr.readthedocs.io/en/latest/client_v2/resource_info/build.html#create-new-build
    self.build = self.project.create_build_from_url(srpm_url=urlsrcrpm)
    buildurl = self.cl.root_url + "/coprs/" + self.project.owner + "/" + self.project.name + "/build/" + str(self.build.number)
    # somehow the html characters are encoded 
    #self.logger.print("see the the details of the build with logs at <a href='" + buildurl + "'>" + buildurl + "</a>...")
    self.logger.print("see the details of the build with logs at " + buildurl)
    while self.build.state != "succeeded" and self.build.state != "failed" and self.build.state != "cancelled":
      time.sleep(15)
      self.build = self.build.get_self()
      self.logger.print("current state of the build: " + self.build.state)

    if self.build.state == "succeeded":
      # wait a minute for the repository to be recalculated for following builds
      time.sleep(60)
      return True
    return False

  def stop(self):
    # cancel the currently running build
    if self.build is not None:
      self.build.cancel()
    return True
