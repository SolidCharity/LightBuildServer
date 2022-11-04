#!/usr/bin/env python3
"""BuildHelper for Ubuntu: knows how to build packages for Ubuntu"""

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
from lib.BuildHelper import BuildHelper;
from lib.BuildHelperDebian import BuildHelperDebian;
import os
import yaml

class BuildHelperUbuntu(BuildHelperDebian):
  'build packages for Ubuntu'

  def __init__(self, container, username, projectname, packagename, branchname):
    BuildHelperDebian.__init__(self, container, username, projectname, packagename, branchname)
    self.dist='ubuntu'
