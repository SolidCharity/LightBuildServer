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
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import OrderedDict

class Logger:
  'collect all the output'

  def __init__(self):
    self.logspath = "/var/www/logs"
    self.startTimer()

  def startTimer(self):
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

  def email(self, fromAddress, toAddress, subject, logurl):
    SERVER = "localhost"
    msg = MIMEMultipart()
    msg['From'] = fromAddress
    msg['To'] = toAddress
    msg['Subject'] = subject
    link="For details, see " + logurl + "\n"
    msg.attach(MIMEText((link+self.get(4000)).encode('utf-8'), 'plain','utf-8'))
    # Send the mail
    server = smtplib.SMTP(SERVER)
    TO = [toAddress] # must be a list
    server.sendmail(fromAddress, TO, msg.as_string())
    server.quit()

  def store(self, DeleteLogAfterDays, LogPath):
    LogPath = self.logspath + "/" + LogPath
    if not os.path.exists(LogPath):
      os.makedirs( LogPath )
    buildnumber=0
    MaximumAgeInSeconds=time.time() - (DeleteLogAfterDays*24*60*60)
    for file in os.listdir(LogPath):
      if file.endswith(".log"):
        oldnumber=int(file[6:-4])
        if oldnumber >= buildnumber:
          buildnumber = oldnumber + 1
        # delete older logs, depending on DeleteLogAfterDays
        if os.path.getmtime(LogPath + "/" + file) < MaximumAgeInSeconds:
          os.unlink(LogPath + "/" + file)
    with open(LogPath + "/build-" + str(buildnumber).zfill(6) + ".log", 'a') as f:
      f.write(self.get())
    return buildnumber 

  def getLog(self, username, projectname, packagename, lxcdistro, lxcrelease, lxcarch, buildnumber):
    LogPath = self.logspath + "/" + username + "/" + projectname + "/" + packagename + "/" + lxcdistro + "/" + lxcrelease + "/" + lxcarch
    with open(LogPath + "/build-" + str(buildnumber).zfill(6) + ".log", 'r') as content_file:
        return content_file.read() 

  def getBuildNumbers(self, username, projectname, packagename, buildtarget):
    LogPath = self.logspath + "/" + username + "/" + projectname + "/" + packagename + "/" + buildtarget
    result={}
    if not os.path.exists(LogPath):
      return result
    for file in os.listdir(LogPath):
      if file.endswith(".log"):
        number=int(file[6:-4])
        result[str(number)] = time.ctime( os.path.getmtime(LogPath + "/" + file))
    return OrderedDict(reversed(sorted(result.items()))) 
