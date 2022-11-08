#!/usr/bin/env python3
"""Logger: collects all the output"""

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
import codecs
import sys
import time
import datetime
import smtplib
from smtplib import SMTP_SSL
import os
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from collections import OrderedDict

from django.conf import settings
from django.utils import timezone
from django.utils.timezone import make_aware

from builder.models import Build, Log

class Logger:
  'collect all the output'

  def __init__(self, build=None):
    self.lastTimeUpdate = timezone.now()
    self.startTimer()
    self.logspath = settings.LOGS_PATH
    self.emailserver = settings.EMAIL_SERVER
    self.emailport = settings.EMAIL_PORT
    self.emailuser = settings.EMAIL_USER
    self.emailpassword = settings.EMAIL_PASSWORD
    self.build = build
    self.MaxDebugLevel = settings.MAX_DEBUG_LEVEL

  def startTimer(self):
    self.starttime = timezone.now()
    self.linebuffer = []
    self.buffer = ""
    self.error = False
    self.lastLine = ""

  def print(self, newOutput, DebugLevel=1):
    if len(newOutput) == 1 and newOutput != "\n":
      self.buffer += newOutput
    elif len(newOutput) > 0:
      if len(self.buffer) > 0:
        newOutput = self.buffer + newOutput
        self.buffer = ""
      self.lastLine = newOutput
      if newOutput[-1:] != "\n":
        newOutput += "\n"
      timeseconds = round((timezone.now() - self.starttime).total_seconds())
      timeprefix = "[" + str(int(timeseconds/60/60)).zfill(2) + ":" + str(int(timeseconds/60)%60).zfill(2) + ":" + str(timeseconds%60).zfill(2)  + "] "
      if "LBSERROR" in newOutput:
        self.error = True
      self.linebuffer.append(timeprefix + newOutput)

      # only write new lines every other second, to avoid putting locks on the database
      # also write often enough, do not collect too many lines
      if self.build and ((timezone.now() - self.lastTimeUpdate).total_seconds() > 2 or len(self.linebuffer) > 20):

        # write the lines to database, and then dump to file when build is finished
        for line in self.linebuffer:
            log = Log(build = self.build, line = line, created = timezone.now())
            log.save()
        self.linebuffer = []
      self.lastTimeUpdate = timezone.now()

      # sometimes we get incomplete bytes, and would get an ordinal not in range error
      # just ignore the exception...
      try:
        if DebugLevel <= self.MaxDebugLevel:
          print(timeprefix + newOutput)
      except BlockingIOError:
        print("Logging print: problem with writing to stdout")
      finally:
        sys.stdout.flush() 

  def hasLBSERROR(self):
    return self.error

  def getLastLine(self):
    return self.lastLine.strip()

  def get(self, limit=None):
    if not self.build:
      return "no log available"

    log = Log.objects.filter(build = self.build)
    if limit is not None:
      log = log[:limit]
    output = ""
    for row in log:
       output += row.line

    return output

  def email(self, fromAddress, toAddress, subject, logurl):
    if self.hasLBSERROR():
      subject = "ERROR " + subject
    link="For details, see <a href='" + logurl + "'>" + logurl + "</a><br/>\n"
    msg = MIMEText(("<html><body>" + link + "<pre>" + self.get(40) + "</pre></body></html>").encode('utf-8'), 'html','utf-8')
    msg['From'] = fromAddress
    msg['To'] = toAddress
    msg['Subject'] = subject
    msg["Date"] = formatdate(localtime=True)
    # Send the mail
    server = smtplib.SMTP(host=self.emailserver, port=self.emailport, timeout=10)
    TO = [toAddress] # must be a list
    try:
      server.ehlo()
      server.starttls()
      server.login(self.emailuser, self.emailpassword)
      server.sendmail(fromAddress, TO, msg.as_string())
    finally:
      server.quit()

  def getLogPath(self, build):
     return build.user.username + "/" + build.project + "/" + build.package + "/" + build.branchname + "/" + build.distro + "/" + build.release + "/" + build.arch

  def store(self, DeleteLogAfterDays, KeepMinimumLogs, logpath):
    if self.build and self.build.id:
      # store buffered lines to the database
      for line in self.linebuffer:
        log = Log(build = self.build, line = line, created=timezone.now())
        log.save()
      self.linebuffer = []

    LogPath = self.logspath + "/" + logpath
    if not os.path.exists(LogPath):
      os.makedirs( LogPath )
    buildnumber=0
    MaximumAgeInSeconds = timezone.now() - datetime.timedelta(days = DeleteLogAfterDays)
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
        if make_aware(datetime.datetime.fromtimestamp(os.path.getmtime(LogPath + "/" + file))) < MaximumAgeInSeconds:
          os.unlink(LogPath + "/" + file)
    self.print("This build took about " + str(round((timezone.now() - self.starttime).total_seconds() / 60)) + " minutes")
    LogFilePath = self.getLogFile(self.build)
    try:
      with open(LogFilePath, 'ab') as f:
        f.write(self.get().encode('utf8'))
    except:
      print ("Unexpected error:", sys.exc_info())
    sys.stdout.flush()

    return buildnumber

  def clean(self):
    # clear log from database
    if self.build:
      logs = Log.objects.filter(build = self.build)
      logs.delete()

  def getLogFile(self, build):
    LogPath = self.logspath + "/" + self.getLogPath(build)
    Path(LogPath).mkdir(parents=True, exist_ok=True)
    return LogPath + "/build-" + str(build.id).zfill(6) + ".log"

  def getLog(self, build):
    filename=self.getLogFile(build)
    if os.path.isfile(filename):
      with open(filename, 'r', encoding="utf-8") as content_file:
        return content_file.read()
    return ""

  def getBuildsOfPackage(self, package):
    result = dict()

    builds = Build.objects. \
        filter(user = package.project.user). \
        filter(project=package.project.name). \
        filter(package=package.name).order_by('-id')

    for b in builds:
        key = f"{b.distro}/{b.release}/{b.arch}-{b.branchname}"
        if not key in result:
            result[key] = []
        if len(result[key]) < settings.DISPLAY_MAX_BUILDS_PER_PACKAGE:
            result[key].append(b)

    return result


  def getBuildResult(self):
    LogFilePath = self.getLogFile(self.build)
    if not os.path.exists(LogFilePath):
      return "failure"
    with codecs.open(LogFilePath, encoding='utf-8', mode='r') as f:
        content = f.read()
    if content.find('LBSERROR') >= 0:
        return "failure"
    return "success"
