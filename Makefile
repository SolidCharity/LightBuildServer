VENV := . .venv/bin/activate &&

all:
	@echo "useful scripts for the LightBuildServer"
	@echo
	@echo "to prepare a development environment: make quickstart"
	@echo "to start the server: make runserver"
	@echo

quickstart_debian: debian_packages quickstart

debian_packages:
	sudo apt update
	sudo apt install python3-venv python3-dev -y

quickstart: create_venv pip_packages create_db init_config
	@echo
	@echo =====================================================================================
	@echo Installation has finished successfully
	@echo Run '"'make runserver'"' in order to start the server and access it through one of the following IP addresses
	@ip addr | sed 's/\/[0-9]*//' | awk '/inet / {print "http://" $$2 ":8000/"}'
	@echo Admin user is '"'admin'"' password is '"'admin'"'

create_venv:
	python3 -m venv .venv

pip_packages:
	${VENV} pip install -r requirements.txt

create_db:
	${VENV} python manage.py migrate
	${VENV} echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(is_superuser=True).exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin')" | python manage.py shell

initdemo:
	${VENV} python manage.py initdemo

init_config:
	mkdir -p var/repos var/tarballs var/logs var/src var/container

runserver:
	${VENV} python manage.py runserver

cronjob:
	${VENV} python manage.py cronjob

