#!/usr/bin/env python3
import sys
import bottle
import os
from bottle import route, run, template, static_file, request, response
import lxc
import socket
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
from LightBuildServer import LightBuildServer
from Logger import Logger
from threading import Thread

class LightBuildServerWeb:
    def __init__(self):
        self.lbs = None

    def check_login(self, username, password):
        # TODO
        return True;

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

        if not self.lbs:
          self.logger = Logger()
          self.lbs=LightBuildServer(self.logger)
          thread = Thread(target = self.lbs.buildpackage, args = (projectname, packagename, lxcdistro, lxcrelease, lxcarch, buildmachine))
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

    def test(self, projectname, packagename, lxcdistro, lxcrelease, lxcarch):
        username = request.get_cookie("account", secret='some-secret-key')
        if not username:
            return "You are not logged in. Access denied. <br/><a href='/login'>Login</a>"

        # TODO get name of available slot
        buildmachine='mybuild01.lbs.solidcharity.com'

        if not self.lbs:
          self.logger = Logger()
          self.lbs=LightBuildServer(self.logger)
          thread = Thread(target = self.lbs.runtests, args = (projectname, packagename, lxcdistro, lxcrelease, lxcarch, buildmachine))
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
      return template('list')

    def repo(self, filepath):
      return static_file(filepath, root='/var/www/repos')

myApp=LightBuildServerWeb()
bottle.route('/login')(myApp.login)
bottle.route('/do_login', method="POST")(myApp.do_login)
bottle.route('/logout')(myApp.logout)
bottle.route('/buildproject/<projectname>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.buildproject)
bottle.route('/build/<projectname>/<packagename>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.build)
bottle.route('/test/<projectname>/<packagename>/<lxcdistro>/<lxcrelease>/<lxcarch>')(myApp.test)
bottle.route('/')(myApp.list)
bottle.route('/list')(myApp.list)
bottle.route('/repos/<filepath:path>')(myApp.repo)
ipaddress=socket.gethostbyname(socket.gethostname()) 
bottle.run(host=ipaddress, port=80, debug=False) 
