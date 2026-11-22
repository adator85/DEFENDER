OS := $(shell uname -s)
CURRENT_USER := $(shell whoami)
CURRENT_GIT_BRANCH := $(shell git branch --show-current)
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

	@python3 defender.py --check-python-version
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
	@. .pyenv/bin/activate && python defender.py --install
	@echo ""
	@echo "============================================"
	@echo "Installation complete!"
	@echo "To start Defender manually:"
	@echo "  .pyenv/bin/python defender.py"
	@echo ""
	@echo "For autostart with OpenRC (as root):"
	@echo "  sudo cp defender.initd /etc/init.d/defender"
	@echo "  sudo rc-update add defender default"
	@echo "  sudo rc-service defender start"
	@echo "============================================"
else
	$(info Creating the systemd user folder...)
	mkdir -p $(HOME_DIR)/.config/systemd/user
	@. .pyenv/bin/activate && python defender.py --install
	loginctl enable-linger $(CURRENT_USER)
	@sleep 2
	systemctl --user daemon-reload
	@echo "========================================================"
	@echo "Installation complete!"
	@echo "To start Defender manually:"
	@echo "  .pyenv/bin/python defender.py --start --with-main-file"
	@echo ""
	@echo "To start defender using systemd (as normal user):"
	@echo "  systemctl --user start defender"
	@echo "========================================================"
endif

endif

clean:
ifeq ($(DISTRO), Alpine Linux)
	$(info Distribution: $(DISTRO))
	@if [ -e .pyenv ]; then \
		. .pyenv/bin/activate && python defender.py --uninstall; \
		echo "Uninstall well executed."; \
	fi
else
	$(info Distribution: $(DISTRO))
	@if [ -e .pyenv ]; then \
		. .pyenv/bin/activate && python defender.py --uninstall; \
		echo "Uninstall well executed."; \
	fi
	@export echo $DBUS_SESSION_BUS_ADDRESS && systemctl --user daemon-reload && echo "Systemd Daemon reloaded!"
endif

update:
ifeq ($(OS), Linux)
	$(info Starting update from the $(CURRENT_GIT_BRANCH) repository...)
	@. .pyenv/bin/activate && python defender.py --update
	$(info Update done!)
endif
