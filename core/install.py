import argparse
import getpass
import os
import sys
import filecmp
from dataclasses import dataclass
from subprocess import check_call, CalledProcessError, DEVNULL, check_output
from pathlib import Path
from platform import python_version_tuple

parser = argparse.ArgumentParser(description="Python Installation Code")
parser.add_argument('--check-version', action='store_true', help='Check if the python version is ok!')
parser.add_argument('--install', action='store_true', help='Run the installation')
parser.add_argument('--git-update', action='store_true', help='Update from git (main repository)')
parser.add_argument('--started-from-sysctl', action='store_true', help='Is Defender Start from systemctl?')
parser.add_argument('--debug-level', type=int, choices=[10, 20, 30, 40, 50], help='Run Defender')
args = parser.parse_args()

PYTHON_REQUIRED_VERSION = (3, 10, 0)
PYTHON_SYSTEM_VERSION = tuple(map(int, python_version_tuple()))
ROOT_PATH = os.getcwd()
PYENV = Path(ROOT_PATH).joinpath('.pyenv/bin/python') if os.name != 'nt' else Path(ROOT_PATH).joinpath('.pyenv/Scripts/python.exe')
PIPENV = Path(ROOT_PATH).joinpath('.pyenv/bin/pip') if os.name != 'nt' else Path(ROOT_PATH).joinpath('.pyenv/Scripts/pip.exe')
USER_HOME_DIRECTORY = Path.home()
SYSTEMD_PATH = Path(USER_HOME_DIRECTORY).joinpath('.config', 'systemd', 'user')
PY_EXEC = 'defender.py'
SERVICE_FILE_NAME = 'defender.service'
CURRENT_USER = getpass.getuser()

@dataclass
class Package:
	name: str
	version: str

def update_packages() -> bool:
	try:
		if sys.prefix not in PYENV.__str__():
			print("You are probably running a new installation "
				  f"or you are not using your virtual env {PYENV}")
			return False

		print(f"> Checking for dependencies versions ==> WAIT")
		check_call([PIPENV, 'install', '--upgrade', '-r', 'requirements.txt'], stdout=DEVNULL)
		print("> Dependencies versions ==> OK")

		return True
	except Exception as err:
		print("UpdatePackage Error:", err)
		return False

def run_git_update() -> None:
	try:
		_current_git_branch = check_output(
			['git', 'branch', '--show-current'],
			text=True
		).strip()

		check_call(['git', 'pull', 'origin', _current_git_branch])

		if not is_openrc():
			create_systemd_service_file()

	except CalledProcessError as cpe:
		print('CalledProcessError:', cpe, str(cpe.returncode))

def check_python_requirement():
	if PYTHON_SYSTEM_VERSION < PYTHON_REQUIRED_VERSION:
		raise RuntimeError(f"Your Python Version is not meeting the requirement, "
						   f"System Version: {PYTHON_SYSTEM_VERSION} < Required Version {PYTHON_REQUIRED_VERSION}")

def is_openrc() -> bool:

	try:
		with open('/etc/os-release') as f:
			return 'Alpine Linux' in f.read()

	except FileNotFoundError:
		return False

def create_systemd_service_file():

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
ExecStart={pyenv} {py_exec} --started-from-sysctl
WorkingDirectory={ROOT_PATH}
SyslogIdentifier=Defender
Restart=on-failure
RestartForceExitStatus=42

[Install]
WantedBy=default.target
'''

	if not Path(ROOT_PATH).joinpath('.tmp/').exists():
		Path(ROOT_PATH).joinpath('.tmp/').mkdir()

	_tmp_file = Path(ROOT_PATH).joinpath('.tmp/' + service_file_name)
	_prod_file = Path(systemd_path).joinpath(service_file_name)
	with open(_tmp_file, 'w') as f:
		f.write(contain)

	if _prod_file.exists():
		if filecmp.cmp(_tmp_file, _prod_file):
			print('No update required for the', _prod_file)
			return

	with open(_prod_file, "w") as file:
		file.write(contain)
		print('Service file generated with current configuration')
		print('Running IRC Service ...')

		print("#"*24)
		print("Installation complete ...")
		print("If the configuration is correct, then you must see your service connected to your irc server")
		print(f"If any issue, you can see the log file for debug {ROOT_PATH}{os.sep}logs{os.sep}defender.log")
		print("#"*24)

	del _tmp_file, _prod_file

def create_openrc_service_file():
	openrc_path = Path(ROOT_PATH).joinpath('defender.initd')

	contain = f'''#!/sbin/openrc-run
name="Defender IRC Service"
description="Defender IRC Bot"
command="{PYENV}"
command_args="{ROOT_PATH}/{PY_EXEC}"
command_background=true
pidfile="/run/${{RC_SVCNAME}}.pid"
command_user="{CURRENT_USER}"
directory="{ROOT_PATH}"

depend() {{
    need net
}}
'''

	with open(openrc_path, "w") as file:
		file.write(contain)

	os.chmod(openrc_path, 0o755)

	print('OpenRC init script generated: defender.initd')
	print()
	print('#' * 24)
	print("Installation complete!")
	print()
	print("Quick start (non-root):")
	print(f"  {PYENV} {PY_EXEC}")
	print()
	print("System service with OpenRC (requires root):")
	print("  sudo cp defender.initd /etc/init.d/defender")
	print("  sudo rc-update add defender default")
	print("  sudo rc-service defender start")
	print()
	print(f"Log file: {ROOT_PATH}{os.sep}logs{os.sep}defender.log")
	print('#' * 24)

def main():
	if args.check_version:
		check_python_requirement()
		sys.exit(0)

	if args.install:
		
		if is_openrc():
			create_openrc_service_file()
		else:
			create_systemd_service_file()

		sys.exit(0)
	
	if args.git_update:
		run_git_update()
		sys.exit(0)

if __name__ == "__main__":
	main()
