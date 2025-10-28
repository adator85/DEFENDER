import argparse
import os
import sys
from pathlib import Path
from platform import python_version_tuple

parser = argparse.ArgumentParser(description="Python Installation Code")
parser.add_argument('--check-version', action='store_true', help='Check if the python version is ok!')
parser.add_argument('--install', action='store_true', help='Run the installation')
args = parser.parse_args()

PYTHON_REQUIRED_VERSION = (3, 10, 0)
PYTHON_SYSTEM_VERSION = tuple(map(int, python_version_tuple()))
ROOT_PATH = os.getcwd()
PYENV = Path(f'{ROOT_PATH}/.pyenv/bin/python')
USER_HOME_DIRECTORY = Path.home()
SYSTEMD_PATH = Path(USER_HOME_DIRECTORY).joinpath('.config', 'systemd', 'user')
PY_EXEC = 'defender.py'
SERVICE_FILE_NAME = 'defender.service'

def check_python_requirement():
    if PYTHON_SYSTEM_VERSION < PYTHON_REQUIRED_VERSION:
	    raise RuntimeError(f"Your Python Version is not meeting the requirement, System Version: {PYTHON_SYSTEM_VERSION} < Required Version {PYTHON_REQUIRED_VERSION}")

def create_service_file():

	pyenv = PYENV
	systemd_path = SYSTEMD_PATH
	py_exec = PY_EXEC
	service_file_name = SERVICE_FILE_NAME

	if not Path(systemd_path).exists():
		print("[!] Folder not available")
		sys.exit(1)

	contain = f'''[Unit]
Description=Defender IRC Service

[Service]
ExecStart={pyenv} {py_exec}
WorkingDirectory={ROOT_PATH}
SyslogIdentifier=Defender
Restart=on-failure

[Install]
WantedBy=default.target
'''
	with open(Path(systemd_path).joinpath(service_file_name), "w") as file:
		file.write(contain)
		print('Service file generated with current configuration')
		print('Running IRC Service ...')

		print(f"#"*24)
		print("Installation complete ...")
		print("If the configuration is correct, then you must see your service connected to your irc server")
		print(f"If any issue, you can see the log file for debug {ROOT_PATH}{os.sep}logs{os.sep}defender.log")
		print(f"#"*24)

def main():
	if args.check_version:
		check_python_requirement()
		sys.exit(0)

	if args.install:
		create_service_file()
		sys.exit(0)


if __name__ == "__main__":
    main()
