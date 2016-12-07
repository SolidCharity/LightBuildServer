#!/usr/bin/env python3
"""Run commands on the shell and log the output to our Logger class"""

# Copyright (c) 2014-2016 Timotheus Pokorra

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

from subprocess import Popen, PIPE, STDOUT
from Logger import Logger

class Shell:
  def __init__(self, logger):
    self.logger = logger

  def executeshell(self, command):
    self.logger.print("now running: " + command)

    # see http://stackoverflow.com/questions/14858059/detecting-the-end-of-the-stream-on-popen-stdout-readline
    # problem is that subprocesses are started, and the pipe is still open???
    child = Popen(command, stdout=PIPE, stderr=STDOUT, universal_newlines=True, shell=True)
    processFinished = False
    returncode=None
    #for line in iter(child.stdout.readline,''):
    while True:
      try:
        line=child.stdout.readline()
      except UnicodeDecodeError as e:
        line="UnicodeDecodeError Problem with decoding the log line"
      if "LBSERROR" in line:
        self.logger.print(line)
      if ((len(line) == 0) and processFinished): # or ("LBSScriptFinished" in line) or ("LBSERROR" in line):
        if not processFinished: # and ("LBSScriptFinished" in line or "LBSERROR" in line):
          returncode = child.poll()
          if returncode is None:
            returncode = 0
        break;
      self.logger.print(line)
      returncode = child.poll()
      if not processFinished and returncode is not None:
        processFinished = True
    return (not returncode)

  def evaluateshell(self, command):
    #self.logger.print("now running: " + command)
    result = ""

    # see http://stackoverflow.com/questions/14858059/detecting-the-end-of-the-stream-on-popen-stdout-readline
    # problem is that subprocesses are started, and the pipe is still open???
    child = Popen(command, stdout=PIPE, stderr=STDOUT, universal_newlines=True, shell=True)
    processFinished = False
    returncode=None
    #for line in iter(child.stdout.readline,''):
    while True:
      line=child.stdout.readline()
      if "LBSERROR" in line:
        self.logger.print(line)
      if ((len(line) == 0) and processFinished): # or ("LBSScriptFinished" in line) or ("LBSERROR" in line):
        if not processFinished: # and ("LBSScriptFinished" in line or "LBSERROR" in line):
          returncode = child.poll()
          if returncode is None:
            returncode = 0
        break;
      result += line
      #self.logger.print(line)
      returncode = child.poll()
      if not processFinished and returncode is not None:
        processFinished = True
    if (not returncode):
      return result
    return returncode
