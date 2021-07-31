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
	@echo Login user is '"'demo'"' password is '"'demo'"'

create_venv:
	python3 -m venv .venv

pip_packages:
	${VENV} pip install -r requirements.txt

create_db:
	cat sql/create_tables.sql | sqlite3 db.sqlite3

init_config:
	cp config-devenv.yml config.yml

runserver:
	${VENV} cd web && python3 lbs.py

