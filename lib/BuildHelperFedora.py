#!/usr/bin/env python3
"""BuildHelper for Fedora: knows how to build packages for Fedora"""

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
from BuildHelper import BuildHelper;
from BuildHelperCentos import BuildHelperCentos;
import os
import yaml

class BuildHelperFedora(BuildHelperCentos):
  'build packages for Fedora'

  def __init__(self, container, username, projectname, packagename, branchname):
    BuildHelperCentos.__init__(self, container, username, projectname, packagename, branchname)
    self.dist='fedora'
    self.rhel = 0
    self.rawhide = 33
    # this is the latest release. rawhide might be already 25, 23 latest release, 24 in testing
    self.latestrelease = 32
    if self.release == "rawhide":
     self.release = self.rawhide
    self.release = str(self.release)
    self.fedora = int(self.release)
    self.releaseForRepoFile = "$releasever"
    # use dnf instead of rpm, starting with Fedora 22
    self.yumOrDnf = "dnf"

  def PrepareMachineBeforeStart(self):
    return True

  def PrepareMachineAfterStart(self):
    if self.fedora == self.rawhide:
      self.run("dnf install -y fedora-repos-rawhide dnf-plugins-core")
      self.run("dnf config-manager --set-disabled fedora updates updates-testing")
      self.run("dnf config-manager --set-enabled rawhide")
      self.run("dnf clean -q dbcache metadata")
      self.run("dnf  --releasever=rawhide --setopt=deltarpm=false distro-sync -y --nogpgcheck")
    elif self.fedora > self.latestrelease:
      # before the final release: make sure we receive the latest packages
      self.run("dnf install -y dnf-plugins-core")
      self.run("dnf config-manager --set-enabled updates-testing")
    else:
      # disable updates-testing for the stable release
      self.run("dnf install -y dnf-plugins-core")
      self.run("dnf config-manager --set-disabled updates-testing")
    return True
