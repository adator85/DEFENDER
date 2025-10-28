import argparse
import os
import sys
import json
from dataclasses import dataclass
from subprocess import check_call, CalledProcessError, check_output
from pathlib import Path
from platform import python_version_tuple
import traceback

parser = argparse.ArgumentParser(description="Python Installation Code")
parser.add_argument('--check-version', action='store_true', help='Check if the python version is ok!')
parser.add_argument('--install', action='store_true', help='Run the installation')
parser.add_argument('--git-update', action='store_true', help='Update from git (main repository)')
args = parser.parse_args()

PYTHON_REQUIRED_VERSION = (3, 10, 0)
PYTHON_SYSTEM_VERSION = tuple(map(int, python_version_tuple()))
ROOT_PATH = os.getcwd()
PYENV = Path(ROOT_PATH).joinpath('.pyenv/bin/python') if os.name != 'nt' else Path(ROOT_PATH).joinpath('.pyenv/Scripts/python.exe')
PIPENV = Path(f'{ROOT_PATH}/.pyenv/bin/pip') if os.name != 'nt' else Path(f'{ROOT_PATH}/.pyenv/Scripts/pip.exe')
USER_HOME_DIRECTORY = Path.home()
SYSTEMD_PATH = Path(USER_HOME_DIRECTORY).joinpath('.config', 'systemd', 'user')
PY_EXEC = 'defender.py'
SERVICE_FILE_NAME = 'defender.service'

@dataclass
class Package:
	name: str = None
	version: str = None

def __load_required_package_versions() -> list[Package]:
	"""This will create Package model with package names and required version
        """
	try:
		DB_PACKAGES: list[Package] = []		
		version_filename = Path(ROOT_PATH).joinpath('version.json')  # f'.{os.sep}version.json'
		with open(version_filename, 'r') as version_data:
			package_info:dict[str, str] = json.load(version_data)

		for name, version in package_info.items():
			if name == 'version':
				continue
			DB_PACKAGES.append(
				Package(name=name, version=version)
				)

		return DB_PACKAGES

	except FileNotFoundError as fe:
		print(f"File not found: {fe}")
	except Exception as err:
		print(f"General Error: {err}")

def update_packages() -> None:
	try:
		newVersion = False
		db_packages = __load_required_package_versions()
		print(ROOT_PATH)
		if sys.prefix not in PYENV.__str__():
			print(f"You are probably running a new installation or you are not using your virtual env {PYENV}")
			return newVersion

		print(f"> Checking for dependencies versions ==> WAIT")
		for package in db_packages:
			newVersion = False
			_required_version = package.version
			_installed_version: str = None
			output = check_output([PIPENV, 'show', package.name])
			for line in output.decode().splitlines():
				if line.startswith('Version:'):
					_installed_version = line.split(':')[1].strip()
					break

			required_version = tuple(map(int, _required_version.split('.')))
			installed_version = tuple(map(int, _installed_version.split('.')))

			if required_version > installed_version:
				print(f'> New version of {package.name} is available {installed_version} ==> {required_version}')
				newVersion = True

			if newVersion:
				check_call([PIPENV, 'install', '--upgrade', package.name])

		print(f"> Dependencies versions ==> OK")
		return newVersion

	except CalledProcessError:
		print(f"[!] Package {package.name} not installed [!]")
	except Exception as err:
		print(f"UpdatePackage Error: {err}")
		traceback.print_exc()

def run_git_update() -> None:
	check_call(['git', 'pull', 'origin', 'main'])

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
	
	if args.git_update:
		run_git_update()
		sys.exit(0)


if __name__ == "__main__":
    main()
