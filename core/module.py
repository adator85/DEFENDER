'''
This is the main operational file to handle modules
'''
import sys
import importlib
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Optional
from core.definition import DefenderModuleHeader, MModule
from core.utils import tr

if TYPE_CHECKING:
    from core.loader import Loader
    from core.irc import Irc
    from core.classes.interfaces.imodule import IModule

class Module:

    DB_MODULES: list[MModule] = []
    DB_MODULE_HEADERS: list[DefenderModuleHeader] = []

    def __init__(self, loader: 'Loader') -> None:
        self._ctx = loader

    def get_all_available_modules(self) -> list[str]:
        """Get list of all main modules
        using this pattern mod_*.py
        all files starting with mod_
        Returns:
            list[str]: List of all module names.
        """
        base_path = Path('mods')
        modules_available = [file.name.replace('.py', '') for file in base_path.rglob('mod_*.py')]
        self._ctx.Logs.debug(f"Modules available: {modules_available}")
        return modules_available

    def get_module_information(self, module_name: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        # module_name : mod_defender
        if not module_name.lower().startswith('mod_'):
            return None, None, None

        module_name = module_name.lower() # --> mod_defender
        module_folder = module_name.split('_')[1].lower() # --> defender
        class_name = module_name.split('_')[1].capitalize() # --> Defender
        self._ctx.Logs.debug(f"Module information Folder: {module_folder}, Name: {module_name}, Class: {class_name}")
        return module_folder, module_name, class_name

    def get_module_header(self, module_name: str) -> Optional[DefenderModuleHeader]:

        for mod_h in self.DB_MODULE_HEADERS:
            if module_name.lower() == mod_h.name.lower():
                self._ctx.Logs.debug(f"Module Header found: {mod_h}")
                return mod_h
        
        return None

    def create_module_header(self, module_header: dict[str, str]) -> bool:
        """Create a new module header into DB_MODULE_HEADERS

        Args:
            module_header (dict[str, str]): The module header

        Returns:
            bool: True if the module header has been created.
        """
        mod_header = DefenderModuleHeader(**module_header)
        if self.get_module_header(mod_header.name) is None:
            self._ctx.Logs.debug(f"[MOD_HEADER] The module header has been created! ({mod_header.name} v{mod_header.version})")
            self.DB_MODULE_HEADERS.append(mod_header)
            return True
       
        return False

    def delete_module_header(self, module_name: str) -> bool:
        mod_header = self.get_module_header(module_name)
        if mod_header is not None:
            self._ctx.Logs.debug(f"[MOD_HEADER] The module header has been deleted ({mod_header.name} v{mod_header.version})")
            self.DB_MODULE_HEADERS.remove(mod_header)
            return True

        self._ctx.Logs.debug(f"[MOD_HEADER ERROR] Impossible to remove the module header ({module_name})")
        return False

    async def load_one_module(self, module_name: str, nickname: str, is_default: bool = False) -> bool:

        module_folder, module_name, class_name = self.get_module_information(module_name)

        if module_folder is None or module_name is None or class_name is None:
            self._ctx.Logs.error(f"There is an error with the module name! {module_folder}, {module_name}, {class_name}")
            return False
        
        if self.is_module_exist_in_sys_module(module_name):
            self._ctx.Logs.debug(f"Module [{module_folder}.{module_name}] already loaded!")
            if self.model_is_module_exist(module_name):
                # Si le module existe dans la variable globale retourne False
                self._ctx.Logs.debug(f"Module [{module_folder}.{module_name}] exist in the local variable!")
                await self._ctx.Irc.Protocol.send_priv_msg(
                    nick_from=self._ctx.Config.SERVICE_NICKNAME,
                    msg=f"Le module {module_name} est déja chargé ! si vous souhaiter le recharge tapez {self._ctx.Config.SERVICE_PREFIX}reload {module_name}",
                    channel=self._ctx.Config.SERVICE_CHANLOG
                )
                return False

            return self.reload_one_module(module_name, nickname)
        
        # Charger le module
        try:
            loaded_module = importlib.import_module(f'mods.{module_folder}.{module_name}')
            my_class = getattr(loaded_module, class_name, None)         # Récuperer le nom de classe
            create_instance_of_the_class: 'IModule' = my_class(self._ctx)       # Créer une nouvelle instance de la classe
            await create_instance_of_the_class.load() if self._ctx.Utils.is_coroutinefunction(create_instance_of_the_class.load) else create_instance_of_the_class.load()
            self.create_module_header(create_instance_of_the_class.MOD_HEADER)
        except AttributeError as attr:
            red = self._ctx.Config.COLORS.red
            nogc = self._ctx.Config.COLORS.red
            await self._ctx.Irc.Protocol.send_priv_msg(
                    nick_from=self._ctx.Config.SERVICE_NICKNAME,
                    msg=tr("[%sMODULE ERROR%s] Module %s is facing issues! %s", red, nogc, module_name, attr),
                    channel=self._ctx.Config.SERVICE_CHANLOG
                )
            self._ctx.Logs.error(msg=attr, exc_info=True)
            return False

        if not hasattr(create_instance_of_the_class, 'cmd'):
            await self._ctx.Irc.Protocol.send_priv_msg(
                    nick_from=self._ctx.Config.SERVICE_NICKNAME,
                    msg=tr("cmd method is not available in the module (%s)", module_name),
                    channel=self._ctx.Config.SERVICE_CHANLOG
                )
            self._ctx.Logs.critical(f"The Module {module_name} has not been loaded because cmd method is not available")
            await self.db_delete_module(module_name)
            return False

        # Charger la nouvelle class dans la variable globale
        if self.model_insert_module(MModule(module_name, class_name, create_instance_of_the_class)):
            # Enregistrer le module dans la base de données
            await self.db_register_module(module_name, nickname, is_default)
            await self._ctx.Irc.Protocol.send_priv_msg(
                        nick_from=self._ctx.Config.SERVICE_NICKNAME,
                        msg=tr("Module %s loaded!", module_name),
                        channel=self._ctx.Config.SERVICE_CHANLOG
                    )

            self._ctx.Logs.debug(f"Module {class_name} has been loaded")
            return True

        return False

    def load_all_modules(self) -> bool:
        ...

    async def reload_one_module(self, module_name: str, nickname: str) -> bool:
        """Reloading one module and insert it into the model as well as the database

        Args:
            uplink (Irc): The Irc service instance
            module_name (str): The module name
            nickname (str): The nickname

        Returns:
            bool: True if the module has been reloaded
        """
        module_folder, module_name, class_name = self.get_module_information(module_name)
        red = self._ctx.Config.COLORS.red
        nogc = self._ctx.Config.COLORS.nogc
        try:
            if self.is_module_exist_in_sys_module(module_name):
                module_model = self.model_get_module(module_name)
                if module_model:
                    self.delete_module_header(module_model.class_instance.MOD_HEADER['name'])
                    await module_model.class_instance.unload() if self._ctx.Utils.is_coroutinefunction(module_model.class_instance.unload) else module_model.class_instance.unload()
                else:
                    await self._ctx.Irc.Protocol.send_priv_msg(
                        nick_from=self._ctx.Config.SERVICE_NICKNAME,
                        msg=f"[ {red}RELOAD MODULE ERROR{nogc} ] Module [{module_folder}.{module_name}] hasn't been reloaded! You must use {self._ctx.Config.SERVICE_PREFIX}load {module_name}",
                        channel=self._ctx.Config.SERVICE_CHANLOG
                    )
                    self._ctx.Logs.debug(f"Module [{module_folder}.{module_name}] not found! Please use {self._ctx.Config.SERVICE_PREFIX}load {module_name}")
                    return False

                # reload module dependencies
                self.reload_all_modules_with_all_dependencies(f'mods.{module_folder}')

                the_module = sys.modules[f'mods.{module_folder}.{module_name}']
                importlib.reload(the_module)
                my_class = getattr(the_module, class_name, None)
                new_instance: 'IModule' = my_class(self._ctx)
                await new_instance.load() if self._ctx.Utils.is_coroutinefunction(new_instance.load) else new_instance.load()
                self.create_module_header(new_instance.MOD_HEADER)
                module_model.class_instance = new_instance

                # Créer le module dans la base de données
                await self.db_register_module(module_name, nickname)
                await self._ctx.Irc.Protocol.send_priv_msg(
                        nick_from=self._ctx.Config.SERVICE_NICKNAME,
                        msg=f"Module [{module_folder}.{module_name}] has been reloaded!",
                        channel=self._ctx.Config.SERVICE_CHANLOG
                    )
                self._ctx.Logs.debug(f"Module [{module_folder}.{module_name}] reloaded!")
                return True
            else:
                # Module is not loaded! Nothing to reload
                self._ctx.Logs.debug(f"[RELOAD MODULE ERROR] [{module_folder}.{module_name}] is not loaded! You must use {self._ctx.Config.SERVICE_PREFIX}load {module_name}")
                await self._ctx.Irc.Protocol.send_priv_msg(
                        nick_from=self._ctx.Config.SERVICE_NICKNAME,
                        msg=f"[ {red}RELOAD MODULE ERROR{nogc} ] Module [{module_folder}.{module_name}] is not loaded! You must use {self._ctx.Config.SERVICE_PREFIX}load {module_name}",
                        channel=self._ctx.Config.SERVICE_CHANLOG
                    )
                return False

        except (TypeError, AttributeError, KeyError, Exception) as err:
            self._ctx.Logs.error(f"[RELOAD MODULE ERROR]: {err}", exc_info=True)
            await self._ctx.Irc.Protocol.send_priv_msg(
                        nick_from=self._ctx.Config.SERVICE_NICKNAME,
                        msg=f"[RELOAD MODULE ERROR]: {err}",
                        channel=self._ctx.Config.SERVICE_CHANLOG
                    )
            await self.db_delete_module(module_name)

    def reload_all_modules(self) -> bool:
        ...

    def reload_all_modules_with_all_dependencies(self, prefix: str = 'mods') -> bool:
        """
        Reload all modules in sys.modules that start with the given prefix.
        Useful for reloading a full package during development.
        """
        modules_to_reload = []

        # Collect target modules
        for name, module in sys.modules.items():
            if (
                isinstance(module, ModuleType)
                and module is not None
                and name.startswith(prefix)
            ):
                modules_to_reload.append((name, module))

        # Sort to reload submodules before parent modules
        for name, module in sorted(modules_to_reload, key=lambda x: x[0], reverse=True):
            try:
                if 'mod_' not in name and 'schemas' not in name:
                    importlib.reload(module)
                    self._ctx.Logs.debug(f'[LOAD_MODULE] Module {module} success')

            except Exception as err:
                self._ctx.Logs.error(f'[LOAD_MODULE] Module {module} failed [!] - {err}')

    async def unload_one_module(self, module_name: str, keep_in_db: bool = True) -> bool:
        """Unload a module

        Args:
            uplink (Irc): The Irc instance
            module_name (str): Module name ex mod_defender
            keep_in_db (bool): Keep in database

        Returns:
            bool: True if success
        """
        try:
            # Le nom du module. exemple: mod_defender
            red = self._ctx.Config.COLORS.red
            nogc = self._ctx.Config.COLORS.nogc
            module_folder, module_name, class_name = self.get_module_information(module_name)
            module = self.model_get_module(module_name)
            if module is None:
                self._ctx.Logs.debug(f"[ UNLOAD MODULE ERROR ] This module {module_name} is not loaded!")
                await self.db_delete_module(module_name)
                await self._ctx.Irc.Protocol.send_priv_msg(
                        nick_from=self._ctx.Config.SERVICE_NICKNAME,
                        msg=f"[ {red}UNLOAD MODULE ERROR{nogc} ] This module {module_name} is not loaded!",
                        channel=self._ctx.Config.SERVICE_CHANLOG
                    )
                return False

            if module:
                self.delete_module_header(module.class_instance.MOD_HEADER['name'])
                await module.class_instance.unload() if self._ctx.Utils.is_coroutinefunction(module.class_instance.unload) else module.class_instance.unload()
                self.DB_MODULES.remove(module)

                # Delete from the sys.modules.
                if sys.modules.get(f'mods.{module_folder}.{module_name}'):
                    del sys.modules[f"mods.{module_folder}.{module_name}"]
                
                if sys.modules.get(f'mods.{module_folder}.{module_name}'):
                    self._ctx.Logs.debug(f"Module mods.{module_folder}.{module_name} still in the sys.modules")

                # Supprimer le module de la base de données
                if not keep_in_db:
                    await self.db_delete_module(module_name)

                await self._ctx.Irc.Protocol.send_priv_msg(
                        nick_from=self._ctx.Config.SERVICE_NICKNAME,
                        msg=f"[ UNLOAD MODULE INFO ] Module {module_name} has been unloaded!",
                        channel=self._ctx.Config.SERVICE_CHANLOG
                    )
                self._ctx.Logs.debug(f"[ UNLOAD MODULE ] {module_name} has been unloaded!")
                return True

            self._ctx.Logs.debug(f"[UNLOAD MODULE]: Module {module_name} not found in DB_MODULES variable!")
            return False

        except Exception as err:
            self._ctx.Logs.error(f"General Error: {err}", exc_info=True)
            return False

    def unload_all_modules(self) -> bool:
        ...

    def is_module_exist_in_sys_module(self, module_name: str) -> bool:
        """Check if the module exist in the sys.modules
        This will check only in the folder mods/
        Args:
            module_name (str): The module name

        Returns:
            bool: True if the module exist
        """
        module_folder, module_name, class_name = self.get_module_information(module_name)
        if "mods." + module_folder + "." + module_name in sys.modules:
            self._ctx.Logs.debug(f"[SYS MODULE] (mods.{module_folder}.{module_name}) found in sys.modules")
            return True
        self._ctx.Logs.debug(f"[SYS MODULE] (mods.{module_folder}.{module_name}) not found in sys.modules")
        return False

    '''
        ALL METHODS RELATED TO THE MModule MODEL DATACLASS
    '''
    def model_get_module(self, module_name: str) -> Optional[MModule]:
        """Get The module model object if exist otherwise it returns None

        Args:
            module_name (str): The module name you want to fetch

        Returns:
            Optional[MModule]: The Module Model Object
        """
        for module in self.DB_MODULES:
            if module.module_name.lower() == module_name.lower():
                self._ctx.Logs.debug(f"[MODEL MODULE GET] The module {module_name} has been found in the model DB_MODULES")
                return module
        
        self._ctx.Logs.debug(f"[MODEL MODULE GET] The module {module_name} not found in the model DB_MODULES")
        return None

    def model_get_loaded_modules(self) -> list[MModule]:
        """Get the instance of DB_MODULES.
        Warning: You should use a copy if you want to loop through the list!

        Returns:
            list[MModule]: A list of module model object
        """
        # self._ctx.Logs.debug(f"[MODEL MODULE LOADED MODULES] {len(self.DB_MODULES)} modules found!")
        return self.DB_MODULES

    def model_insert_module(self, module_model: MModule) -> bool:
        """Insert a new module model object

        Args:
            module_model (MModule): The module model object

        Returns:
            bool: True if the model has been inserted
        """
        module = self.model_get_module(module_model.module_name)
        if module is None:
            self.DB_MODULES.append(module_model)
            self._ctx.Logs.debug(f"[MODEL MODULE INSERT] The module {module_model.module_name} has been inserted in the local variable model DB_MODULES")
            return True
        
        self._ctx.Logs.debug(f"[MODEL MODULE INSERT] The module {module_model.module_name} already exist in the local variable model DB_MODULES")
        return False

    def model_clear(self) -> None:
        """Clear DB_MODULES list!
        """
        self.DB_MODULES.clear()
        self._ctx.Logs.debug("[MODEL MODULE CLEAR] The local variable model DB_MODULES has been cleared")
        return None

    def model_is_module_exist(self, module_name: str) -> bool:
        """Check if the module exist in the module model object

        Args:
            module_name (str): The module name

        Returns:
            bool: True if the module_name exist
        """
        if self.model_get_module(module_name):
            self._ctx.Logs.debug(f"[MODEL MODULE EXIST] The module {module_name} exist in the local model DB_MODULES!")
            return True

        self._ctx.Logs.debug(f"[MODEL MODULE EXIST] The module {module_name} is not available in the local model DB_MODULES!")
        return False

    '''
        OPERATION DEDICATED TO DATABASE MANAGEMENT
    '''

    async def db_load_all_existing_modules(self) -> bool:
        """Charge les modules qui existe déja dans la base de données

        Returns:
            None: Aucun retour requis, elle charge puis c'est tout
        """
        self._ctx.Logs.debug("[DB LOAD MODULE] Loading modules from the database!")
        result = await self._ctx.Base.db_execute_query(f"SELECT module_name FROM {self._ctx.Config.TABLE_MODULE}")
        for r in result.fetchall():
            await self.load_one_module(r[0], 'sys', True)

        return True
 
    async def db_is_module_exist(self, module_name: str) -> bool:
        """Check if the module exist in the database

        Args:
            module_name (str): The module name you want to check

        Returns:
            bool: True if the module exist in the database
        """
        query = f"SELECT id FROM {self._ctx.Config.TABLE_MODULE} WHERE module_name = :module_name"
        mes_donnes = {'module_name': module_name.lower()}
        results = await self._ctx.Base.db_execute_query(query, mes_donnes)

        if results.fetchall():
            self._ctx.Logs.debug(f"[DB MODULE EXIST] The module {module_name} exist in the database!")
            return True
        else:
            self._ctx.Logs.debug(f"[DB MODULE EXIST] The module {module_name} is not available in the database!")
            return False

    async def db_register_module(self, module_name: str, nickname: str, is_default: bool = False) -> bool:
        """Insert a new module in the database

        Args:
            module_name (str): The module name
            nickname (str): The user who loaded the module
            isdefault (int): Is this a default module. Default 0
        """
        if not await self.db_is_module_exist(module_name):
            insert_cmd_query = f"INSERT INTO {self._ctx.Config.TABLE_MODULE} (datetime, user, module_name, isdefault) VALUES (:datetime, :user, :module_name, :isdefault)"
            mes_donnees = {'datetime': self._ctx.Utils.get_sdatetime(), 'user': nickname, 'module_name': module_name.lower(), 'isdefault': is_default}
            insert = await self._ctx.Base.db_execute_query(insert_cmd_query, mes_donnees)
            if insert.rowcount > 0:
                self._ctx.Logs.debug(f"[DB REGISTER MODULE] Module {module_name} has been inserted to the database!")
                return True
            else:
                self._ctx.Logs.debug(f"[DB REGISTER MODULE] Module {module_name} not inserted to the database!")
                return False

        self._ctx.Logs.debug(f"[DB REGISTER MODULE] Module {module_name} already exist in the database! Nothing to insert!")
        return False
    
    async def db_update_module(self, module_name: str, nickname: str) -> None:
        """Update the datetime and the user that updated the module

        Args:
            module_name (str): The module name to update
            nickname (str): The nickname who updated the module
        """
        update_cmd_query = f"UPDATE {self._ctx.Config.TABLE_MODULE} SET datetime = :datetime, LOWER(user) = :user WHERE LOWER(module_name) = :module_name"
        mes_donnees = {'datetime': self._ctx.Utils.get_sdatetime(), 'user': nickname.lower(), 'module_name': module_name.lower()}
        result = await self._ctx.Base.db_execute_query(update_cmd_query, mes_donnees)
        if result.rowcount > 0:
            self._ctx.Logs.debug(f"[DB UPDATE MODULE] Module {module_name} has been updated!")
            return True
        else:
            self._ctx.Logs.debug(f"[DB UPDATE MODULE] Module {module_name} not found! Nothing to update!")
            return False

    async def db_delete_module(self, module_name:str) -> None:
        """Delete a module from the database

        Args:
            module_name (str): The module name you want to delete
        """
        insert_cmd_query = f"DELETE FROM {self._ctx.Config.TABLE_MODULE} WHERE LOWER(module_name) = :module_name"
        mes_donnees = {'module_name': module_name.lower()}
        delete = await self._ctx.Base.db_execute_query(insert_cmd_query, mes_donnees)
        if delete.rowcount > 0:
            self._ctx.Logs.debug(f"[DB MODULE DELETE] The module {module_name} has been deleted from the dabatase!")
            return True

        self._ctx.Logs.debug(f"[DB MODULE DELETE] The module {module_name} is not available in the database! Nothing to delete!")
        return False
