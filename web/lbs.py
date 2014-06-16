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
        return '''
        <form action="/do_login" method="post">
            Username: <input name="username" type="text" />
            Password: <input name="password" type="password" />
            <input value="Login" type="submit" />
        </form>
        '''

    def do_login(self):
        username = request.forms.get('username')
        password = request.forms.get('password')
        if self.check_login(username, password):
           response.set_cookie("account", username, secret='some-secret-key')
           return template("<p>Welcome {{name}}! You are now logged in.</p><br/><a href='/'>Back to main page</a>", name=username)
        else:
           return "<p>Login failed.</p>"

    def logout(self):
        username = request.get_cookie("account", secret='some-secret-key')
        if not username:
            return "You are not logged in. Access denied. <br/><a href='/login'>Login</a>"
        response.delete_cookie("account")
        return template("<p>{{name}}, you are now logged out!</p><br/><a href='/'>Back to main page</a>", name=username);

    def buildproject(self, projectname, lxcdistro, lxcrelease, lxcarch):
        # TODO calculate dependancies between packages inside the project, and build in correct order
        return self.list();

    def getLbsName(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
        return username+"-"+projectname+"-"+packagename+"-"+branchname+"-"+lxcdistro+"-"+lxcrelease+"-"+lxcarch

    def triggerbuild(self, projectname, packagename, lxcdistro, lxcrelease, lxcarch):
        return self.triggerbuildwithbranch(projectname, packagename, "master", lxcdistro, lxcrelease, lxcarch)

    def triggerbuildwithbranch(self, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
        username = request.get_cookie("account", secret='some-secret-key')
        if not username:
            return "You are not logged in. Access denied. <br/><a href='/login'>Login</a>"

        lbsName=self.getLbsName(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)
        if lbsName in self.recentlyFinishedLbsList:
          del self.recentlyFinishedLbsList[lbsName]
        if not lbsName in self.lbsList:
          self.ToBuild.append(lbsName)
          self.buildqueue.append((username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch))
        bottle.redirect("/livelog/"+username+"/"+projectname+"/"+packagename+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease+"/"+lxcarch)

    def triggerbuildwithpwd(self, projectname, packagename, lxcdistro, lxcrelease, lxcarch, username, password):
      return self.triggerbuildwithbranchandpwd(projectname, packagename, "master", lxcdistro, lxcrelease, lxcarch, username, password)

    def triggerbuildwithbranchandpwd(self, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, username, password):
      if self.check_login(username, password):
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
            return template('buildresult', buildresult="We are waiting for a build machine to become available...", timeoutInSeconds=10, username=username, projectname=projectname, packagename=packagename, branchname=branchname, auth_username=username)
          else:
            return template('buildresult', buildresult="No build is planned for this package at the moment...", timeoutInSeconds=-1, username=username, projectname=projectname, packagename=packagename, branchname=branchname, auth_username=username)

        if lbs.finished:
          output = lbs.logger.get()
          # stop refreshing
          timeout=-1
        else:
          output = lbs.logger.get(4000)
          timeout = 2

        return template('buildresult', buildresult=output, timeoutInSeconds=timeout, username=username, projectname=projectname, packagename=packagename, branchname=branchname, auth_username=auth_username)

    def listMachines(self):
      # for displaying the logout link
      auth_username = request.get_cookie("account", secret='some-secret-key')

      buildmachines={}
      lbs = LightBuildServer(Logger())
      for buildmachine in self.config['lbs']['Machines']:
        buildmachines[buildmachine] = lbs.GetBuildMachineState(buildmachine)

      return template('machines', buildmachines=buildmachines, auth_username=auth_username)

    def listProjects(self):
      # for displaying the logout link
      auth_username = request.get_cookie("account", secret='some-secret-key')

      # TODO support several users ???
      for user in self.config['lbs']['Users']:
        userconfig=self.config['lbs']['Users'][user]
        for project in userconfig['Projects']:
          projectconfig=userconfig['Projects'][project]
          for package in projectconfig:
            projectconfig[package]["detailurl"] = "/detail/" + user + "/" + project + "/" + package
            projectconfig[package]["buildurl"] = "/triggerbuild/" + project + "/" + package
        return template('projects', projects = userconfig['Projects'], auth_username=auth_username)

    def detail(self, username, projectname, packagename):
        # for displaying the logout link
        auth_username = request.get_cookie("account", secret='some-secret-key')

        user=self.config['lbs']['Users'][username]
        project=user['Projects'][projectname]
        package=project[packagename]
        package["giturl"] = user['GitURL']+"lbs-" + projectname + "/tree/master/" + packagename
        package["buildurl"] = "/triggerbuild/" + projectname + "/" + packagename
        package["logs"] = {}
        package["repoinstructions"] = {}
        if not "Branches" in package:
          package["Branches"] = ["master"]
        for branchname in package["Branches"]:
          for buildtarget in package['Distros']:
            package["logs"][buildtarget+"-"+branchname] = Logger().getBuildNumbers(username, projectname, packagename, branchname, buildtarget)
        for buildtarget in package['Distros']:
          buildHelper = BuildHelperFactory.GetBuildHelper(buildtarget.split("/")[0], None, "", username, projectname, packagename)
          package["repoinstructions"][buildtarget] = buildHelper.GetRepoInstructions(self.config['lbs']['LBSUrl'], buildtarget)
        return template('detail', username=username, projectname=projectname, packagename=packagename, package=package, auth_username=auth_username)

    def logs(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildnumber):
      # for displaying the logout link
      auth_username = request.get_cookie("account", secret='some-secret-key')

      content = Logger().getLog(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildnumber)
      return template('buildresult', buildresult=content, timeoutInSeconds=-1, username=username, projectname=projectname, packagename=packagename, branchname=branchname, auth_username=auth_username)

    def repo(self, filepath):
      return static_file(filepath, root='/var/www/repos')

    def tarball(self, filepath):
      return static_file(filepath, root='/var/www/tarballs')

    def css(self, filename):
      return static_file(filename, root=os.path.dirname(os.path.realpath(__file__)) + "/css/")

    def manageBuildMachines(self, action, buildmachine):
      # TODO: need admin status to manage machines?
      username = request.get_cookie("account", secret='some-secret-key')
      if not username:
        return "You are not logged in. Access denied. <br/><a href='/login'>Login</a>"
      if action == "reset":
        LightBuildServer(Logger()).ReleaseMachine(buildmachine)
      return template("<p>The machine {{buildmachine}} should now be available.</p><br/><a href='/'>Back to main page</a>", buildmachine=buildmachine)

myApp=LightBuildServerWeb()
bottle.route('/login')(myApp.login)
bottle.route('/do_login', method="POST")(myApp.do_login)
bottle.route('/logout')(myApp.logout)
bottle.route('/buildproject/<projectname>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.buildproject)
bottle.route('/triggerbuild/<projectname>/<packagename>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.triggerbuild)
bottle.route('/triggerbuild/<projectname>/<packagename>/<branchname>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.triggerbuildwithbranch)
bottle.route('/triggerbuild/<projectname>/<packagename>/<lxcdistro>/<lxcrelease>/<lxcarch>/<username>/<password>')(myApp.triggerbuildwithpwd)
bottle.route('/triggerbuild/<projectname>/<packagename>/<branchname>/<lxcdistro>/<lxcrelease>/<lxcarch>/<username>/<password>')(myApp.triggerbuildwithbranchandpwd)
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
ipaddress=socket.gethostbyname(socket.gethostname()) 
bottle.run(host=ipaddress, port=80, debug=False) 
