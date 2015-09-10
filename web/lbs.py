#!/usr/bin/env python3
"""Light Build Server: build packages for various distributions, using linux containers"""

# Copyright (c) 2014-2015 Timotheus Pokorra

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
import bottle
import os
from bottle import route, run, template, static_file, request, response
import socket
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
from LightBuildServer import LightBuildServer
from BuildHelper import BuildHelper
from BuildHelperFactory import BuildHelperFactory
from Logger import Logger
import Config
import copy

class LightBuildServerWeb:
    def __init__(self):
        self.config = Config.LoadConfig()
        self.LBS = LightBuildServer()

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

    def getLogoutAuthUsername(self):
        # return only the username if other users exist in the config file
        auth_username = request.get_cookie("account", secret='some-secret-key')
        if auth_username is None:
          return ""
        for user in self.config['lbs']['Users']:
          if not user == auth_username:
            return " " + auth_username
        return ""

    def checkPermission(self, auth_username, username):
        if 'Secret' in self.config['lbs']['Users'][username] and not auth_username == username:
          return template("message", title="Error", message="You don't have the permissions to see this content", redirect="/")
        return None

    def processbuildqueue(self):
      try:
        self.LBS.ProcessBuildQueue()
      except:
        print("Unexpected error:", sys.exc_info()[0])
        print(sys.exc_info())

    def cancelplannedbuild(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
      # for displaying the logout link
      auth_username = request.get_cookie("account", secret='some-secret-key')

      if auth_username is None:
        return template('message', title="Error", message="You must be logged in to cancel a planned build", redirect="/login")

      try:
        self.LBS.CancelPlannedBuild(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch)
        return template("message", title="Success", message="Build job has been removed from the queue", redirect="/machines")
      except:
        print("Unexpected error:", sys.exc_info()[0])
        print(sys.exc_info())

    def buildproject(self, username, projectname, lxcdistro, lxcrelease, lxcarch):
        auth_username = request.get_cookie("account", secret='some-secret-key')
        if not auth_username:
            return self.pleaselogin()
        if not auth_username == username:
            return template("message", title="Wrong user", message="You are logged in with username "+auth_username + ". Access denied. Please login as " + username + "!", redirect="/project/" + username + "/" + projectname)

        message = self.LBS.BuildProject(username, projectname, lxcdistro, lxcrelease, lxcarch)

        # TODO redirect to build queue listing
        return template("<p>Build for project {{projectname}} has been triggered.</p>{{message}}<br/><a href='/'>Back to main page</a>", projectname=projectname, message=message)

    def triggerbuild(self, username, projectname, packagename, lxcdistro, lxcrelease, lxcarch):
        return self.triggerbuildwithbranch(username, projectname, packagename, "master", lxcdistro, lxcrelease, lxcarch)

    def triggerbuildwithbranch(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
        auth_username = request.get_cookie("account", secret='some-secret-key')
        if not auth_username:
            return self.pleaselogin()
        if not auth_username == username:
            return template("message", title="Wrong user", message="You are logged in with username "+auth_username + ". Access denied. Please login as " + username + "!", redirect="/package/" + username + "/" + projectname + "/" + packagename)

        self.LBS.BuildProjectWithBranch(username,projectname,packagename,branchname,lxcdistro,lxcrelease,lxcarch)

        bottle.redirect("/livelog/"+username+"/"+projectname+"/"+packagename+"/"+branchname+"/"+lxcdistro+"/"+lxcrelease+"/"+lxcarch)

    def triggerbuildwithpwd(self, username, projectname, packagename, lxcdistro, lxcrelease, lxcarch, auth_username, password):
      return self.triggerbuildwithbranchandpwd(projectname, username, packagename, "master", lxcdistro, lxcrelease, lxcarch, auth_username, password)

    def triggerbuildwithbranchandpwd(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, auth_username, password):
      # note: we are not using the template message, because this will be processed by scripts usually
      if not (auth_username == username and self.check_login(auth_username, password)):
       return template("<p>wrong username {{username}} or password.</p><br/><a href='/'>Back to main page</a>", username=username)

      message = self.LBS.BuildProjectWithBranchAndPwd(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, auth_username, password)
 
      return template("<p>" + message + "</p><br/><a href='/'>Back to main page</a>", lbsName="")

    def triggerbuildprojectwithpwd(self, username, projectname, lxcdistro, lxcrelease, lxcarch, auth_username, password):
      # note: we are not using the template message, because this will be processed by scripts usually
      if not (auth_username == username and self.check_login(auth_username, password)):
       return template("<p>wrong username {{username}} or password.</p><br/><a href='/'>Back to main page</a>", username=username)

      message = self.LBS.BuildProject(username, projectname, lxcdistro, lxcrelease, lxcarch)
 
      return template("<p>" + message + "</p><br/><a href='/'>Back to main page</a>", lbsName="")

    def livelog(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch):
        # for displaying the logout link
        auth_username = request.get_cookie("account", secret='some-secret-key')
       
        output = self.checkPermission(auth_username, username)
        if output is not None:
          return output

        (output, timeout) = self.LBS.LiveLog(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch)

        return template('buildresult', buildresult=output, timeoutInSeconds=timeout, username=username, projectname=projectname, packagename=packagename, branchname=branchname, buildtarget=lxcdistro + "/" + lxcrelease + "/" + lxcarch, auth_username=auth_username, logout_auth_username=self.getLogoutAuthUsername())

    def listMachines(self):
      # for displaying the logout link
      auth_username = request.get_cookie("account", secret='some-secret-key')

      if auth_username is None:
        return template('message', title="Error", message="You must be logged in to see the machines", redirect="/login")

      buildmachines={}
      for buildmachine in self.config['lbs']['Machines']:
        buildmachines[buildmachine] = self.LBS.GetBuildMachineState(buildmachine)

      return template('machines', buildmachines=buildmachines, jobs=self.LBS.GetBuildQueue(), finishedjobs=self.LBS.GetFinishedQueue(), auth_username=auth_username, logout_auth_username=self.getLogoutAuthUsername())

    def listProjects(self):
      # for displaying the logout link
      auth_username = request.get_cookie("account", secret='some-secret-key')

      users={}
      for user in self.config['lbs']['Users']:
        userconfig=copy.deepcopy(self.config['lbs']['Users'][user])
        if 'Secret' in userconfig and not auth_username == user:
          continue
        for project in userconfig['Projects']:
          projectconfig=userconfig['Projects'][project]
          if not 'Packages' in projectconfig:
            packages = {}
            for package in userconfig['Projects'][project]:
              packages[package] = userconfig['Projects'][project][package]
            userconfig['Projects'][project]['Packages'] = packages
          packages = userconfig['Projects'][project]['Packages']
          for package in packages:
            if packages[package] is None:
              packages[package] = {}
            if 'Distros' in projectconfig:
              packages[package]['Distros'] = projectconfig['Distros']
            packages[package]['packageurl'] = "/package/" + user + "/" + project + "/" + package
        users[user] = userconfig['Projects']
      return template('projects', users = users, auth_username=auth_username, logout_auth_username=self.getLogoutAuthUsername())

    def project(self, user, project):
        # for displaying the logout link
        auth_username = request.get_cookie("account", secret='some-secret-key')

        output = self.checkPermission(auth_username, user)
        if output is not None:
          return output

        userconfig=copy.deepcopy(self.config['lbs']['Users'][user])
        buildtargets={}

        projectconfig=userconfig['Projects'][project]
        if not 'Packages' in projectconfig:
          packages = {}
          for package in userconfig['Projects'][project]:
            packages[package] = userconfig['Projects'][project][package]
          userconfig['Projects'][project]['Packages'] = packages
        packages = userconfig['Projects'][project]['Packages']
        for package in packages:
          if packages[package] is None:
            packages[package] = {}
          if 'Distros' in projectconfig:
            packages[package]['Distros'] = projectconfig['Distros']
          packages[package]['packageurl'] = "/package/" + user + "/" + project + "/" + package
          packages[package]['buildurl'] = "/triggerbuild/" + user + "/" + project + "/" + package
          packages[package]['buildresult'] = {}
          for buildtarget in packages[package]['Distros']:
            if not buildtarget in buildtargets:
              buildtargets[buildtarget] = 1
            packages[package]['buildresult'][buildtarget] = Logger().getLastBuild(user, project, package, "master", buildtarget)
        users={}
        users[user] = userconfig['Projects']

        return template('project', users = users, buildtargets=buildtargets, auth_username=auth_username, username=user, project=project, logout_auth_username=self.getLogoutAuthUsername())

    def package(self, username, projectname, packagename):
        # for displaying the logout link
        auth_username = request.get_cookie("account", secret='some-secret-key')

        output = self.checkPermission(auth_username, username)
        if output is not None:
          return output

        user=copy.deepcopy(self.config['lbs']['Users'][username])
        project=user['Projects'][projectname]
        if 'Packages' in project:
          project[packagename] = project['Packages'][packagename]
        package=project[packagename]
        if package == None:
          package = dict()
        elif not isinstance(package, (dict)):
          return template("message", title="Error", message="Something wrong in your config.yml about package " + packagename, redirect="/")
        gitprojectname = projectname
        if 'GitProjectName' in project:
          gitprojectname = project['GitProjectName']
        package["giturl"] = user['GitURL']+"lbs-" + gitprojectname + "/tree/master/" + packagename
        package["buildurl"] = "/triggerbuild/" + username + "/" + projectname + "/" + packagename
        package["logs"] = {}
        package["repoinstructions"] = {}
        package["srcinstructions"] = {}
        package["wininstructions"] = {}
        if not "Branches" in package:
          package["Branches"] = ["master"]
        for branchname in package["Branches"]:
          if not 'Distros' in package:
            package['Distros'] = project['Distros']
          if 'ExcludeDistros' in package:
            index=0
            while index < len(package['Distros']):
              d = package['Distros'][index]
              deleted = False
              for exclude in package['ExcludeDistros']:
                if not deleted and d.startswith(exclude):
                  del package['Distros'][index]
                  deleted = True
              if not deleted:
                index+=1
          for buildtarget in package['Distros']:
            package["logs"][buildtarget+"-"+branchname] = Logger().getBuildNumbers(username, projectname, packagename, branchname, buildtarget)
        for buildtarget in package['Distros']:
          buildHelper = BuildHelperFactory.GetBuildHelper(buildtarget.split("/")[0], None, username, projectname, packagename)
          package["repoinstructions"][buildtarget] = buildHelper.GetRepoInstructions(self.config, self.config['lbs']['DownloadUrl'], buildtarget)
          package["srcinstructions"][buildtarget] = buildHelper.GetSrcInstructions(self.config, self.config['lbs']['DownloadUrl'], buildtarget)
          package["wininstructions"][buildtarget] = buildHelper.GetWinInstructions(self.config, self.config['lbs']['DownloadUrl'], buildtarget)
        return template('package', username=username, projectname=projectname, packagename=packagename, package=package, auth_username=auth_username, logout_auth_username=self.getLogoutAuthUsername())

    def logs(self, username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildnumber):
      # for displaying the logout link
      auth_username = request.get_cookie("account", secret='some-secret-key')

      output = self.checkPermission(auth_username, username)
      if output is not None:
        return output

      content = Logger().getLog(username, projectname, packagename, branchname, lxcdistro, lxcrelease, lxcarch, buildnumber)
      return template('buildresult', buildresult=content, timeoutInSeconds=-1, username=username, projectname=projectname, packagename=packagename, branchname=branchname, buildtarget=lxcdistro + "/" + lxcrelease + "/" + lxcarch, auth_username=auth_username, logout_auth_username=self.getLogoutAuthUsername())

    def repo(self, filepath):
      return static_file(filepath, root=self.config['lbs']['ReposPath'])

    def tarball(self, filepath):
      return static_file(filepath, root=self.config['lbs']['TarballsPath'])

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
        self.LBS.ReleaseMachine(buildmachine)
      return template("message", title="machine available", message="The machine "+buildmachine+" should now be available.", redirect="/machines")

myApp=LightBuildServerWeb()
bottle.route('/login')(myApp.login)
bottle.route('/do_login', method="POST")(myApp.do_login)
bottle.route('/logout')(myApp.logout)
bottle.route('/processbuildqueue')(myApp.processbuildqueue)
bottle.route('/cancelplannedbuild/<username>/<projectname>/<packagename>/<branchname>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.cancelplannedbuild)
bottle.route('/buildproject/<username>/<projectname>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.buildproject)
bottle.route('/triggerbuild/<username>/<projectname>/<packagename>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.triggerbuild)
bottle.route('/triggerbuild/<username>/<projectname>/<packagename>/<branchname>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.triggerbuildwithbranch)
bottle.route('/triggerbuild/<username>/<projectname>/<packagename>/<lxcdistro>/<lxcrelease>/<lxcarch>/<auth_username>/<password>')(myApp.triggerbuildwithpwd)
bottle.route('/triggerbuild/<username>/<projectname>/<packagename>/<branchname>/<lxcdistro>/<lxcrelease>/<lxcarch>/<auth_username>/<password>')(myApp.triggerbuildwithbranchandpwd)
bottle.route('/triggerbuildproject/<username>/<projectname>/<lxcdistro>/<lxcrelease>/<lxcarch>/<auth_username>/<password>')(myApp.triggerbuildprojectwithpwd)
bottle.route('/livelog/<username>/<projectname>/<packagename>/<branchname>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.livelog)
bottle.route('/package/<username>/<projectname>/<packagename>')(myApp.package)
bottle.route('/project/<user>/<project>')(myApp.project)
bottle.route('/')(myApp.listProjects)
bottle.route('/projects')(myApp.listProjects)
bottle.route('/logs/<username>/<projectname>/<packagename>/<branchname>/<lxcdistro>/<lxcrelease>/<lxcarch>/<buildnumber>')(myApp.logs)
bottle.route('/repos/<filepath:path>')(myApp.repo)
bottle.route('/tarballs/<filepath:path>')(myApp.tarball)
bottle.route('/machines')(myApp.listMachines)
bottle.route('/machines/<action>/<buildmachine>')(myApp.manageBuildMachines)
bottle.route('/css/<filename>')(myApp.css)
bottle.route('/ext/<filepath:path>')(myApp.ext)
if __name__ == '__main__':
  # we need the IP address that connects to the outside world
  s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  # just need to connect to any external host to know which is the IP address of the machine that hosts LBS
  s.connect(("www.solidcharity.com", 80))
  ipaddress=s.getsockname()[0]
  bottle.run(host=ipaddress, port=80, debug=False)
else:
  app = application = bottle.default_app()
