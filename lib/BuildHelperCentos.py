#!/usr/bin/env python3
"""BuildHelper for CentOS: knows how to build packages for CentOS"""

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

class BuildHelperCentos(BuildHelper):
  'build packages for CentOS'

  def PrepareForBuilding(self):
    if not self.run("yum -y update"):
      return self.output
    if not self.run("yum -y install wget"):
      return self.output

  def InstallRequiredPackages(self):
    print("Centos: InstallRequiredPackages not implemented yet") 

  def BuildPackage(self):
    print("Centos: BuildPackages not implemented yet") 

  def InstallTestEnvironment(self):
    if not self.run("cd lbs-" + self.projectname + "-master/" + self.packagename + " && ./setup.sh"):
      return self.output

  def RunTests(self):
    if not self.run("cd lbs-" + self.projectname + "-master/" + self.packagename + " && ./runtests.sh"):
      return self.output
