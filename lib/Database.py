#!/usr/bin/env python3
"""Database: access to database"""

# Copyright (c) 2014-2020 Timotheus Pokorra

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
import time
import os
from collections import OrderedDict
import sqlite3
import Config

class Database:
  'access to database'

  def __init__(self, config):
    self.config = config
    self.newdatabase = False
    if 'SqliteFile' in self.config['lbs']:
        if not os.path.isfile(self.config['lbs']['SqliteFile']):
            raise Exception('cannot find sqlite db: ' + self.config['lbs']['SqliteFile'])
        self.con = sqlite3.connect(
               self.config['lbs']['SqliteFile'],
               detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES,
               timeout=self.config['lbs']['WaitForDatabase'])
        self.con.row_factory = sqlite3.Row

  def execute(self, stmt, values = ()):
    if 'SqliteFile' in self.config['lbs']:
      cur = self.con.cursor()
      print(stmt)
      cur.execute(stmt, values)
      return cur

  def commit(self):
    self.con.commit()

  def close(self):
    self.con.close()
