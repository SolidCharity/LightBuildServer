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
import time
import smtplib

class Logger:
  'collect all the output'

  def __init__(self):
    self.starttime = time.time()
    self.output = "";
    self.buffer = "";

  def print(self, newOutput):
    if len(newOutput) == 1 and newOutput != "\n":
      self.buffer += newOutput
    elif len(newOutput) > 0:
      if len(self.buffer) > 0:
        newOutput = self.buffer + newOutput
        self.buffer = ""
      if newOutput[-1:] != "\n":
        newOutput += "\n"
      timeprefix = "[" + str(int(time.time() - self.starttime)).zfill(5) + "] "
      self.output += timeprefix + newOutput
      sys.stdout.write(timeprefix + newOutput)
      sys.stdout.flush()

  def get(self, limit=None):
    if limit is None:
      return self.output
    return self.output[-1*limit:]

  def email(self, fromAddress, toAddress, subject):
    SERVER = "localhost"
    FROM = fromAddress
    TO = [toAddress] # must be a list
    message = """\
    From: %s
    To: %s
    Subject: %s

    %s
    """ % (FROM, ", ".join(TO), subject, self.output)
    # Send the mail
    server = smtplib.SMTP(SERVER)
    server.sendmail(FROM, TO, message)
    server.quit()
