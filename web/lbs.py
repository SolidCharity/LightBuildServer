#!/usr/bin/env python3
import sys
from subprocess import Popen, PIPE
from io import StringIO
import bottle
import os
from bottle import route, run, template, static_file, request, response
import lxc
import socket
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib'))
from LightBuildServer import LightBuildServer

def check_login(username, password):
    return True;

@route('/login')
def login():
    return '''
        <form action="/login" method="post">
            Username: <input name="username" type="text" />
            Password: <input name="password" type="password" />
            <input value="Login" type="submit" />
        </form>
    '''

@route('/login', method='POST')
def do_login():
    username = request.forms.get('username')
    password = request.forms.get('password')
    if check_login(username, password):
        response.set_cookie("account", username, secret='some-secret-key')
        return template("<p>Welcome {{name}}! You are now logged in.</p><br/><a href='/'>Back to main page</a>", name=username)
    else:
        return "<p>Login failed.</p>"

@route('/logout')
def logout():
    username = request.get_cookie("account", secret='some-secret-key')
    if not username:
        return "You are not logged in. Access denied. <br/><a href='/login'>Login</a>"
    response.delete_cookie("account")
    return list();

@route('/buildproject/<projectname>/<lxcdistro>/<lxcrelease>/<lxcarch>')
def buildproject(projectname, lxcdistro, lxcrelease, lxcarch):
    # TODO calculate dependancies between packages inside the project, and build in correct order
    return list();

@route('/build/<projectname>/<packagename>/<lxcdistro>/<lxcrelease>/<lxcarch>')
def build(projectname, packagename, lxcdistro, lxcrelease, lxcarch):
    username = request.get_cookie("account", secret='some-secret-key')
    if not username:
        return "You are not logged in. Access denied. <br/><a href='/login'>Login</a>"

    buildmachine='mybuild01'
    lbs=LightBuildServer()
    output = lbs.buildpackage(projectname, packagename, lxcdistro, lxcrelease, lxcarch, buildmachine) 
    return template('buildresult', buildresult=output)

@route('/')
@route('/list')
def list():
  return template('list')

@route ('/repos/<filepath:path>')
def repo(filepath):
  return static_file(filepath, root='/var/www/repos')

ipaddress=socket.gethostbyname(socket.gethostname()) 
run(host=ipaddress, port=80, debug=False) 
