#!/usr/bin/env python3
"""BuildHelperFactory: gets the correct build helper for the right package format"""

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

from lib.BuildHelperDebian import BuildHelperDebian
from lib.BuildHelperUbuntu import BuildHelperUbuntu
from lib.BuildHelperCentos import BuildHelperCentos
from lib.BuildHelperFedora import BuildHelperFedora

class BuildHelperFactory:
  'factory class for specific BuildHelper implementations for the various Linux Distributions'

  def GetBuildHelper(distro, container, build):
    if distro == "debian":
      return BuildHelperDebian(container, build)
    if distro == "ubuntu":
      return BuildHelperUbuntu(container, build)
    if distro == "centos":
      return BuildHelperCentos(container, build)
    if distro == "fedora":
      return BuildHelperFedora(container, build)
