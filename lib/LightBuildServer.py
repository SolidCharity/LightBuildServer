#!/usr/bin/env python3
"""Light Build Server: build packages for various distributions, using linux containers"""

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

from LXCContainer import LXCContainer

class LightBuildServer:
  'light build server based on lxc and git'

  def __init__(self):
    self.output = ""
    self.container = None

  def createbuildmachine(self, lxcdistro, lxcrelease, lxcarch, buildmachine):
    self.container = LXCContainer(buildmachine)
    result = self.container.createmachine(lxcdistro, lxcrelease, lxcarch)
    self.output += self.container.output
    return result
  
  def buildpackage(self, projectname, packagename, lxcdistro, lxcrelease, lxcarch, buildmachine):
    self.output = ""
    # TODO pick up github url from database
    lbsproject='https://github.com/tpokorra/lbs-' + projectname + '/' + packagename
    if self.createbuildmachine(lxcdistro, lxcrelease, lxcarch, buildmachine):

      # install a mount for the project repo
      self.container.installmount("/root/repo", "/var/www/repos/" + projectname + "/" + lxcdistro + "/" + lxcrelease + "/" + lxcarch)

      if self.container.startmachine():
        print("container has been started successfully")
      
      # TODO prepare container, install packages that the build requires
      result = self.container.execute("pwd");
      self.output += self.container.output
      if not result:
        return self.output
      result = self.container.execute("apt-get update");
      result = self.container.execute("apt-get upgrade");
      result = self.container.execute("apt-get -y install git-core");
      self.output += self.container.output
      if not result:
        return self.output
      # TODO get the sources
      # TODO do the actual build
      # TODO on failure, show errors
      # TODO on success, create repo for download, and display success
      # TODO destroy the container
      self.container.stop();
      self.container.destroy();
      self.output += "\nSuccess!"
    else:
      self.output += self.container.output
      self.output += "\nThere is a problem with creating the container!"
    return self.output
