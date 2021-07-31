CREATE TABLE package (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username char(100) NOT NULL,
  projectname char(100) NOT NULL,
  packagename char(100) NOT NULL,
  branchname char(100) NOT NULL,
  sourcehash char(100) NOT NULL);
CREATE TABLE packagedependancy (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dependantpackage INTEGER,
  requiredpackage INTEGER);
CREATE TABLE packagebuildstatus (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  packageid INTEGER,
  distro char(40),
  release char(40),
  arch char(40),
  dirty INTEGER NOT NULL DEFAULT 1);
CREATE TABLE build (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  status char(20) NOT NULL,
  username char(100) NOT NULL,
  projectname char(100) NOT NULL,
  secret char(1),
  packagename char(100) NOT NULL,
  branchname char(100) NOT NULL,
  distro char(20) NOT NULL,
  release char(20) NOT NULL,
  arch char(10) NOT NULL,
  avoidlxc INTEGER NOT NULL DEFAULT 0,
  avoiddocker INTEGER NOT NULL DEFAULT 0,
  dependsOnOtherProjects TEXT NOT NULL,
  buildmachine char(100),
  started DATETIME DEFAULT CURRENT_TIMESTAMP,
  finished DATETIME DEFAULT CURRENT_TIMESTAMP,
  hanging INTEGER default 0,
  buildsuccess char(20),
  buildnumber INTEGER);
CREATE TABLE `machine` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` char(100) NOT NULL,
  `status` char(40) NOT NULL,
  `type` char(20) NOT NULL DEFAULT 'docker',
  `buildjob` text,
  `queue` text,
  `username` char(100) DEFAULT NULL,
  `projectname` char(100) DEFAULT NULL,
  `secret` char(1) NOT NULL DEFAULT 't',
  `packagename` char(100) DEFAULT NULL,
  `static` char(1) NOT NULL DEFAULT 'f',
  `priority` int(11) NOT NULL DEFAULT '100',
  `port` int(11) DEFAULT NULL,
  `cid` int(11) DEFAULT NULL,
  `local` char(1) DEFAULT NULL
);
CREATE TABLE `log` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `buildid` int(11) DEFAULT NULL,
  `line` text,
  `created` DATETIME DEFAULT CURRENT_TIMESTAMP
)
