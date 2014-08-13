#!/usr/bin/env python3
import sys
import bottle
import os
import time
from bottle import route, run, template, static_file, request, response
import lxc
import socket
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
from LightBuildServer import LightBuildServer
from BuildHelper import BuildHelper
from BuildHelperFactory import BuildHelperFactory
from Logger import Logger
from threading import Thread
import yaml
import copy
from collections import deque

class LightBuildServerWeb:
    def __init__(self):
        configfile="../config.yml"
        stream = open(configfile, 'r')
        self.config = yaml.load(stream)
        self.lbsList = {}
        self.recentlyFinishedLbsList = {}
        self.buildqueue = deque()
        self.ToBuild = deque()
        thread = Thread(target = self.buildqueuethread, args=())
        thread.start()

    def check_login(self, username, password):
        if username in self.config['lbs']['Users'] and self.config['lbs']['Users'][username]['Password'] == password:
          return True
        return False;

    def login(self):
        username = request.get_cookie("account", secret='some-secret-key')
        return template('login', auth_username=username, title="Login")

    def do_login(self):
        username = request.forms.get('username')
        password = request.forms.get('password')
        if self.check_login(username, password):
           response.set_cookie("account", username, secret='some-secret-key')
           return template("message", title="Welcome", message="Welcome " + username + "! You are now logged in.", redirect="/")
        else:
           return template("message", title="Login failed", message="Login failed. Please try again.", redirect="/login")

    def pleaselogin(self):
        return template("message", title="Please login", message="You are not logged in. Access denied. Please login!", redirect="/login")

    def logout(self):
        username = request.get_cookie("account", secret='some-secret-key')
        if not username:
            return self.pleaselogin()
        response.delete_cookie("account")
        return template("message", title="Logged out", message=username+", you are now logged out!", redirect="/")

    def buildproject(self, projectname, lxcdistro, lxcrelease, lxcarch):
        # TODO calculate dependancies between packages inside the project, and build in correct order
        return self.list();

    def getLbsName(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
        return username+"-"+projectname+"-"+packagename+"-"+branchname+"-"+lxcdistro+"-"+lxcrelease+"-"+lxcarch

    def getLogoutAuthUsername(self):
        # return only the username if other users exist in the config file
        auth_username = request.get_cookie("account", secret='some-secret-key')
        if auth_username is None:
          return ""
        for user in self.config['lbs']['Users']:
          if not user == auth_username:
            return " " + auth_username
        return ""

    def triggerbuild(self, username, projectname, packagename, lxcdistro, lxcrelease, lxcarch):
        return self.triggerbuildwithbranch(username, projectname, packagename, "master", lxcdistro, lxcrelease, lxcarch)

    def triggerbuildwithbranch(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
        auth_username = request.get_cookie("account", secret='some-secret-key')
        if not auth_username:
            return self.pleaselogin()
        if not auth_username == username:
            return template("message", title="Wrong user", message="You are logged in with username "+auth_username + ". Access denied. Please login as " + username + "!", redirect="/detail/" + username + "/" + projectname + "/" + packagename)

        lbsName=self.getLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
        if lbsName in self.recentlyFinishedLbsList:
          del self.recentlyFinishedLbsList[lbsName]
        if not lbsName in self.lbsList:
          self.ToBuild.append(lbsName)
          self.buildqueue.append((username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch))
        bottle.redirect("/livelog/"+username+"/"+projectname+"/"+packagename+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease+"/"+lxcarch)

    def triggerbuildwithpwd(self, username, projectname, packagename, lxcdistro, lxcrelease, lxcarch, auth_username, password):
      return self.triggerbuildwithbranchandpwd(projectname, username, packagename, "master", lxcdistro, lxcrelease, lxcarch, auth_username, password)

    def triggerbuildwithbranchandpwd(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, auth_username, password):
      # note: we are not using the template message, because this will be processed by scripts usually
      if auth_username == username and self.check_login(auth_username, password):
        lbsName=self.getLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
        if not lbsName in self.lbsList:
          self.ToBuild.append(lbsName)
          self.buildqueue.append((username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch))
          return template("<p>Build for {{lbsName}} has been triggered.</p><br/><a href='/'>Back to main page</a>", lbsName=lbsName)
        else:
          return template("<p>{{lbsName}} is already in the build queue.</p><br/><a href='/'>Back to main page</a>", lbsName=lbsName)
      return template("<p>wrong username {{username}} or password.</p><br/><a href='/'>Back to main page</a>", username=username)

    def WaitForBuildJobFinish(self, thread, lbsName):
      thread.join()
      self.recentlyFinishedLbsList[lbsName] = self.lbsList[lbsName] 
      del self.lbsList[lbsName]

    def buildqueuethread(self):
      while True:
        if len(self.buildqueue) > 0:
          # peek at the leftmost item
          item = self.buildqueue[0]
          username = item[0]
          projectname = item[1]
          packagename = item[2]
          branchname = item[3]
          lxcdistro = item[4]
          lxcrelease = item[5]
          lxcarch = item[6]
          lbsName=self.getLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
          lbs=LightBuildServer(Logger())
          # get name of available slot
          buildmachine=lbs.GetAvailableBuildMachine(buildjob=username+"/"+projectname+"/"+packagename+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease+"/"+lxcarch)
          if not buildmachine == None:
            self.lbsList[lbsName] = lbs
            thread = Thread(target = lbs.buildpackage, args = (username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildmachine))
            thread.start()
            threadWait = Thread(target = self.WaitForBuildJobFinish, args = (thread, lbsName))
            threadWait.start()
            self.ToBuild.remove(lbsName)
            self.buildqueue.remove(item)
        # sleep two seconds before looping through buildqueue again
        time.sleep(2)

    def livelog(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
        # for displaying the logout link
        auth_username = request.get_cookie("account", secret='some-secret-key')

        lbsName=self.getLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
        if lbsName in self.recentlyFinishedLbsList:
          lbs = self.recentlyFinishedLbsList[lbsName] 
        elif lbsName in self.lbsList:
          lbs = self.lbsList[lbsName]
        else:
          if lbsName in self.ToBuild: 
            return template('buildresult', buildresult="We are waiting for a build machine to become available...", timeoutInSeconds=10, username=username, projectname=projectname, packagename=packagename, branchname=branchname, auth_username=username, logout_auth_username=self.getLogoutAuthUsername())
          else:
            return template('buildresult', buildresult="No build is planned for this package at the moment...", timeoutInSeconds=-1, username=username, projectname=projectname, packagename=packagename, branchname=branchname, auth_username=username, logout_auth_username=self.getLogoutAuthUsername())

        if lbs.finished:
          output = lbs.logger.get()
          # stop refreshing
          timeout=-1
        else:
          output = lbs.logger.get(4000)
          timeout = 2

        return template('buildresult', buildresult=output, timeoutInSeconds=timeout, username=username, projectname=projectname, packagename=packagename, branchname=branchname, auth_username=auth_username, logout_auth_username=self.getLogoutAuthUsername())

    def listMachines(self):
      # for displaying the logout link
      auth_username = request.get_cookie("account", secret='some-secret-key')

      buildmachines={}
      lbs = LightBuildServer(Logger())
      for buildmachine in self.config['lbs']['Machines']:
        buildmachines[buildmachine] = lbs.GetBuildMachineState(buildmachine)

      return template('machines', buildmachines=buildmachines, auth_username=auth_username, logout_auth_username=self.getLogoutAuthUsername())

    def listProjects(self):
      # for displaying the logout link
      auth_username = request.get_cookie("account", secret='some-secret-key')

      users={}
      for user in self.config['lbs']['Users']:
        userconfig=copy.deepcopy(self.config['lbs']['Users'][user])
        for project in userconfig['Projects']:
          projectconfig=userconfig['Projects'][project]
          if 'Packages' in projectconfig:
            packages = userconfig['Projects'][project]['Packages']
          else:
            packages = userconfig['Projects'][project]
          for package in packages:
            if not package in projectconfig:
              projectconfig[package] = {}
            if 'Distros' in projectconfig:
              projectconfig[package]['Distros'] = projectconfig['Distros']
            projectconfig[package]['detailurl'] = "/detail/" + user + "/" + project + "/" + package
            projectconfig[package]['buildurl'] = "/triggerbuild/" + user + "/" + project + "/" + package
          if 'Distros' in projectconfig:
            del projectconfig['Distros']
          if 'Packages' in projectconfig:
            del projectconfig['Packages']
        users[user] = userconfig['Projects']
      return template('projects', users = users, auth_username=auth_username, logout_auth_username=self.getLogoutAuthUsername())

    def detail(self, username, projectname, packagename):
        # for displaying the logout link
        auth_username = request.get_cookie("account", secret='some-secret-key')

        user=copy.deepcopy(self.config['lbs']['Users'][username])
        project=user['Projects'][projectname]
        if 'Packages' in project:
          project[packagename] = project['Packages']
        package=project[packagename]
        package["giturl"] = user['GitURL']+"lbs-" + projectname + "/tree/master/" + packagename
        package["buildurl"] = "/triggerbuild/" + username + "/" + projectname + "/" + packagename
        package["logs"] = {}
        package["repoinstructions"] = {}
        if not "Branches" in package:
          package["Branches"] = ["master"]
        for branchname in package["Branches"]:
          if not 'Distros' in package:
            package['Distros'] = project['Distros']
          for buildtarget in package['Distros']:
            package["logs"][buildtarget+"-"+branchname] = Logger().getBuildNumbers(username, projectname, packagename, branchname, buildtarget)
        for buildtarget in package['Distros']:
          buildHelper = BuildHelperFactory.GetBuildHelper(buildtarget.split("/")[0], None, "", username, projectname, packagename)
          package["repoinstructions"][buildtarget] = buildHelper.GetRepoInstructions(self.config['lbs']['LBSUrl'], buildtarget)
        return template('detail', username=username, projectname=projectname, packagename=packagename, package=package, auth_username=auth_username, logout_auth_username=self.getLogoutAuthUsername())

    def logs(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildnumber):
      # for displaying the logout link
      auth_username = request.get_cookie("account", secret='some-secret-key')

      content = Logger().getLog(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildnumber)
      return template('buildresult', buildresult=content, timeoutInSeconds=-1, username=username, projectname=projectname, packagename=packagename, branchname=branchname, auth_username=auth_username, logout_auth_username=self.getLogoutAuthUsername())

    def repo(self, filepath):
      return static_file(filepath, root='/var/www/repos')

    def tarball(self, filepath):
      return static_file(filepath, root='/var/www/tarballs')

    def css(self, filename):
      return static_file(filename, root=os.path.dirname(os.path.realpath(__file__)) + "/css/")
    def ext(self, filepath):
      return static_file(filepath, root=os.path.dirname(os.path.realpath(__file__)) + "/ext/")

    def manageBuildMachines(self, action, buildmachine):
      # TODO: need admin status to manage machines?
      username = request.get_cookie("account", secret='some-secret-key')
      if not username:
        return self.pleaselogin()
      if action == "reset":
        LightBuildServer(Logger()).ReleaseMachine(buildmachine)
      return template("message", title="machine available", message="The machine "+buildmachine+" should now be available.", redirect="/machines")

myApp=LightBuildServerWeb()
bottle.route('/login')(myApp.login)
bottle.route('/do_login', method="POST")(myApp.do_login)
bottle.route('/logout')(myApp.logout)
bottle.route('/buildproject/<projectname>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.buildproject)
bottle.route('/triggerbuild/<username>/<projectname>/<packagename>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.triggerbuild)
bottle.route('/triggerbuild/<username>/<projectname>/<packagename>/<branchname>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.triggerbuildwithbranch)
bottle.route('/triggerbuild/<username>/<projectname>/<packagename>/<lxcdistro>/<lxcrelease>/<lxcarch>/<auth_username>/<password>')(myApp.triggerbuildwithpwd)
bottle.route('/triggerbuild/<username>/<projectname>/<packagename>/<branchname>/<lxcdistro>/<lxcrelease>/<lxcarch>/<auth_username>/<password>')(myApp.triggerbuildwithbranchandpwd)
bottle.route('/livelog/<username>/<projectname>/<packagename>/<branchname>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.livelog)
bottle.route('/detail/<username>/<projectname>/<packagename>')(myApp.detail)
bottle.route('/')(myApp.listProjects)
bottle.route('/projects')(myApp.listProjects)
bottle.route('/logs/<username>/<projectname>/<packagename>/<branchname>/<lxcdistro>/<lxcrelease>/<lxcarch>/<buildnumber>')(myApp.logs)
bottle.route('/repos/<filepath:path>')(myApp.repo)
bottle.route('/tarballs/<filepath:path>')(myApp.tarball)
bottle.route('/machines')(myApp.listMachines)
bottle.route('/machines/<action>/<buildmachine>')(myApp.manageBuildMachines)
bottle.route('/css/<filename>')(myApp.css)
bottle.route('/ext/<filepath:path>')(myApp.ext)
ipaddress=socket.gethostbyname(socket.gethostname()) 
bottle.run(host=ipaddress, port=80, debug=False) 
