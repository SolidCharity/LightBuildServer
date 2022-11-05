from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from projects.models import Project, Package, Distro, Branch
from machines.models import Machine

class Command(BaseCommand):
    help = 'Initialises the database with some demo data'

    def add_machine(self, hostname, port, cid, type):
        if Machine.objects.filter(host = hostname).exists():
            print(f"machine {hostname} already exists")
        else:
            machine = Machine(
                host = hostname,
                port = port,
                type = type,
                private_key = "TODO",
                static = False,
                local = False,
                priority = 1,
                cid = cid,
                enabled = True,
                status = "AVAILABLE",
            )
            machine.save()
            print(f"created machine {hostname}")


    def create_user(self, username, email):
        if User.objects.filter(username = username).exists():
            print(f"user {username} already exists")
        else:
            user = User.objects.create_user(
                username = username,
                email = email,
                password = User.objects.make_random_password(),
            )
            print(f"created user {username}")


    def create_project(self, username, projectname, giturl, gitbranch, visible = True):
        if Project.objects.filter(user__username = username).filter(name = projectname).exists():
            print(f"project {username}::{projectname} already exists")
        else:
            project = Project(
                user = User.objects.filter(username = username).first(),
                name = projectname,
                git_url = giturl,
                git_branch = gitbranch,
                visible = visible,
            )
            project.save()
            print(f"created project {username}::{projectname}")


    def create_package(self, username, projectname, packagename, buildtargets, branches):
        project = Project.objects.filter(user__username = username).filter(name = projectname).first()
        if not project:
            raise Exception(f"cannot find project {username}::{projectname}")
        if Package.objects.filter(project = project).filter(name = packagename).exists():
            print(f"package {username}::{projectname}::{packagename} already exists")
        else:
            package = Package(
                project = Project.objects.filter(user__username = username).filter(name = projectname).first(),
                name = packagename,
            )
            package.save()
            print(f"created package {username}::{projectname}::{packagename}")
            for buildtargetname in buildtargets:
                distro = Distro(package = package, name = buildtargetname)
                distro.save()
            for branchname in branches:
                branch = Branch(package = package, name = branchname)
                branch.save()


    def handle(self, *args, **options):

        # create some build machines
        self.add_machine("build01.example.org", 2222, 5, "lxd")
        self.add_machine("build02.example.org", 2222, 8, "docker")

        # create some demo users
        self.create_user("solidcharity", "solidcharity@example.org")
        self.create_user("tpokorra", "tpokorra@example.org")
        self.create_user("basx", "basx@example.org")

        # create some projects and packages
        self.create_project("solidcharity", "openpetra", "https://github.com/solidcharity/", "master", visible=True)
        self.create_package("solidcharity", "openpetra", "manual", ("debian/bullseye/amd64",), ("master",))

        self.create_project("basx", "basxconnect", "https://github.com/basxsoftwareassociation/", "main", visible=False)

        self.create_project("tpokorra", "test", "https://github.com/tpokorra/", "master", visible=False)
        self.create_package("tpokorra", "test", "test", ("centos/9-Stream/amd64", "debian/bullseye/amd64",), ("master",))

        self.create_project("tpokorra", "lbs", "https://github.com/tpokorra/", "master", visible=True)
