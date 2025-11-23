import asyncio
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
    asyncio.run(main(), debug=False)
