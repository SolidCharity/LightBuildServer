LightBuildServer
================

LightBuildServer for building rpm and deb packages, using linux containers

LightBuildServer is developed as Open Source software under the LGPL v2.1 or later.

This is still work in progress!

For more details, please see the [LightBuildServer Wiki](https://github.com/SolidCharity/LightBuildServer/wiki)!

Goals
-----
The goal is to have a light weight build server, that can be easily installed on any Linux operating system, and allows people to quickly build packages for all supported Linux distributions.

This project will be kept simple, by using linux containers (lxc) for building on various Linux distributions, and using Github (or any other git repo server) for managing the package sources.

The goal is to have a simpler version of the [OpenBuildService](http://openbuildservice.org/), which is quite complex to setup, and does not like uptodate debian package conventions, etc.

Not the goal
------------
The goal is not to create a replacement for the [openSUSE Build Service](https://build.opensuse.org/): This project aims towards people compiling their own packages on their own instance of the LightBuildServer.

Implementation
--------------

The web interface and the server itself are being implemented in Python3. The main reason for this is that LXC has some Python3 bindings...

The server will use a MySQL database for the storage of users and projects, and build queues.

The generated packages are delivered from the server directly, via apt or yum repositories.

We are using LXC to build the packages. We are mounting network shares to reduce the amount of downloading required packages.
