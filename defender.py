import asyncio
import concurrent.futures
from core import install
#############################################
#       @Version : 6.4                      #
#       Requierements :                     #
#           Python3.10 or higher            #
#           SQLAlchemy, requests, psutil    #
#           unrealircd-rpc-py, pyyaml       #
#           uvicorn, starlette, faker       #
#           UnrealIRCD 6.2.2 or higher      #
#############################################

async def main():
    install.update_packages()
    from core.loader import Loader
    loader = Loader()
    await loader.start()
    await loader.Irc.run()

if __name__ == "__main__":
    try:
        asyncio.run(main(), debug=False)
    except KeyboardInterrupt:
        tq = concurrent.futures.thread._threads_queues.copy()
        for t, q in tq.items():
            concurrent.futures.thread._threads_queues.pop(t, None)
    except RuntimeError:
        pass
