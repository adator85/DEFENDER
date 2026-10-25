OS := $(shell uname -s)
CURRENT_USER := $(shell whoami)
PYTHON_VERSION := $(shell python3 -V)
HOME_DIR := $(shell echo $$HOME)
SHELL := $(shell echo $$0)
DISTRO := $(shell if [ -f /etc/os-release ]; then . /etc/os-release && echo $$NAME; else echo "Unknown Linux"; fi)

install:
ifeq ($(wildcard config/configuration.yaml),)
	$(error You must provide the Configuration file: config/configuration.yaml)
endif

ifeq ($(OS), Linux)
	$(info Operating System: $(OS))
	$(info Distribution: $(DISTRO))
	$(info Python version: $(PYTHON_VERSION))
	$(info Home directory: $(HOME_DIR))
	$(info Shell type: $(SHELL))

	@python3 core/install.py --check-version
	@if [ $$? -eq 0 ]; then \
		echo "Python Version OK! Well done :)"; \
	else \
		echo "Error: Script failed with exit code $$?"; \
		exit 1; \
	fi

	$(info Creating Python Virtual Environment...)
	python3 -m venv .pyenv
	@. .pyenv/bin/activate && \
		python -m pip install --upgrade pip && \
		pip cache purge && \
		pip install -r requirements.txt

ifeq ($(DISTRO), Alpine Linux)
	@. .pyenv/bin/activate && python core/install.py --install
	$(info )
	$(info ============================================)
	$(info Installation complete!)
	$(info To start Defender manually:)
	$(info   .pyenv/bin/python defender.py)
	$(info )
	$(info For autostart with OpenRC (as root):)
	$(info   sudo cp defender.initd /etc/init.d/defender)
	$(info   sudo rc-update add defender default)
	$(info   sudo rc-service defender start)
	$(info ============================================)
else
	$(info Creating the systemd user folder...)
	mkdir -p $(HOME_DIR)/.config/systemd/user
	@. .pyenv/bin/activate && python core/install.py --install
	loginctl enable-linger $(CURRENT_USER)
	@sleep 2
	systemctl --user daemon-reload
	systemctl --user start defender
endif

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
