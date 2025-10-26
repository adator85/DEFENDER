from core import installation

#############################################
#       @Version : 6.3                      #
#       Requierements :                     #
#           Python3.10 or higher            #
#           SQLAlchemy, requests, psutil    #
#           unrealircd-rpc-py, pyyaml       #
#           UnrealIRCD 6.2.2 or higher      #
#############################################

try:
    installation.Install()
    from core.loader import Loader
    loader = Loader()
    loader.Irc.init_irc()

except AssertionError as ae:
    print(f'Assertion Error -> {ae}')
except KeyboardInterrupt as k:
    # ircInstance.Base.execute_periodic_action()
    ...