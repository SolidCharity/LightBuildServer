#!/usr/bin/env python3
"""Logger: collects all the output"""

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
import sys

class Logger:
  'collect all the output'

  def __init__(self):
    self.output = "";
    self.buffer = "";

  def print(self, newOutput):
    if len(newOutput) == 1 and newOutput != "\n":
      self.buffer += newOutput
    else:
      if len(self.buffer) > 0:
        newOutput = self.buffer + newOutput
        self.buffer = ""
      self.output += newOutput
      if self.output[-1:] != "\n":
        self.output += "\n"
      sys.stdout.write(newOutput)
      sys.stdout.flush()

  def get(self, limit=None):
    if limit is None:
      return self.output
    return self.output[-1*limit:]

