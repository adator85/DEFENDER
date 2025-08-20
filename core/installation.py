import os
import json
from sys import exit, prefix
from dataclasses import dataclass
from subprocess import check_call, run, CalledProcessError, PIPE, check_output
from platform import python_version, python_version_tuple

class Install:

    @dataclass
    class CoreConfig:
        install_log_file: str
        unix_systemd_folder: str
        service_file_name: str
        service_cmd_executable: list
        service_cmd_daemon_reload: list
        defender_main_executable: str
        python_min_version: str
        python_current_version_tuple: tuple[str, str, str]
        python_current_version: str
        defender_install_folder: str
        venv_folder: str
        venv_cmd_installation: list
        venv_cmd_requirements: list
        venv_pip_executable: str
        venv_python_executable: str

    @dataclass
    class Package:
        name: str = None
        version: str = None

    DB_PACKAGES: list[Package] = []

    def __init__(self) -> None:

        self.set_configuration()

        if self.skip_install:
            self.install_dependencies()
            self.check_packages_version()
            return None

        self.check_packages_version()

        # Sinon tester les dependances python et les installer avec pip
        if self.do_install():

            self.install_dependencies()

            self.create_service_file()

            self.print_final_message()

        return None

    def set_configuration(self):

        self.skip_install = False
        defender_install_folder = os.getcwd()
        venv_folder = '.pyenv'
        unix_user_home_directory = os.path.expanduser("~")
        unix_systemd_folder = os.path.join(unix_user_home_directory, '.config', 'systemd', 'user')
        defender_main_executable = os.path.join(defender_install_folder, 'defender.py')

        self.config = self.CoreConfig(
                install_log_file='install.log',
                unix_systemd_folder=unix_systemd_folder,
                service_file_name='defender.service',
                service_cmd_executable=['systemctl', '--user', 'start', 'defender'],
                service_cmd_daemon_reload=['systemctl', '--user', 'daemon-reload'],
                defender_main_executable=defender_main_executable,
                python_min_version='3.10',
                python_current_version_tuple=python_version_tuple(),
                python_current_version=python_version(),
                defender_install_folder=defender_install_folder,
                venv_folder=venv_folder,
                venv_cmd_installation=['python3', '-m', 'venv', venv_folder],
                venv_cmd_requirements=['sqlalchemy','psutil','requests','faker','unrealircd_rpc_py'],
                venv_pip_executable=f'{os.path.join(defender_install_folder, venv_folder, "bin")}{os.sep}pip',
                venv_python_executable=f'{os.path.join(defender_install_folder, venv_folder, "bin")}{os.sep}python'
            )

        if not self.check_python_version():
            # If the Python version is not good then Exit
            exit("/!\\ Python version error /!\\")

        if not os.path.exists(os.path.join(self.config.defender_install_folder, 'config', 'configuration.json')):
            # If configuration file do not exist
            exit("/!\\ Configuration file (core/configuration.json) doesn't exist! please create it /!\\")

        # Exclude Windows OS from the installation
        if os.name == 'nt':
            # If windows, modify pip and python virtual environment executable
            self.config.venv_pip_executable = f'{os.path.join(defender_install_folder, venv_folder, "Scripts")}{os.sep}pip.exe'
            self.config.venv_python_executable = f'{os.path.join(defender_install_folder, venv_folder, "Scripts")}{os.sep}python.exe'
            self.skip_install = True
            return False

        if self.is_root():
            exit(f'/!\\ I highly not recommend running Defender as root /!\\')
            self.skip_install = True
            return False

    def is_root(self) -> bool:

        if os.geteuid() != 0:
            print('> User without privileges ==> OK')
            return False
        elif os.geteuid() == 0:
            print('/!\\ Do not use root to install Defender /!\\')
            exit("Do not use root to install Defender")
            return True

    def do_install(self) -> bool:

        full_service_file_path = os.path.join(self.config.unix_systemd_folder, self.config.service_file_name)

        if not os.path.exists(full_service_file_path):
            print(f'/!\\ Service file does not exist /!\\')
            return True

        # Check if virtual env exist
        if not os.path.exists(f'{os.path.join(self.config.defender_install_folder, self.config.venv_folder)}'):
            self.run_subprocess(self.config.venv_cmd_installation)
            print(f'/!\\ Virtual env does not exist run the install /!\\')
            return True

    def run_subprocess(self, command:list) -> None:

        print(f'> {command}')
        try:
            check_call(command)
            print("The command completed successfully.")
        except CalledProcessError as e:
            print(f"The command failed with the return code: {e.returncode}")
            print(f"Try to install dependencies ...")
            exit(5)

    def get_packages_version_from_json(self) -> None:
        """This will create Package model with package names and required version
        """
        try:
            
            version_filename = f'.{os.sep}version.json'
            with open(version_filename, 'r') as version_data:
                package_info:dict[str, str] = json.load(version_data)

            for name, version in package_info.items():
                if name == 'version':
                    continue

                self.DB_PACKAGES.append(
                    self.Package(name=name, version=version)
                    )

            return None
        except FileNotFoundError as fe:
            print(f"File not found: {fe}")
        except Exception as err:
            print(f"General Error: {err}")

    def check_packages_version(self) -> bool:

        try:
            newVersion = False
            self.get_packages_version_from_json()
            
            if not self.config.venv_folder in prefix:
                print(f"You are probably running a new installation or you are not using your virtual env {self.config.venv_folder}")
                return newVersion

            print(f"> Checking for dependencies versions ==> WAIT")
            for package in self.DB_PACKAGES:
                newVersion = False
                required_version = package.version
                installed_version = None

                output = check_output([self.config.venv_pip_executable, 'show', package.name])
                for line in output.decode().splitlines():
                    if line.startswith('Version:'):
                        installed_version = line.split(':')[1].strip()
                        break

                required_major, required_minor, required_patch = required_version.split('.')
                installed_major, installed_minor, installed_patch = installed_version.split('.')

                if required_major > installed_major:
                    print(f'> New version of {package.name} is available {installed_version} ==> {required_version}')
                    newVersion = True
                elif required_major == installed_major and required_minor > installed_minor:
                    print(f'> New version of {package.name} is available {installed_version} ==> {required_version}')
                    newVersion = True
                elif required_major == installed_major and required_minor == installed_minor and required_patch > installed_patch:
                    print(f'> New version of {package.name} is available {installed_version} ==> {required_version}')
                    newVersion = True

                if newVersion:
                    self.run_subprocess([self.config.venv_pip_executable, 'install', '--upgrade', package.name])

            print(f"> Dependencies versions ==> OK")
            return newVersion

        except CalledProcessError:
            print(f"/!\\ Package {package.name} not installed /!\\")
        except Exception as err:
            print(f"General Error: {err}")

    def check_python_version(self) -> bool:
        """Test si la version de python est autorisée ou non

        Returns:
            bool: True si la version de python est autorisé sinon False
        """
        # Current system version
        sys_major, sys_minor, sys_patch = self.config.python_current_version_tuple

        # min python version required
        python_required_version = self.config.python_min_version.split('.')
        min_major, min_minor = tuple((python_required_version[0], python_required_version[1]))

        if int(sys_major) < int(min_major):
            print(f"## Your python version must be greather than or equal to {self.config.python_min_version} ##")
            return False

        elif (int(sys_major) <= int(min_major)) and (int(sys_minor) < int(min_minor)):
            print(f"## Your python version must be greather than or equal to {self.config.python_min_version} ##")
            return False

        print(f"> Version of python : {self.config.python_current_version} ==> OK")

        return True

    def check_package(self, package_name) -> bool:

        try:
            # Run a command in the virtual environment's Python to check if the package is installed
            run([self.config.venv_python_executable, '-c', f'import {package_name}'], check=True, stdout=PIPE, stderr=PIPE)
            return True
        except CalledProcessError as cpe:
            print(cpe)
            return False

    def install_dependencies(self) -> None:
        """### Verifie les dépendances si elles sont installées
        - Test si les modules sont installés
        - Met a jour pip
        - Install les modules manquants
        """
        do_install = False

        # Check if virtual env exist
        if not os.path.exists(f'{os.path.join(self.config.defender_install_folder, self.config.venv_folder)}'):
            self.run_subprocess(self.config.venv_cmd_installation)
            do_install = True

        for module in self.config.venv_cmd_requirements:
            if not self.check_package(module):
                do_install = True

        if not do_install:
            return None

        print("===> Clean pip cache")
        self.run_subprocess([self.config.venv_pip_executable, 'cache', 'purge'])
        
        print("===> Check if pip is up to date")
        self.run_subprocess([self.config.venv_python_executable, '-m', 'pip', 'install', '--upgrade', 'pip'])

        if not self.check_package('greenlet'):
            self.run_subprocess([self.config.venv_pip_executable, 'install', '--only-binary', ':all:', 'greenlet'])
            print('====> Greenlet installed')

        for module in self.config.venv_cmd_requirements:
            if not self.check_package(module):
                print("### Trying to install missing python packages ###")
                self.run_subprocess([self.config.venv_pip_executable, 'install', module])
                print(f"====> Module {module} installed!")
            else:
                print(f"==> {module} already installed")

    def create_service_file(self) -> None:

        full_service_file_path = os.path.join(self.config.unix_systemd_folder, self.config.service_file_name)

        if os.path.exists(full_service_file_path):
            print(f'/!\\ Service file already exist /!\\')
            self.run_subprocess(self.config.service_cmd_executable)
            return None

        contain = f'''[Unit]
Description=Defender IRC Service

[Service]
ExecStart={self.config.venv_python_executable} {self.config.defender_main_executable}
WorkingDirectory={self.config.defender_install_folder}
SyslogIdentifier=Defender
Restart=on-failure

[Install]
WantedBy=default.target
'''
        # Check if user systemd is available (.config/systemd/user/)
        if not os.path.exists(self.config.unix_systemd_folder):
            self.run_subprocess(['mkdir', '-p', self.config.unix_systemd_folder])

            with open(full_service_file_path, 'w+') as servicefile:
                servicefile.write(contain)
                servicefile.close()
                print('Service file generated with current configuration')
                print('Running IRC Service ...')
                self.run_subprocess(self.config.service_cmd_daemon_reload)
                self.run_subprocess(self.config.service_cmd_executable)

        else:
            with open(full_service_file_path, 'w+') as servicefile:
                servicefile.write(contain)
                servicefile.close()
                print('Service file generated with current configuration')
                print('Running IRC Service ...')
                self.run_subprocess(self.config.service_cmd_daemon_reload)
                self.run_subprocess(self.config.service_cmd_executable)

    def print_final_message(self) -> None:

        print(f"#"*24)
        print("Installation complete ...")
        print("If the configuration is correct, then you must see your service connected to your irc server")
        print(f"If any issue, you can see the log file for debug {self.config.defender_install_folder}{os.sep}logs{os.sep}defender.log")
        print(f"#"*24)
        exit(1)
