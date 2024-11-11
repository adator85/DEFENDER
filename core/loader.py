from core.classes import user, admin, channel, clone, reputation, settings
import core.definition as df
import core.base as baseModule
import core.classes.config as confModule

class Loader:

    def __init__(self):

        # Load Modules
        self.Definition: df                     = df

        self.ConfModule: confModule             = confModule

        self.BaseModule: baseModule             = baseModule

        # Load Classes
        self.Settings: settings                 = settings.Settings()

        self.Config: df.MConfig                 = self.ConfModule.Configuration().ConfigObject

        self.Base: baseModule.Base              = self.BaseModule.Base(self.Config, self.Settings)

        self.User: user.User                    = user.User(self.Base)

        self.Admin: admin.Admin                 = admin.Admin(self.Base)

        self.Channel: channel.Channel           = channel.Channel(self.Base)

        self.Clone: clone.Clone                 = clone.Clone(self.Base)

        self.Reputation: reputation.Reputation  = reputation.Reputation(self.Base)
