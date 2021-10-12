#!/usr/bin/env python3
"""Config: load configuration parameters"""

# Copyright (c) 2014-2021 Timotheus Pokorra

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

import os
import yaml

def LoadConfig():
  'load configuration parameters'
  currentpath=os.path.abspath(os.path.dirname(__file__))
  configfile=os.path.join(currentpath, "../config.yml")
  if not os.path.isfile(configfile):
    configfile=os.path.join(currentpath, "../../etc/config.yml")
  if not os.path.isfile(configfile):
    configfile="/etc/lightbuildserver/config.yml"
  stream = open(configfile, 'r')
  return yaml.safe_load(stream)
