import getpass
import logging
import os
import sys
import filecmp
from dataclasses import dataclass
from subprocess import check_call, CalledProcessError, DEVNULL, check_output, run
from pathlib import Path
from platform import python_version_tuple

LOG_INSTALL_LEVEL = 12
PYTHON_REQUIRED_VERSION = (3, 10, 0)
PYTHON_SYSTEM_VERSION = tuple(map(int, python_version_tuple()))
ROOT_PATH = Path(os.getcwd())
USER_HOME_DIRECTORY = Path.home()

REQUIREMENT_FILE = 'requirements.txt'
PYENV_FOLDER_NAME = '.pyenv'
DATA_FOLDER_NAME = 'data'
DATABASE_FOLDER_NAME = 'db'
LOGS_FOLDER_NAME = 'logs'

DATA_FULLPATH = Path(DATA_FOLDER_NAME)
DATABASE_FULLPATH = DATA_FULLPATH.joinpath(DATABASE_FOLDER_NAME)
LOGS_FULLPATH = DATA_FULLPATH.joinpath(LOGS_FOLDER_NAME)

PYENV = ROOT_PATH.joinpath(f'{PYENV_FOLDER_NAME}/bin/python') if os.name != 'nt' else ROOT_PATH.joinpath(f'{PYENV_FOLDER_NAME}/Scripts/python.exe')
PIPENV = ROOT_PATH.joinpath(f'{PYENV_FOLDER_NAME}/bin/pip') if os.name != 'nt' else ROOT_PATH.joinpath(f'{PYENV_FOLDER_NAME}/Scripts/pip.exe')

SYSTEMD_PATH = USER_HOME_DIRECTORY.joinpath('.config', 'systemd', 'user')
PY_EXEC = 'defender.py'
SERVICE_FILE_NAME = 'defender.service'
CURRENT_USER = getpass.getuser()

@dataclass
class Package:
	name: str
	version: str

def start_log_system() -> logging.Logger:

	logging_name = 'defender-install'
	debug_level = 10

	# Create folder if not available
	logs_directory = LOGS_FULLPATH
	if not logs_directory.exists():
		logs_directory.mkdir(parents=True)

	logs_fullpath = LOGS_FULLPATH.joinpath('defender.log')

	# Init logs object
	logs = logging.getLogger(logging_name)
	logs.setLevel(debug_level)

	# Add custom levels
	logging.addLevelName(LOG_INSTALL_LEVEL, 'INSTALL')

	# Add Handlers
	file_handler = logging.FileHandler(logs_fullpath, encoding='UTF-8')
	file_handler.setLevel(debug_level)

	stdout_handler = logging.StreamHandler()
	stdout_handler.setLevel(debug_level)

	# Define log format
	formatter = logging.Formatter(
		fmt='%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(funcName)s:%(lineno)d)',
		datefmt='%Y-%m-%d %H:%M:%S'
		)

	# Apply log format
	file_handler.setFormatter(formatter)
	stdout_handler.setFormatter(formatter)

	# Add handler to logs
	logs.addHandler(file_handler)
	logs.addHandler(stdout_handler)

	logs.log(LOG_INSTALL_LEVEL, 'Starting Logging system: [%s]', logs.name)

	return logs

log = start_log_system()

def run_update_packages():
	try:
		if not PIPENV.exists():
			log.log(LOG_INSTALL_LEVEL, 'Python Virtual env has been removed. No packages updated!')
			return
		
		log.log(LOG_INSTALL_LEVEL, '> Checking for dependencies versions ==> WAIT')
		log.log(LOG_INSTALL_LEVEL, '> Upgrading local pip!')
		check_call([PIPENV, 'install', '--upgrade', 'pip'], stdout=DEVNULL)

		log.log(LOG_INSTALL_LEVEL, '> Upgrading local packages!')
		check_call([PIPENV, 'install', '--upgrade', '-r', 'requirements.txt'], stdout=DEVNULL)

		log.log(LOG_INSTALL_LEVEL, '> Dependencies versions ==> OK')

	except Exception as err:
		log.error('General Error:', err)

def run_git_update() -> None:
	try:

		_current_git_branch = check_output(
			['git', 'branch', '--show-current'],
			text=True
		).strip()

		log.log(LOG_INSTALL_LEVEL, '> Checking Defender updates using current branch %s', _current_git_branch)

		check_call(['git', 'pull', 'origin', _current_git_branch])

		if not is_openrc():
			create_systemd_service_file()

		del _current_git_branch

	except CalledProcessError as cpe:
		log.error('CalledProcessError: %s - %s', cpe, str(cpe.returncode))

