from core.classes import user, admin, client, channel, reputation, settings, commands
import core.definition as df
import core.utils as utils
import core.base as base_module
import core.classes.config as conf_module

class Loader:

    def __init__(self):

        # Load Main Modules
        self.Definition: df                      = df

        self.ConfModule: conf_module             = conf_module

        self.BaseModule: base_module             = base_module

        self.Utils: utils                        = utils

        # Load Classes
        self.Settings: settings.Settings        = settings.Settings()

        self.Config: df.MConfig                 = self.ConfModule.Configuration().ConfigObject

        self.Base: base_module.Base              = self.BaseModule.Base(self)

        self.User: user.User                    = user.User(self.Base)

        self.Client: client.Client              = client.Client(self.Base)

        self.Admin: admin.Admin                 = admin.Admin(self.Base)

        self.Channel: channel.Channel           = channel.Channel(self.Base)

        self.Reputation: reputation.Reputation  = reputation.Reputation(self.Base)

        self.Commands: commands.Command         = commands.Command(self.Base)
