IMG=kinetic-photo-server

build:
	docker build -t $(IMG) .

setup.cfg: setup.cfg.template Pipfile Pipfile.lock
	cp setup.cfg.template setup.cfg
	pipenv requirements  | awk -F\; '{print $$1}' | grep = | sed 's/==/>=/g' | sed 's/^/\t/' >> setup.cfg
