from logging import Logger
from core.classes import user, admin, client, channel, reputation, settings, commands
import core.logs as logs
import core.definition as df
import core.utils as utils
import core.base as base_module
import core.classes.config as conf_module

class Loader:

    def __init__(self):

        # Load Main Modules
        self.Definition: df                     = df

        self.ConfModule: conf_module            = conf_module

        self.BaseModule: base_module            = base_module

        self.Utils: utils                       = utils

        self.LoggingModule: logs                = logs

        # Load Classes
        self.ServiceLogging: logs.ServiceLogging     = logs.ServiceLogging()

        self.Logs: Logger                       = self.ServiceLogging.get_logger()

        self.Settings: settings.Settings        = settings.Settings()

        self.Config: df.MConfig                 = self.ConfModule.Configuration().ConfigObject

        self.Base: base_module.Base             = self.BaseModule.Base(self)

        self.User: user.User                    = user.User(self)

        self.Client: client.Client              = client.Client(self)

        self.Admin: admin.Admin                 = admin.Admin(self)

        self.Channel: channel.Channel           = channel.Channel(self)

        self.Reputation: reputation.Reputation  = reputation.Reputation(self)

        self.Commands: commands.Command         = commands.Command(self)
