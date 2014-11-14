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
from smtplib import SMTP_SSL
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import OrderedDict
import yaml

class Logger:
  'collect all the output'

  def __init__(self):
    self.logspath = "/var/www/logs"
    self.lastTimeUpdate = int(time.time())
    self.startTimer()
    configfile="../config.yml"
    stream = open(configfile, 'r')
    config = yaml.load(stream)
    self.emailserver = config['lbs']['EmailServer']
    self.emailport = config['lbs']['EmailPort']
    self.emailuser = config['lbs']['EmailUser']
    self.emailpassword = config['lbs']['EmailPassword']

  def startTimer(self):
    self.starttime = time.time()
    self.output = ""
    self.buffer = ""
    self.error = False
    self.lastLine = ""

  def print(self, newOutput):
    if len(newOutput) == 1 and newOutput != "\n":
      self.buffer += newOutput
    elif len(newOutput) > 0:
      if len(self.buffer) > 0:
        newOutput = self.buffer + newOutput
        self.buffer = ""
      self.lastLine = newOutput
      if newOutput[-1:] != "\n":
        newOutput += "\n"
      timeprefix = "[" + str(int(time.time() - self.starttime)).zfill(5) + "] "
      self.lastTimeUpdate = int(time.time())
      if "LBSERROR" in newOutput:
        self.error = True
      self.output += timeprefix + newOutput
      # sometimes we get incomplete bytes, and would get an ordinal not in range error
      # just ignore the exception...
      try:
        sys.stdout.write(timeprefix + newOutput)
      finally:
        sys.stdout.flush() 

  def hasLBSERROR(self):
    return self.error

  def getLastLine(self):
    return self.lastLine.strip()

  def get(self, limit=None):
    if limit is None:
      return self.output
    return self.output[-1*limit:]

  def email(self, fromAddress, toAddress, subject, logurl):
    if self.hasLBSERROR():
      subject = "ERROR " + subject
    link="For details, see <a href='" + logurl + "'>" + logurl + "</a><br/>\n"
    msg = MIMEText(("<html><body>" + link + "<pre>" + self.get(4000) + "</pre></body></html>").encode('utf-8'), 'html','utf-8')
    msg['From'] = fromAddress
    msg['To'] = toAddress
    msg['Subject'] = subject
    # Send the mail
    server = smtplib.SMTP_SSL(host=self.emailserver, port=self.emailport, timeout=10)
    TO = [toAddress] # must be a list
    try:
      server.login(self.emailuser, self.emailpassword)
      server.sendmail(fromAddress, TO, msg.as_string())
    finally:
      server.quit()

  def getLogPath(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
     return username + "/" + projectname + "/" + packagename + "/" + branchname + "/" + lxcdistro + "/" + lxcrelease + "/" + lxcarch

  def store(self, DeleteLogAfterDays, KeepMinimumLogs, logpath):
    LogPath = self.logspath + "/" + logpath
    if not os.path.exists(LogPath):
      os.makedirs( LogPath )
    buildnumber=0
    MaximumAgeInSeconds=time.time() - (DeleteLogAfterDays*24*60*60)
    logfiles=[] 
    for file in os.listdir(LogPath):
      if file.endswith(".log"):
        logfiles.append(file)
        oldnumber=int(file[6:-4])
        if oldnumber >= buildnumber:
          buildnumber = oldnumber + 1
    logfiles=sorted(logfiles)
    if len(logfiles) > KeepMinimumLogs:
      for i in range(1, len(logfiles) - KeepMinimumLogs):
        file=logfiles[i - 1]
        # delete older logs, depending on DeleteLogAfterDays
        if os.path.getmtime(LogPath + "/" + file) < MaximumAgeInSeconds:
          os.unlink(LogPath + "/" + file)
    self.print("This build took about " + str(int((time.time() - self.starttime) / 60)) + " minutes")
    with open(LogPath + "/build-" + str(buildnumber).zfill(6) + ".log", 'a') as f:
      f.write(self.get())
    return buildnumber 

  def getLog(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildnumber):
    LogPath = self.logspath + "/" + self.getLogPath(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch)
    filename=LogPath + "/build-" + str(buildnumber).zfill(6) + ".log"
    if os.path.is_file(filename):
      with open(filename + ".log", 'r') as content_file:
        return content_file.read()
    return ""

  def getBuildNumbers(self, username, projectname, packagename, branchname, buildtarget):
    LogPath = self.logspath + "/" + username + "/" + projectname + "/" + packagename + "/" + branchname + "/" + buildtarget
    result={}
    if not os.path.exists(LogPath):
      return result
    for file in os.listdir(LogPath):
      if file.endswith(".log"):
        number=int(file[6:-4])
        result[number] = {}
        result[number]["timefinished"] = time.ctime( os.path.getmtime(LogPath + "/" + file))
        result[number]["resultcode"] = "success"
        with open(LogPath + "/" + file, 'r') as f:
          content = f.read()
          if content.find('LBSERROR') >= 0:
            result[number]["resultcode"] = "failure"
    return OrderedDict(reversed(sorted(result.items())))

  def getLastBuild(self, username, projectname, packagename, branchname, buildtarget):
    LogPath = self.logspath + "/" + username + "/" + projectname + "/" + packagename + "/" + branchname + "/" + buildtarget
    result={}
    if not os.path.exists(LogPath):
      return result
    previousNumber = -1
    for file in os.listdir(LogPath):
      if file.endswith(".log"):
        number=int(file[6:-4])
        if number > previousNumber:
          previousNumber = number
          result = {}
          result['number'] = number
          result['resultcode'] = "success"
          with open(LogPath + "/" + file, 'r') as f:
            content = f.read()
            if content.find('LBSERROR') >= 0:
              result['resultcode'] = "failure"
    return result 