def check_python_version_requirement():
	if PYTHON_SYSTEM_VERSION < PYTHON_REQUIRED_VERSION:
		raise RuntimeError("Your Python Version is not meeting the requirement, "
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

	if not systemd_path.exists():
		log.error('[!] Folder not available: %s', str(systemd_path))
		sys.exit(1)

	contain = f'''[Unit]
Description=Defender IRC Service

[Service]
ExecStart={pyenv} {py_exec} --start --with-sysctl
WorkingDirectory={ROOT_PATH}
SyslogIdentifier=Defender
Restart=on-failure
RestartForceExitStatus=42

[Install]
WantedBy=default.target
'''

	if not ROOT_PATH.joinpath('.tmp/').exists():
		ROOT_PATH.joinpath('.tmp/').mkdir()

	_tmp_file = ROOT_PATH.joinpath('.tmp/' + service_file_name)
	_prod_file = systemd_path.joinpath(service_file_name)
	with open(_tmp_file, 'w') as f:
		f.write(contain)

	if _prod_file.exists():
		if filecmp.cmp(_tmp_file, _prod_file):
			log.log(LOG_INSTALL_LEVEL, 'No update required for the %s', _prod_file)
			return

	with open(_prod_file, "w") as file:
		file.write(contain)
		log.log(LOG_INSTALL_LEVEL, 'Service file generated with current configuration')

	del _tmp_file, _prod_file

def create_openrc_service_file():
	openrc_path = Path(ROOT_PATH).joinpath('defender.initd')

	contain = f'''#!/sbin/openrc-run
name="Defender IRC Service"
description="Defender IRC Bot"
command="{PYENV}"
command_args="{ROOT_PATH}/{PY_EXEC} --start --with-sysctl"
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

	log.log(LOG_INSTALL_LEVEL, 'OpenRC init script generated: defender.initd')
	log.log(LOG_INSTALL_LEVEL, '')
	log.log(LOG_INSTALL_LEVEL, '#' * 24)
	log.log(LOG_INSTALL_LEVEL, 'Installation complete!')
	log.log(LOG_INSTALL_LEVEL, '')
	log.log(LOG_INSTALL_LEVEL, 'Quick start (non-root):')
	log.log(LOG_INSTALL_LEVEL, '  %s %s', PYENV, PY_EXEC)
	log.log(LOG_INSTALL_LEVEL, '')
	log.log(LOG_INSTALL_LEVEL, 'System service with OpenRC (requires root):')
	log.log(LOG_INSTALL_LEVEL, '  sudo cp defender.initd /etc/init.d/defender')
	log.log(LOG_INSTALL_LEVEL, '  sudo rc-update add defender default')
	log.log(LOG_INSTALL_LEVEL, '  sudo rc-service defender start')
	log.log(LOG_INSTALL_LEVEL, '')
	log.log(LOG_INSTALL_LEVEL, 'Log file: %s', LOGS_FULLPATH.joinpath('defender.log'))
	log.log(LOG_INSTALL_LEVEL, '#' * 24)

def create_required_folders():
	"""Create required folders if they don't exist
	"""
	if not DATA_FULLPATH.exists():
		DATA_FULLPATH.mkdir()
		log.log(LOG_INSTALL_LEVEL, '-> Data folder created: %s', DATA_FULLPATH.__str__())

	if not SYSTEMD_PATH.exists():
		SYSTEMD_PATH.mkdir()
		log.log(LOG_INSTALL_LEVEL, '-> Systemd folder created: %s', SYSTEMD_PATH.__str__())

	if not DATABASE_FULLPATH.exists():
		DATABASE_FULLPATH.mkdir()
		log.log(LOG_INSTALL_LEVEL, '-> Database folder created: %s', DATABASE_FULLPATH.__str__())

	if not LOGS_FULLPATH.exists():
		LOGS_FULLPATH.mkdir()
		log.log(LOG_INSTALL_LEVEL, '-> Logs folder created: %s', LOGS_FULLPATH.__str__())

def install() -> bool:
	# Check python version
	# Create python virtualenv if not exist
	# Create systemd folder
	# Create defender.service file.
	# Create logs folder if not exist
	# Create db folder if not exist.
	check_python_version_requirement()

	create_required_folders()

	log.log(LOG_INSTALL_LEVEL, 'Defender folders status:')
	log.log(LOG_INSTALL_LEVEL, '	Python Virtual Environment: %s', 'Created' if PYENV.exists() else 'Not created')
	log.log(LOG_INSTALL_LEVEL, '	Database Folder: %s', 'Created' if DATABASE_FULLPATH.exists() else 'Not created')
	log.log(LOG_INSTALL_LEVEL, '	Logs folder: %s', 'Created' if LOGS_FULLPATH.exists() else 'Not created')

	try:
		if not PYENV.exists():
			log.log(LOG_INSTALL_LEVEL, '-> Create Python virtual environment: %s', PYENV)
			check_call(['python3', '-m', 'venv', PYENV_FOLDER_NAME])
			check_call([PIPENV, 'install', '-r', 'requirements.txt'])
		else:
			if not is_packages_installed():
				log.log(LOG_INSTALL_LEVEL, '-> Virtual Environment installed but missing packages:')
				check_call([PIPENV, 'install', '-r', 'requirements.txt'])

		if is_openrc():
			create_openrc_service_file()
		else:
			create_systemd_service_file()
			check_call(['loginctl', 'enable-linger', CURRENT_USER])
			check_call(['systemctl', '--user', 'daemon-reload'])

	except CalledProcessError as cpe:
		log.error('CalledProcessError: %s (%s)', cpe, cpe.returncode)
		return False

def uninstall():

	if not is_installed():
		log.log(LOG_INSTALL_LEVEL, 'Defender is not installed!')
		return

	_response = input('Do you confirm the uninstall of the app (Y/n)? ')

	match _response.lower():
		case 'y':
			# Stop Defender Servcie.
			if is_openrc():
				try:
					check_call(['rc-service', 'defender', 'stop'])
				except CalledProcessError as cpe:
					log.log(LOG_INSTALL_LEVEL, 'rc-service Error: %s', cpe)
				try:
					check_call(['rc-update', 'del', 'defender', 'default'])
				except CalledProcessError as cpe:
					log.log(LOG_INSTALL_LEVEL, 'rc-update Error: %s', cpe)

				ROOT_PATH.joinpath('defender.initd').unlink()
			else:
				# Stop and Remove Service file and reload daemon
				check_call(['systemctl', '--user', 'stop', SERVICE_FILE_NAME])
				SYSTEMD_PATH.joinpath(SERVICE_FILE_NAME).unlink()
				check_call(['systemctl', '--user', 'daemon-reload'])

			# Remove Python Virtual Environment
			_pyenv_fqn = Path(PYENV_FOLDER_NAME)
			check_call(['rm', '-rf', _pyenv_fqn])

			_remove = input('Do you delete the data folder (Y/n)? ')
			match _remove.lower():
				case 'y':
					check_call(['rm', '-rf', DATA_FULLPATH])
				case 'n':
					log.log(LOG_INSTALL_LEVEL, 'Data Folder still available.')
				case _:
					log.warning('This option is not available!')

			log.log(LOG_INSTALL_LEVEL, 'Defender has been uninstalled successfuly!')
		case 'n':
			log.log(LOG_INSTALL_LEVEL, 'Uninstall aborted!')
		case _:
			log.warning('This option is not available!')

def update():
	if sys.prefix not in PYENV.__str__():
		log.warning('You are probably running a new installation '
		            'or you are not using your virtual env %s', PYENV)
		return

	run_git_update()
	run_update_packages()

def version() -> str:
	import json
	
	try:
		with open('version.json', 'r') as f:
			version: dict = json.loads(f.read())
			return 'Defender v' + version.get('version', '')

		return ''
	except FileNotFoundError as fe:
		log.error('❌ File [version.json] not found: %s', fe)

def is_installed() -> bool:

	installed = True

	if not PYENV.exists():
		installed = False
	else:
		installed = is_packages_installed()
	
	if not DATA_FULLPATH.exists():
		installed = False

	if not SYSTEMD_PATH.exists():
		installed = False

	if not DATABASE_FULLPATH.exists():
		installed = False

	if not LOGS_FULLPATH.exists():
		installed = False


	return installed

def is_packages_installed():
	try:
		packages: list[str] = []
		with open(REQUIREMENT_FILE, "r", encoding="utf-8") as f:
			packages = [
				line.strip()
				for line in f
				if line.strip() and not line.strip().startswith("#")
			]

		missing_packages = []

		for package in packages:
			result = run(
				[PYENV, "-m", "pip", "show", package.split("==")[0].split(">=")[0].split("<=")[0].strip()],
				capture_output=True,
				text=True)

			if result.returncode != 0:
				missing_packages.append(package)

		if not missing_packages:
			log.log(LOG_INSTALL_LEVEL, "✅ All packages installed !")

			return True
		else:
			log.log(LOG_INSTALL_LEVEL, '❌ %s missing package(s):', len(missing_packages))
			for package in missing_packages:
				log.log(LOG_INSTALL_LEVEL, '   - %s', package)

			return False

	except FileNotFoundError:
		log.error('❌ Requirement File [%s] not found.', REQUIREMENT_FILE)
		return False
