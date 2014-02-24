#!/usr/bin/env python3
import bottle
from bottle import route, run, template
import lxc
import socket

@route('/build/<name>')
def build(name):
          # TODO create lxc container with specified OS
          container = lxc.Container("mybuild")
          container.create("debian", 0, {"release": "wheezy", "arch": "amd64"})
          container.start()
          output = container.get_ips(timeout=10)
          # TODO prepare container, install packages that the build requires
          # TODO get the sources
          # TODO do the actual build
          # TODO on failure, show errors
          # TODO on success, create repo for download, and display success
          # TODO destroy the container
          container.stop();
          container.destroy();
          #return template('Output was {{output}}', output=output)
          return template('buildresult', buildresult=output)

@route('/list')    
def list():
  return template('list')

ipaddress=socket.gethostbyname(socket.gethostname()) 
run(host=ipaddress, port=80, debug=True) 
