#!/usr/bin/env python3
"""Logger: collects all the output"""

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
import codecs
import sys
import time
import smtplib
from smtplib import SMTP_SSL
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import OrderedDict
import Config
from Database import Database

class Logger:
  'collect all the output'

  def __init__(self, buildid=-1):
    self.lastTimeUpdate = int(time.time())
    self.startTimer()
    self.config = Config.LoadConfig()
    self.logspath = self.config['lbs']['LogsPath']
    self.emailserver = self.config['lbs']['EmailServer']
    self.emailport = self.config['lbs']['EmailPort']
    self.emailuser = self.config['lbs']['EmailUser']
    self.emailpassword = self.config['lbs']['EmailPassword']
    self.buildid = buildid

  def startTimer(self):
    self.starttime = time.time()
    self.linebuffer = []
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
      timeseconds = int(time.time() - self.starttime)
      timeprefix = "[" + str(int(timeseconds/60/60)).zfill(2) + ":" + str(int(timeseconds/60)%60).zfill(2) + ":" + str(timeseconds%60).zfill(2)  + "] "
      if "LBSERROR" in newOutput:
        self.error = True
      self.linebuffer.append(timeprefix + newOutput)

      # only write new lines every other second, to avoid putting locks on the database
      # also write often enough, do not collect too many lines
      if self.buildid != -1 and (self.lastTimeUpdate + 2 < int(time.time()) or len(self.linebuffer) > 20):
        con = Database(self.config)
        stmt = "INSERT INTO log(buildid, line) VALUES(?,?)"
        # write the lines to database, and then dump to file when build is finished
        for line in self.linebuffer:
          con.execute(stmt, (self.buildid, line))
        self.linebuffer = []
        con.commit()
        con.close()
      self.lastTimeUpdate = int(time.time())

      # sometimes we get incomplete bytes, and would get an ordinal not in range error
      # just ignore the exception...
      try:
        # TODO define in config.yml if we really want the output to the screen (ie uwsgi.log) or just to the log system
        sys.stdout.write(timeprefix + newOutput)
      except BlockingIOError:
        print("Logging print: problem with writing to stdout")
      finally:
        sys.stdout.flush() 

  def hasLBSERROR(self):
    return self.error

  def getLastLine(self):
    return self.lastLine.strip()

  def get(self, limit=None):
    if self.buildid == -1:
      return "no log available"

    con = Database(self.config)
    stmt = "SELECT * FROM log WHERE buildid = ? ORDER BY id DESC"
    if limit is not None:
      stmt = stmt + " LIMIT ?"
      cursor = con.execute(stmt, (self.buildid, limit))
    else:
      cursor = con.execute(stmt, (self.buildid,))
    data = cursor.fetchall()
    con.close()
    output = ""
    for row in data:
       output = row['line'] + output

    return output

  def email(self, fromAddress, toAddress, subject, logurl):
    if self.hasLBSERROR():
      subject = "ERROR " + subject
    link="For details, see <a href='" + logurl + "'>" + logurl + "</a><br/>\n"
    msg = MIMEText(("<html><body>" + link + "<pre>" + self.get(40) + "</pre></body></html>").encode('utf-8'), 'html','utf-8')
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
    if self.buildid != -1:
      # store buffered lines to the database
      con = Database(self.config)
      stmt = "INSERT INTO log(buildid, line) VALUES(?,?)"
      for line in self.linebuffer:
        con.execute(stmt, (self.buildid, line))
      self.linebuffer = []
      con.commit()
      con.close()

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

  def clean(self):
    # clear log from database
    if self.buildid != -1:
      con = Database(self.config)
      stmt = "DELETE FROM log WHERE buildid = ?"
      con.execute(stmt, (self.buildid, ))
      con.commit()
      con.close()

  def getLogFile(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildnumber):
    LogPath = self.logspath + "/" + self.getLogPath(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch)
    return LogPath + "/build-" + str(buildnumber).zfill(6) + ".log"

  def getLog(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildnumber):
    filename=self.getLogFile(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildnumber)
    if os.path.isfile(filename):
      with open(filename, 'r') as content_file:
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
        with codecs.open(LogPath + "/" + file, encoding='utf-8', mode='r') as f:
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
          with codecs.open(LogPath + "/" + file, encoding='utf-8', mode='r') as f:
            content = f.read()
            if content.find('LBSERROR') >= 0:
              result['resultcode'] = "failure"
    return result 
