LightBuildServer
================

LightBuildServer for building rpm and deb packages or run Continuous Integration scripts, using linux containers.

LightBuildServer is developed as Open Source software under the BSD 3-Clause License.

This is still work in progress!

For more details, please see the [LightBuildServer Wiki](https://github.com/SolidCharity/LightBuildServer/wiki)!

Goals
-----
The goal is to have a light weight build server, that can be easily installed on any Linux operating system, and allows people to quickly build packages for all supported Linux distributions. It also allows running scripts for Continuous Integration or Nightly Tests.

This project will be kept simple, by using linux containers (lxc) for building on various Linux distributions, and using Github (or any other git repo server) for managing the package sources.

The goal is to have a simpler version of the [OpenBuildService](http://openbuildservice.org/), which is quite complex to setup, and does not like uptodate debian package conventions, etc.

Not the goal
------------
The goal is not to create a replacement for the [openSUSE Build Service](https://build.opensuse.org/): This project aims towards people compiling their own packages or running their CI scripts on their own instance of the LightBuildServer.

Implementation
--------------

The web interface and the server itself are being implemented in Python3 and with Django.

The server uses the database backend of Django (Postgresql, Sqlilte, MySQL) for the storage of users and projects, and build queues.

The generated packages are delivered from the server directly, via apt or yum repositories.

We are using LXC/LXD/Docker to build the packages or run the CI scripts.

See in action
-------------

You can see a LightBuildServer in action at https://lbs.solidcharity.com. 

You can see:
* the logs of the public builds: https://lbs.solidcharity.com/machines/
* you can install a Debian package: https://lbs.solidcharity.com/projects/solidcharity/openpetra/package/sql2diagram/
* you can see test runs, run every night: https://lbs.solidcharity.com/projects/basx/basxconnect/package/basxconnect-test/
* you can see the test of installation routines of software, run every night: https://lbs.solidcharity.com/projects/tpokorra/hostsharing/package/civicrm-test/

For each project, there is a link at the top, directing you to the setup script and/or packaging instructions for that project.

License
-------

the LightBuildServer is published with the BSD 3-Clause License.

Setup for Development
---------------------

You can run `make quickstart` to create a Python3 virtual environment, install all required packages, and create the database.

You can run `make initdemo` for loading initial users, projects and packages for development and testing.
