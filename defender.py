import asyncio
from core import install

#############################################
#       @Version : 6.3                      #
#       Requierements :                     #
#           Python3.10 or higher            #
#           SQLAlchemy, requests, psutil    #
#           unrealircd-rpc-py, pyyaml       #
#           UnrealIRCD 6.2.2 or higher      #
#############################################

async def main():
    from core.loader import Loader
    loader = Loader()
    await loader.start()
    await loader.Irc.run()

if __name__ == "__main__":
    asyncio.run(main(), debug=True)
