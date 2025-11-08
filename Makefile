OS := $(shell uname -s)
CURRENT_USER := $(shell whoami)
PYTHON_VERSION := $(shell python3 -V)
HOME_DIR := $(shell echo $$HOME)
SHELL := /bin/bash

install:
ifeq ($(wildcard config/configuration.yaml),)
	$(error You must provide the Configuration file: config/configuration.yaml)
endif

ifeq ($(OS), Linux)
	$(info Installation for os : $(OS))
	$(info Python version: $(PYTHON_VERSION))
	$(info Home directory: $(HOME_DIR))

	@python3 core/install.py --check-version
	@if [ $$? -eq 0 ]; then \
		echo "Python Version OK! Well done :)"; \
	else \
		echo "Error: Script failed with exit code $$?"; \
		exit 1; \
	fi

	$(info Creating the systemd user folder...)
	mkdir -p $(HOME_DIR)/.config/systemd/user

	$(info Creating Python Virtual Environment...)
	python3 -m venv .pyenv
	@. .pyenv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip cache purge && \
		pip install -r requirements.txt

	@. .pyenv/bin/activate && python core/install.py --install
	loginctl enable-linger $(CURRENT_USER)
	@sleep 2
	@export echo $DBUS_SESSION_BUS_ADDRESS && \
		systemctl --user daemon-reload && \
		systemctl --user start defender

endif

clean:
ifeq ($(OS), Linux)
	@export echo $DBUS_SESSION_BUS_ADDRESS && \
		systemctl --user stop defender
	$(info Defender has been stopped...)
	@if [ -e .pyenv ]; then \
		rm -rf .pyenv; \
		echo "Virtual Env has been removed!"; \
	fi
	@if [ -e $(HOME_DIR)/.config/systemd/user/defender.service ]; then \
		rm $(HOME_DIR)/.config/systemd/user/defender.service; \
		echo "Systemd file has been removed!"; \
	fi
	@export echo $DBUS_SESSION_BUS_ADDRESS && systemctl --user daemon-reload && echo "Systemd Daemon reloaded!"
endif

update:
ifeq ($(OS), Linux)
	$(info Starting update from the main repository...)
	@. .pyenv/bin/activate && python core/install.py --git-update
	$(info Update done!)
endif
