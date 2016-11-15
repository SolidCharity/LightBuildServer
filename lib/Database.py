#!/usr/bin/env python3
"""Database: access to database"""

# Copyright (c) 2014-2016 Timotheus Pokorra

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
import MySQLdb
import Config

class Database:
  'access to database'

  def __init__(self, config):
    self.config = config
    self.newdatabase = False
    if 'SqliteFile' in self.config['lbs']:
        if not os.path.isfile(self.config['lbs']['SqliteFile']):
            self.newdatabase = True
        self.con = sqlite3.connect(
               self.config['lbs']['SqliteFile'],
               detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES,
               timeout=self.config['lbs']['WaitForDatabase'])
        self.con.row_factory = sqlite3.Row
    else:
        self.con = MySQLdb.connect(host="localhost",
               user=self.config['lbs']['MysqlUser'],
               passwd=self.config['lbs']['MysqlPassword'],
               db=self.config['lbs']['MysqlDatabase'],
               use_unicode=True, charset="utf8");
        cursor = self.execute("SHOW TABLES LIKE 'dbversion'");
        if not cursor.fetchone():
            self.newdatabase = True

  def createOrUpdate(self):
    dbversion=6

    createTablePackageStmt = """
CREATE TABLE package (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username char(100) NOT NULL,
  projectname char(100) NOT NULL,
  packagename char(100) NOT NULL,
  branchname char(100) NOT NULL,
  # current hash of the source from the source repository
  sourcehash char(100) NOT NULL)
"""
    createTablePackageDependancyStmt = """
CREATE TABLE packagedependancy (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  # referencing package table
  dependantpackage INTEGER,
  requiredpackage INTEGER)
"""
    createTablePackageBuildStatusStmt = """
CREATE TABLE packagebuildstatus (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  packageid INTEGER,
  distro char(40),
  release char(40),
  arch char(40),
  dirty INTEGER NOT NULL DEFAULT 1)
"""
    if self.newdatabase:
      createTableStmt = """
CREATE TABLE build (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  status char(20) NOT NULL,
  username char(100) NOT NULL,
  projectname char(100) NOT NULL,
  packagename char(100) NOT NULL,
  branchname char(100) NOT NULL,
  distro char(20) NOT NULL,
  release char(20) NOT NULL,
  arch char(10) NOT NULL,
  avoidlxc INTEGER NOT NULL DEFAULT 0,
  avoiddocker INTEGER NOT NULL DEFAULT 0,
  dependsOnOtherProjects TEXT NOT NULL,
  buildmachine char(100),
  started TIMESTAMP,
  finished TIMESTAMP,
  hanging INTEGER default 0,
  buildsuccess char(20),
  buildnumber INTEGER)
"""
      self.execute(createTableStmt)
      createTableStmt = """
CREATE TABLE machine (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name char(100) NOT NULL,
  status char(40) NOT NULL,
  type char(20) NOT NULL DEFAULT 'docker',
  static char(1) NOT NULL DEFAULT 'f',
  buildjob TEXT,
  queue TEXT,
  username char(100),
  projectname char(100),
  packagename char(100))
"""
      self.execute(createTableStmt)
      createTableStmt = """
CREATE TABLE log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  buildid INTEGER,
  line TEXT,
  created TIMESTAMP DEFAULT (datetime('now','localtime')))
"""
      self.execute(createTableStmt)
      self.execute(createTablePackageStmt)
      self.execute(createTablePackageDependancyStmt)
      self.execute(createTablePackageBuildStatusStmt)
      self.execute("CREATE TABLE dbversion ( version INTEGER )")
      self.execute("INSERT INTO dbversion(version) VALUES(%d)" % (dbversion))
      self.commit()

    cursor = self.execute("SELECT version FROM dbversion")
    currentdbversion = cursor.fetchone()["version"]
    if currentdbversion != dbversion:
      if currentdbversion < 2:
        self.execute("ALTER TABLE build ADD COLUMN hanging INTEGER DEFAULT 0")
      if currentdbversion < 3:
        self.execute("ALTER TABLE machine ADD COLUMN type CHAR(20) NOT NULL DEFAULT 'docker'")
      if currentdbversion < 4:
        self.execute("ALTER TABLE build ADD COLUMN avoidlxc INTEGER NOT NULL DEFAULT 0")
        self.execute("ALTER TABLE build ADD COLUMN avoiddocker INTEGER NOT NULL DEFAULT 0")
      if currentdbversion < 5:
        self.execute("ALTER TABLE machine ADD COLUMN static char(1) NOT NULL DEFAULT 'f'")
      if currentdbversion < 6:
        self.execute(createTablePackageStmt)
        self.execute(createTablePackageDependancyStmt)
        self.execute(createTablePackageBuildStatusStmt)
      self.execute("UPDATE dbversion SET version = %d" % (dbversion))
      self.commit()

  def execute(self, stmt, values = ()):
    if 'SqliteFile' in self.config['lbs']:
      cur = self.con.cursor()
      cur.execute(stmt, values)
      return cur
    else:
      # Mysql
      cur = self.con.cursor(MySQLdb.cursors.DictCursor)
      cur.execute(
           stmt.replace('?', '%s')
                .replace('release', '`release`')
                .replace('AUTOINCREMENT', 'AUTO_INCREMENT')
                .replace("(datetime('now','localtime'))", "CURRENT_TIMESTAMP")
                .replace("AND datetime(started,'", "AND DATE_ADD(started, INTERVAL ")
                .replace("AND datetime(created,'", "AND DATE_ADD(created, INTERVAL ")
                .replace(" seconds')", " SECOND)")

           , values)
      return cur

  def commit(self):
    self.con.commit()

  def close(self):
    self.con.close()
