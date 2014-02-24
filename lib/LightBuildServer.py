#!/usr/bin/env python3

import sys
from subprocess import Popen, PIPE
import lxc

class LightBuildServer:
  'light build server based on lxc and git'

  def __init__(self):
    self.output = ""
    self.container = None

  def createbuildmachine(self, lxcdistro, lxcrelease, lxcarch, buildmachine):
    self.container = lxc.Container(buildmachine)
    output = ''
    # create lxc container with specified OS
    #if container.create(lxcdistro, 0, {"release": lxcrelease, "arch": lxcarch}):
    child = Popen(["lxc-create", "-t", "download", "--name", buildmachine,
	"--", "-d", lxcdistro, "-r", lxcrelease, "-a", lxcarch], stdout=PIPE, stderr=PIPE)
    while True:
      out = child.stdout.read(1).decode("utf-8")
      if (out == '') and child.poll() != None:
        break
      if (out != ''):
        sys.stdout.write(out)
        output += out
        sys.stdout.flush()
    streamdata = child.communicate();
    output += streamdata[1].decode("utf-8");
    self.output += output
    return (not child.returncode)
  
  def buildpackage(self, projectname, packagename, lxcdistro, lxcrelease, lxcarch, buildmachine):
    self.output = ""
    # TODO pick up github url from database
    lbsproject='https://github.com/tpokorra/lbs-' + projectname + '/' + packagename
    if self.createbuildmachine(lxcdistro, lxcrelease, lxcarch, buildmachine):
      # TODO for each build slot, create a cache mount, depending on the OS. /var/cache contains yum and apt caches
      #         /var/lib/lbs/cache
      # TODO for each project, create a repo mount, depending on the OS
      #         /var/lib/lbs/repos
      self.container.start()
      # TODO prepare container, install packages that the build requires
      # TODO get the sources
      # TODO do the actual build
      # TODO on failure, show errors
      # TODO on success, create repo for download, and display success
      # TODO destroy the container
      self.container.stop();
      self.container.destroy();
      self.output += "\nSuccess!"
    else:
      self.output += "\nThere is a problem with creating the container!"
    return self.output
