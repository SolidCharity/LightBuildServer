#!/usr/bin/env python3
import sys
import bottle
import os
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

class LightBuildServerWeb:
    def __init__(self):
        configfile="../config.yml"
        stream = open(configfile, 'r')
        self.config = yaml.load(stream)
        self.lbs = None
        self.logger = Logger()

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
        return self.list();

    def buildproject(self, projectname, lxcdistro, lxcrelease, lxcarch):
        # TODO calculate dependancies between packages inside the project, and build in correct order
        return self.list();

    def build(self, projectname, packagename, lxcdistro, lxcrelease, lxcarch):
        username = request.get_cookie("account", secret='some-secret-key')
        if not username:
            return "You are not logged in. Access denied. <br/><a href='/login'>Login</a>"

        # TODO get name of available slot
        buildmachine='mybuild01.lbs.solidcharity.com'
        staticIP='10.0.3.2'

        if not self.lbs:
          self.lbs=LightBuildServer(self.logger, username)
          thread = Thread(target = self.lbs.buildpackage, args = (projectname, packagename, lxcdistro, lxcrelease, lxcarch, buildmachine, staticIP))
          thread.start()

        if self.lbs.finished:
          output = self.lbs.logger.get()
          # TODO stop refreshing
          timeout=600000
          self.lbs = None
        else:
          output = self.lbs.logger.get(4000)
          timeout = 2

        return template('buildresult', buildresult=output, timeoutInSeconds=timeout)

    def list(self):
      # TODO support several users ???
      for user in self.config['lbs']['Users']:
        userconfig=self.config['lbs']['Users'][user]
        for project in userconfig['Projects']:
          projectconfig=userconfig['Projects'][project]
          for package in projectconfig:
            projectconfig[package]["detailurl"] = "/detail/" + user + "/" + project + "/" + package
            projectconfig[package]["buildurl"] = "/build/" + project + "/" + package
        return template('list', projects = self.config['lbs']['Users'][user]['Projects'])

    def detail(self, username, projectname, packagename):
        user=self.config['lbs']['Users'][username]
        project=user['Projects'][projectname]
        package=project[packagename]
        package["giturl"] = user['GitURL']+"lbs-" + projectname + "/tree/master/" + packagename
        package["buildurl"] = "/build/" + projectname + "/" + packagename
        package["logs"] = {}
        package["repoinstructions"] = {}
        for buildtarget in package['Distros']:
          package["logs"][buildtarget] = self.logger.getBuildNumbers(username, projectname, packagename, buildtarget)
          buildHelper = BuildHelperFactory.GetBuildHelper(buildtarget.split("/")[0], None, "", username, projectname, packagename)
          package["repoinstructions"][buildtarget] = buildHelper.GetRepoInstructions(self.config, buildtarget)
        return template('detail', username=username, projectname=projectname, packagename=packagename, package=package)

    def logs(self, username, projectname, packagename, lxcdistro, lxcrelease, lxcarch, buildnumber):
      content = self.logger.getLog(username, projectname, packagename, lxcdistro, lxcrelease, lxcarch, buildnumber)
      return template('buildresult', buildresult=content, timeoutInSeconds=4000)

    def repo(self, filepath):
      return static_file(filepath, root='/var/www/repos')

    def tarball(self, filepath):
      return static_file(filepath, root='/var/www/tarballs')

myApp=LightBuildServerWeb()
bottle.route('/login')(myApp.login)
bottle.route('/do_login', method="POST")(myApp.do_login)
bottle.route('/logout')(myApp.logout)
bottle.route('/buildproject/<projectname>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.buildproject)
bottle.route('/build/<projectname>/<packagename>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.build)
bottle.route('/detail/<username>/<projectname>/<packagename>')(myApp.detail)
bottle.route('/')(myApp.list)
bottle.route('/list')(myApp.list)
bottle.route('/logs/<username>/<projectname>/<packagename>/<lxcdistro>/<lxcrelease>/<lxcarch>/<buildnumber>')(myApp.logs)
bottle.route('/repos/<filepath:path>')(myApp.repo)
bottle.route('/tarballs/<filepath:path>')(myApp.tarball)
ipaddress=socket.gethostbyname(socket.gethostname()) 
bottle.run(host=ipaddress, port=80, debug=False) 
