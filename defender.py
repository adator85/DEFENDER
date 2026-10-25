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
    install.update_packages()
    from core.loader import Loader
    loader = Loader()

    parser = argparse.ArgumentParser(description="Python Starting Code")
    parser.add_argument('--debug-level', type=int, choices=[10, 20, 30, 40, 50], help='Run Defender')
    parser.add_argument('--started-from-sysctl', action='store_true', help='Is Defender Start from systemctl?')
    args = parser.parse_args()

    if args.debug_level:
        loader.ServiceLogging.set_file_handler_level(args.debug_level)
        loader.ServiceLogging.set_stdout_handler_level(args.debug_level)

    if args.started_from_sysctl:
        loader.Config.DEFENDER_STARTED_FROM_SYSTEMCTL = args.started_from_sysctl

    await loader.start()
    await loader.Irc.run()

    return loader.Config.DEFENDER_EXIT_STATUS

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
