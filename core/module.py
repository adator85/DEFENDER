"""
This is the main operational file to handle modules
"""
import sys
import importlib
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Optional, cast, Type
from core.definition import DefenderModuleHeader, MModule
from core.utils import tr

if TYPE_CHECKING:
    from core.loader import Loader
    from core.classes.interfaces.imodule import IModule

class Module:

    def __init__(self, loader: 'Loader') -> None:
        self._ctx = loader
        self.DB_MODULES: list[MModule] = []

    def discover(self) -> list[str]:
        """Get list of all main modules
        using this pattern mod_*.py
        all files starting with mod_
        Returns:
            list[str]: List of all module names.
        """
        base_path = Path('mods')
        modules_available = [file.name.replace('.py', '') for file in base_path.rglob('mod_*.py')]
        self._ctx.Logs.debug("Modules available: %s", modules_available)
        return modules_available

    async def _import_module(self, module_folder: str, module_name: str, class_name: str) -> 'IModule':

        _module_path = f'mods.{module_folder}.{module_name}'
        loaded_module = importlib.import_module(_module_path)
        my_class = getattr(loaded_module, class_name, None)
        if my_class is None:
            raise AttributeError(f'This class was not found: {class_name}')

        my_class = cast(Type['IModule'], my_class)
        self.is_module_compliant(my_class)

        # Créer une nouvelle instance de la classe
        _new_instance: 'IModule' = my_class(self._ctx)

        if self._ctx.Utils.is_coroutinefunction(_new_instance.load):
            await _new_instance.load()
        else:
            raise TypeError(f'The load method must be await coroutine function! {module_name}.{class_name}')

        if not _new_instance.is_loaded:
            raise AttributeError(
                f'[{class_name}] Your module is not valid make sure you have implemented required methods!')

        self._ctx.Logs.debug('[MODULE IMPORT] Module %s.%s imported into sys.modules',
                             module_folder, module_name)
        return _new_instance

    async def load_one_module(self, module_name: str, nickname: str, *,
                              is_default: bool = False,
                              load_modules_dependencies: bool = False) -> bool:

        _proto = self._ctx.Irc.Protocol
        _log = self._ctx.Logs
        _red = self._ctx.Const.Colors.red
        _nogc = self._ctx.Const.Colors.nogc
        try:
            module_folder, m_name, class_name = self.sanitize_module_information(module_name)
        except SyntaxError as se:
            _log.critical("[MODULE ERROR]: %s", se)
            return False

        async def _cleanup_module(_m_folder, _m_name):
            self.drop_module_from_sys_modules(_m_folder, _m_name)
            self.model_drop_module(_m_name)
            await self.db_delete_module(_m_name)

        try:
            if self.model_is_module_exist(m_name):
                # Module exist in sys.module
                _log.debug('[LOAD ONE MODULE] Module %s already exist!', m_name)
                await _proto.send_priv_msg(
                    nick_from=self._ctx.Config.SERVICE_NICKNAME,
                    msg=tr("Module %s already loaded!", m_name),
                    channel=self._ctx.Config.SERVICE_CHANLOG)
                return False

            # Load the module.
            # reload module dependencies
            if load_modules_dependencies:
                self.reload_all_modules_with_all_dependencies(f'mods.{module_folder}')

            create_instance_of_the_class = await self._import_module(module_folder, m_name, class_name)
            mod_header = DefenderModuleHeader(**create_instance_of_the_class.MOD_HEADER)
            mod_obj = MModule(
                m_name,
                class_name,
                create_instance_of_the_class,
                mod_header
            )

            # Create Module object
            if self.model_insert_module(mod_obj):
                # Enregistrer le module dans la base de données
                await self.db_register_module(m_name, nickname, is_default)
                await _proto.send_priv_msg(
                    nick_from=self._ctx.Config.SERVICE_NICKNAME,
                    msg=tr("Module %s loaded!", m_name),
                    channel=self._ctx.Config.SERVICE_CHANLOG)
                _log.debug("Module %s has been loaded", class_name)
                return True
            else:
                _log.debug("[LOAD ONE MODULE INFO] Module %s has not been loaded", m_name)
                await _cleanup_module(module_folder, m_name)
                return False

        except AttributeError as attr:
            await _proto.send_priv_msg(
                    nick_from=self._ctx.Config.SERVICE_NICKNAME,
                    msg=tr("[ %sMODULE ERROR%s ] Module %s is facing issues! %s",
                           _red, _nogc, m_name, attr),
                    channel=self._ctx.Config.SERVICE_CHANLOG
                )
            await _cleanup_module(module_folder, m_name)
            _log.error(msg=attr, exc_info=True)
            return False

    async def unload_one_module(self, module_name: str, keep_in_db: bool = True) -> bool:
        """Unload a module

        Args:
            module_name (str): Module name ex mod_defender
            keep_in_db (bool): Keep in database
        Returns:
            bool: True if success
        """
        # Le nom du module. exemple: mod_defender
        red = self._ctx.Const.Colors.red
        nogc = self._ctx.Const.Colors.nogc
        _proto = self._ctx.Irc.Protocol
        _log = self._ctx.Logs
        try:
            module_folder, m_name, class_name = self.sanitize_module_information(module_name)
        except SyntaxError as se:
            _log.critical("[MODULE ERROR]: %s", se)
            return False

        if not self.is_module_exist_in_sys_module(m_name):
            _log.debug("[ UNLOAD MODULE ] This module (%s) is not loaded in the sys.modules!",
                       m_name)
            return False

        try:
            module = self.model_get_module(m_name)
            if module is None:
                _log.debug("[ UNLOAD MODULE ERROR ] This module (%s) is not loaded!",
                           m_name)
                await self.db_delete_module(m_name)
                await _proto.send_priv_msg(
                        nick_from=self._ctx.Config.SERVICE_NICKNAME,
                        msg=f"[ {red}UNLOAD MODULE ERROR{nogc} ] This module {m_name} is not loaded!",
                        channel=self._ctx.Config.SERVICE_CHANLOG
                    )
                return False

            if module:
                # Drop the module from the model
                self.model_drop_module(m_name)

                # Clean the module
                await module.class_instance.unload()
                await module.class_instance.cleanup()

                # Delete from the sys.modules.
                if not self.drop_module_from_sys_modules(module_folder, m_name):
                    self._ctx.Logs.debug("Module mods.%s.%s still in the sys.modules",
                                         module_folder, m_name)

                # Supprimer le module de la base de données
                if not keep_in_db:
                    await self.db_delete_module(m_name)

                await _proto.send_priv_msg(
                        nick_from=self._ctx.Config.SERVICE_NICKNAME,
                        msg=f"[ UNLOAD MODULE INFO ] Module {m_name} has been unloaded!",
                        channel=self._ctx.Config.SERVICE_CHANLOG
                    )
                _log.debug("[ UNLOAD MODULE ] %s has been unloaded!", m_name)

                del module.class_instance
                del module
                return True

            _log.debug("[UNLOAD MODULE]: Module %s not found in DB_MODULES variable!", m_name)
            return False

        except Exception as err:
            _log.error("General Error: %s", err, exc_info=True)
            return False

    async def reload_one_module(self, module_name: str, nickname: str) -> bool:
        """Reloading one module and insert it into the model as well as the database

        Args:
            module_name (str): The module name
            nickname (str): The nickname

        Returns:
            bool: True if the module has been reloaded
        """
        _proto = self._ctx.Irc.Protocol
        _log = self._ctx.Logs
        _red = self._ctx.Const.Colors.red
        _green = self._ctx.Const.Colors.green
        _nogc = self._ctx.Const.Colors.nogc

        try:
            module_folder, m_name, class_name = self.sanitize_module_information(module_name)
        except SyntaxError as se:
            _log.critical("[MODULE ERROR]: %s", se)
            return False

        try:
            if not await self.unload_one_module(m_name):
                return False
            else:
                if await self.load_one_module(m_name, nickname, load_modules_dependencies=True):
                    await _proto.send_priv_msg(
                        nick_from=self._ctx.Config.SERVICE_NICKNAME,
                        channel=self._ctx.Config.SERVICE_CHANLOG,
                        msg=tr('[ %sMODULE RELOADED%s ] Module %s has been reloaded!',
                               _green, _nogc, m_name)
                    )
                    return True

            return False

        except (TypeError, AttributeError, KeyError, Exception) as err:
            _log.error("[RELOAD MODULE ERROR]: %s", err, exc_info=True)
            await _proto.send_priv_msg(
                        nick_from=self._ctx.Config.SERVICE_NICKNAME,
                        msg=f"[ {_red}RELOAD MODULE ERROR {_nogc}]: {err}",
                        channel=self._ctx.Config.SERVICE_CHANLOG
                    )
            self.drop_module_from_sys_modules(module_folder, m_name)
            await self.db_delete_module(m_name)
            return False

    def reload_all_modules_with_all_dependencies(self, prefix: str = 'mods') -> None:
        """
        Reload all modules in sys.modules that start with the given prefix.
        Useful for reloading a full package during development.
        """
        modules_to_reload = []
        _log = self._ctx.Logs

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
                    _log.debug(f'[LOAD_MODULE] Module {module} success')

            except Exception as err:
                _log.error(f'[LOAD_MODULE] Module {module} failed [!] - {err}')

    def load_all_modules(self) -> bool:
        raise NotImplementedError('load_all_modules')

    def reload_all_modules(self) -> bool:
        raise NotImplementedError('reload_all_modules')

    def unload_all_modules(self) -> bool:
        raise NotImplementedError('unload_all_modules')

    def is_module_exist_in_sys_module(self, module_name: str) -> bool:
        """Check if the module exist in the sys.modules
        This will check only in the folder mods/
        Args:
            module_name (str): The module name

        Returns:
            bool: True if the module exist
        """
        try:
            module_folder, m_name, class_name = self.sanitize_module_information(module_name)
        except SyntaxError as se:
            self._ctx.Logs.critical("[MODULE ERROR]: %s", se)
            return False

        if "mods." + module_folder + "." + module_name in sys.modules:
            return True

        return False

    @staticmethod
    def drop_module_from_sys_modules(module_folder: str, module_name: str) -> bool:
        """Drop module from sys.modules

        Args:
            module_folder (str): The folder of the module
            module_name (str): The name of the module

        Returns:
            bool: True if success or False
        """
        full_path = f'mods.{module_folder}.{module_name}'
        module = sys.modules.pop(full_path, None)
        parent_name, _, child_name = full_path.rpartition('.')
        parent = sys.modules.get(parent_name, None)
        if parent is not None:
            if getattr(parent, child_name, None) is module and module is not None:
                delattr(parent, child_name)

        if sys.modules.get(f'mods.{module_folder}.{module_name}'):
            return False

        return True

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
        if module_name is not None:
            for module in self.DB_MODULES:
                if module.module_name.lower() == module_name.lower():
                    self._ctx.Logs.debug(f"[MODEL MODULE GET] The module {module_name} has been found in the model DB_MODULES")
                    return module
        
            self._ctx.Logs.debug(f"[MODEL MODULE GET] The module {module_name} not found in the model DB_MODULES")

        return None

    def model_drop_module(self, module_name: str) -> bool:
        """Drop a module model object from DB_MODULES

        Args:
            module_name (str): The module name you want to drop

        Returns:
            bool: True if the model has been dropped
        """
        module = self.model_get_module(module_name)
        if module:
            self.DB_MODULES.remove(module)
            return True

        return False

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
        
        self._ctx.Logs.debug(f"[MODEL MODULE INSERT ERROR] The module {module_model.module_name} already exist in the local variable model DB_MODULES")
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
            await self.load_one_module(r[0], 'sys', is_default=True)

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
            is_default (int): Is this a default module. Default 0
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
    
    async def db_update_module(self, module_name: str, nickname: str) -> bool:
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

    async def db_delete_module(self, module_name:str) -> bool:
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

    '''
        UTILS DEDICATED TO MODULE
    '''

    def sanitize_module_information(self, module_name: str) -> tuple[str, str, str]:
        """
        Sanitize the module name, and it returns a tuple with needed information
        eg. module name must start with mod_
        it return:
            - module_folder: defender
            - module_name: mod_defender
            - class_name: Defender
        It raise SyntaxError if the module name does not start with "mod_"
        """
        # module_name : mod_defender
        if not module_name.lower().startswith('mod_'):
            self._ctx.Logs.critical("Not a valid module name: %s",
                                 module_name)
            raise SyntaxError(f'This module name ({module_name}) does not start with "mod_"')

        module_name = module_name.lower() # --> mod_defender
        module_folder = module_name.split('_')[1].lower() # --> defender
        class_name = module_name.split('_')[1].capitalize() # --> Defender

        return module_folder, module_name, class_name

    def is_module_compliant(self, obj: object) -> bool:
        """
        It check if the module is compliant.
        It raises AttributeError if the module is not compliant
        """
        class_name = obj.__name__
        attributs = {'MOD_HEADER', 'mod_config'}
        methods = {'load', 'unload', 'create_tables', 'cmd', 'hcmds', 'ModConfModel'}

        obj_attributs: set = set([attribut for attribut in dir(obj) if not callable(getattr(obj, attribut)) and not attribut.startswith('__')])
        obj_methods: set = set([method for method in dir(obj) if callable(getattr(obj, method)) and not method.startswith('__')])

        if not attributs.issubset(obj_attributs):
            self._ctx.Logs.error(f'[{class_name}] Your module is not valid make sure you have implemented required attributes {attributs}')
            raise AttributeError(f'[{class_name}] Your module is not valid make sure you have implemented required attributes {attributs}')

        if not methods.issubset(obj_methods):
            self._ctx.Logs.error(f'[{class_name}] Your module is not valid make sure you have implemented required methods {methods}')
            raise AttributeError(f'[{class_name}] Your module is not valid make sure you have implemented required methods {methods}')

        return True
