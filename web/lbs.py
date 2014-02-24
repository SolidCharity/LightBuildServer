#!/usr/bin/env python3
import sys
from subprocess import Popen, PIPE
from io import StringIO
import bottle
from bottle import route, run, template, static_file, request, response
import lxc
import socket

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

@route('/build/<packagename>/<lxcdistro>/<lxcrelease>/<lxcarch>')
def build(packagename, lxcdistro, lxcrelease, lxcarch):
    username = request.get_cookie("account", secret='some-secret-key')
    if not username:
        return "You are not logged in. Access denied. <br/><a href='/login'>Login</a>"

    # TODO pick up details from database, and POST parameters 
    buildmachine='mybuild01'
    lbsproject='https://github.com/tpokorra/lbs-lxc'
    # TODO should have subdirectories for the packages: lxc, lbs, etc
    # lbsproject='https://github.com/tpokorra/lbs-mono'
    #   should have subdirectories for packages: mono-opt, monodevelop-opt, etc

    container = lxc.Container(buildmachine)
    output = ''
    # create lxc container with specified OS
    #if container.create(lxcdistro, 0, {"release": lxcrelease, "arch": lxcarch}):
    child = Popen(["lxc-create", "-t", "download", "--name", buildmachine,
	"--", "-d", lxcdistro, "-r", lxcrelease, "-a", lxcarch], stdout=PIPE, stderr=PIPE)
    while True:
      out = child.stdout.read(1).decode("utf-8")
      if (out == '') and child.poll() != None:
        break
      if (out != ''):
        sys.stdout.write(out)
        output += out
        sys.stdout.flush()
    streamdata = child.communicate();
    output += streamdata[1].decode("utf-8");
    if not child.returncode:
      # TODO for each build slot, create a cache mount, depending on the OS. /var/cache contains yum and apt caches
      #         /var/lib/lbs/cache
      # TODO for each project, create a repo mount, depending on the OS
      #         /var/lib/lbs/repos
      container.start()
      # TODO prepare container, install packages that the build requires
      # TODO get the sources
      # TODO do the actual build
      # TODO on failure, show errors
      # TODO on success, create repo for download, and display success
      # TODO destroy the container
      container.stop();
      container.destroy();
      return template('buildresult', buildresult=output)
    else:
      output += "\nThere is a problem with creating the container!"

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
