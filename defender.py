import asyncio
import concurrent.futures
import sys
import argparse
from core import install

#############################################
#       @Version : 6.5                      #
#       Requierements :                     #
#           Python3.10 or higher            #
#           SQLAlchemy, requests, psutil    #
#           unrealircd-rpc-py, pyyaml       #
#           uvicorn, starlette, faker       #
#           UnrealIRCD 6.2.2 or higher      #
#############################################

async def main() -> int:

    parser = argparse.ArgumentParser(description="Python Starting Code")
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument('--start', action='store_true', help='Start Defender')
    action_group.add_argument('--install', action='store_true', help='Install defender application')
    action_group.add_argument('--uninstall', action='store_true', help='Install defender application')
    action_group.add_argument('--update', action='store_true', help='Update defender application')
    action_group.add_argument('--check-python-version', action='store_true', help='Check python version')
    action_group.add_argument('--version', action='store_true', help='Check python version')

    start_group = parser.add_mutually_exclusive_group()
    start_group.add_argument('--with-sysctl', action='store_true', help='Start Defender from systemctl')
    start_group.add_argument('--with-main-file', action='store_true', help='Start Defender from Defender.py')
    parser.add_argument('--debug-level', type=int, choices=[10, 20, 30, 40, 50], help='Set the debug level of Defender')

    args = parser.parse_args()

    if args.start and not (args.with_sysctl or args.with_main_file):
        parser.error('--start require at least on of the 2 following arguments [--with-sysctl] or [--with-main-file] to start')
        return 1

    if args.start:
        if not install.is_installed():
            parser.error('Defender not installed, please run python3 defender.py --install')
            return 1
        from core.loader import Loader
        loader = Loader()
        if args.debug_level:
            loader.ServiceLogging.set_file_handler_level(args.debug_level)
            loader.ServiceLogging.set_stdout_handler_level(args.debug_level)

        if args.with_sysctl:
            loader.Config.DEFENDER_STARTED_FROM_SYSTEMCTL = args.with_sysctl
            await loader.start()
            await loader.Irc.run()

        elif args.with_main_file:
            await loader.start()
            await loader.Irc.run()

        return loader.Config.DEFENDER_EXIT_STATUS

    elif args.install:
        install.install()

    elif args.uninstall:
        install.uninstall()

    elif args.update:
        install.update()

    elif args.check_python_version:
        install.check_python_version_requirement()

    elif args.version:
        print(install.version())

    return 0

if __name__ == "__main__":
    try:
        defender_exit_status = asyncio.run(main(), debug=False)
        sys.exit(defender_exit_status)

    except KeyboardInterrupt:
        tq = dict(concurrent.futures.thread._threads_queues).copy()
        for t, q in tq.items():
            concurrent.futures.thread._threads_queues.pop(t, None)

    except RuntimeError:
        pass
