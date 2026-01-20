import core.logs as logs
import core.definition as df
import core.utils as utils
import core.base as base_mod
import core.module as module_mod
import core.classes.modules.commands as commands_mod
import core.classes.modules.config as conf_mod
import core.classes.modules.rpc.rpc as rpc_mod
import core.irc as irc
import core.classes.protocols.factory as factory
from logging import Logger
from core.classes.modules.settings import global_settings
from core.classes.modules import translation, user, admin, channel, reputation, settings, sasl

class Loader:

    _instance = None

    def __new__(cls, *agrs):

        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):

        # Load Main Modules
        self.Definition: df                         = df

        self.ConfModule: conf_mod                   = conf_mod

        self.BaseModule: base_mod                   = base_mod

        self.CommandModule: commands_mod            = commands_mod

        self.LoggingModule: logs                    = logs

        self.RpcServerModule: rpc_mod               = rpc_mod

        self.Utils: utils                           = utils

        # Load Classes
        self.Settings: settings.Settings            = global_settings

        self.ServiceLogging: logs.ServiceLogging    = self.LoggingModule.ServiceLogging()

        self.Logs: Logger                           = self.ServiceLogging.get_logger()

        self.Config: df.MConfig                     = self.ConfModule.Configuration(self).configuration_model

        self.Settings.global_lang                   = self.Config.LANG if self.Config.LANG else "EN"

        self.Settings.global_logger                 = self.Logs

        self.Translation: translation.Translation   = translation.Translation(self)

        self.Settings.global_translation            = self.Translation.get_translation()

        self.Base: base_mod.Base                    = self.BaseModule.Base(self)

        self.User: user.User                        = user.User(self)

        self.Settings.global_user                   = self.User

        self.Admin: admin.Admin                     = admin.Admin(self)

        self.Channel: channel.Channel               = channel.Channel(self)

        self.Reputation: reputation.Reputation      = reputation.Reputation(self)

        self.Commands: commands_mod.Command         = commands_mod.Command(self)

        self.ModuleUtils: module_mod.Module         = module_mod.Module(self)

        self.Sasl: sasl.Sasl                        = sasl.Sasl(self)

        self.Irc: irc.Irc                           = irc.Irc(self)

        self.PFactory: factory.ProtocolFactorty     = factory.ProtocolFactorty(self)

        self.RpcServer: rpc_mod.JSonRpcServer       = rpc_mod.JSonRpcServer(self)

        self.Logs.debug(self.Utils.tr("Loader %s success", __name__))
    
    async def start(self):
        await self.Base.init()
