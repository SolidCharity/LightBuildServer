#!/usr/bin/env python3
"""BuildHelper for Fedora: knows how to build packages for Fedora"""

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
from BuildHelper import BuildHelper;
from BuildHelperCentos import BuildHelperCentos;
import os
import yaml

class BuildHelperFedora(BuildHelperCentos):
  'build packages for Fedora'

  def __init__(self, container, pathInsideContainer, username, projectname, packagename):
    BuildHelperCentos.__init__(self, container, pathInsideContainer, username, projectname, packagename)
    self.dist='fedora'
    self.fedora = self.release
    self.rhel = 0

  def PrepareMachineBeforeStart(self):
    return True

  def PrepareMachineAfterStart(self):
    if self.container.release == "rawhide":
      self.run("yum install -y fedora-release-rawhide yum-utils")
      self.run("yum-config-manager --disable fedora updates updates-testing")
      self.run("yum-config-manager --enable rawhide")
      self.run("yum update -y yum")
      self.run("yum --releasever=rawhide -y distro-sync --nogpgcheck")
    return True
