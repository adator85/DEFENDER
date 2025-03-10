from core import installation

#############################################
#       @Version : 6                        #
#       Requierements :                     #
#           Python3.10 or higher            #
#           SQLAlchemy, requests, psutil    #
#           UnrealIRCD 6.2.2 or higher      #
#############################################

try:

    installation.Install()

    from core.loader import Loader
    from core.irc import Irc
    # loader = Loader()
    ircInstance = Irc(Loader())
    ircInstance.init_irc(ircInstance)

except AssertionError as ae:
    print(f'Assertion Error -> {ae}')
except KeyboardInterrupt as k:
    ircInstance.Base.execute_periodic_action()