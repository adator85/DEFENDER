import asyncio
import gc
import importlib
import sys
from typing import TYPE_CHECKING
# import core.module as module_mod
# from core.classes.modules import user, admin, channel, reputation, sasl
from core.utils import tr

if TYPE_CHECKING:
    from core.loader import Loader

# Modules impacted by rehashing!
REHASH_MODULES = [
    'core.definition',
    'core.utils',
    'core.base',
    'core.module',
    'core.classes.modules.config',
    'core.classes.modules.commands',
    'core.classes.modules.user',
    'core.classes.modules.admin',
    'core.classes.modules.channel',
    'core.classes.modules.reputation',
    'core.classes.modules.sasl',
    'core.classes.modules.rpc.rpc_channel',
    'core.classes.modules.rpc.rpc_command',
    'core.classes.modules.rpc.rpc_user',
    'core.classes.modules.rpc.rpc',
    'core.classes.interfaces.iprotocol',
    'core.classes.interfaces.imodule',
    'core.classes.protocols.command_handler',
    'core.classes.protocols.factory',
    'core.classes.protocols.unreal6',
    'core.classes.protocols.inspircd'
]

async def restart_service(uplink: 'Loader', reason: str = "Restarting with no reason!") -> None:
    """

    Args:
        uplink (Irc): The Irc instance
        reason (str): The reason of the restart.
    """
    _running_threads = uplink.Base.running_threads.copy()
    for dthread in _running_threads:
        if dthread.thread.name == 'heartbeat':
            dthread.event.clear()
            while dthread.thread.is_alive():
                continue
            uplink.Base.running_threads.remove(dthread)

    # unload modules.
    _db_modules = uplink.ModuleUtils.model_get_loaded_modules().copy()
    for module in _db_modules:
        await uplink.ModuleUtils.unload_one_module(module.module_name)

    uplink.Base.garbage_collector_thread()

    # Cleaning modules
    for mod in REHASH_MODULES:
        if mod in sys.modules:
            del sys.modules[mod]
        importlib.import_module(mod)

    # uplink.ModuleUtils.model_clear()          # Clear loaded modules.
    # uplink.User.UID_DB.clear()                # Clear User Object
    # uplink.Channel.UID_CHANNEL_DB.clear()     # Clear Channel Object
    # uplink.Irc.Protocol.Handler.DB_IRCDCOMMS.clear()

    del (uplink.User, uplink.Admin, uplink.Channel,
        uplink.Reputation, uplink.ModuleUtils, uplink.Sasl,
        uplink.Utils, uplink.Config, _running_threads,
        uplink.Base)
    
    # Reload configuration
    uplink.Config = uplink.ConfModule.Configuration(uplink).configuration_model
    uplink.Utils = sys.modules['core.utils']
    uplink.Base = uplink.BaseModule.Base(uplink)
    uplink.User = sys.modules['core.classes.modules.user'].User(uplink)
    uplink.Admin = sys.modules['core.classes.modules.admin'].Admin(uplink)
    uplink.Channel = sys.modules['core.classes.modules.channel'].Channel(uplink)
    uplink.Reputation = sys.modules['core.classes.modules.reputation'].Reputation(uplink)
    uplink.ModuleUtils = sys.modules['core.module'].Module(uplink)
    uplink.Sasl = sys.modules['core.classes.modules.sasl'].Sasl(uplink)

    print(f"############ NUMBER OF IO THREADS: {len(uplink.Base.running_iothreads)}")
    print(f"############ NUMBER OF IO TASKS: {len(uplink.Base.running_iotasks)}")
    print(f"############ NUMBER OF THREADS: {len(uplink.Base.running_threads)}")

    uplink.Logs.debug(f'[{uplink.Config.SERVICE_NICKNAME} RESTART]: Reloading configuration!')
    await uplink.Irc.Protocol.send_squit(server_id=uplink.Config.SERVEUR_ID, server_link=uplink.Config.SERVEUR_LINK, reason=reason)
    uplink.Logs.debug('Restarting Defender ...')

    uplink.Irc.signal = False
    if uplink.Irc.writer:
        uplink.Irc.writer.close()
        try:
            await uplink.Irc.writer.wait_closed()
        except Exception:
            pass

    gc.collect()

    if uplink.Irc.writer.is_closing():
        print("*"*56, uplink.Irc.writer, "CLOSED")
        del uplink.Irc.writer, uplink.Irc.reader

    uplink.Config.DEFENDER_RESTART = 0
    await uplink.Irc.run()

async def rehash_service(uplink: 'Loader', nickname: str) -> None:
    _colors = uplink.Const.Colors
    _protocol = uplink.Irc.Protocol
    await (_protocol
           .send_priv_msg(
               uplink.Config.SERVICE_NICKNAME,
               msg=f'[ {_colors.blue}{_colors.bold}REHASH INFO{_colors.nogc}{_colors.reset} ] The system is going to rehash!',
               channel=uplink.Config.SERVICE_CHANLOG))

    uplink.Config.DEFENDER_REHASH = 1
    need_a_restart = ["SERVEUR_ID"]
    uplink.Settings.set_cache('commands', uplink.Commands.DB_COMMANDS)
    uplink.Settings.set_cache('users', uplink.User.UID_DB)
    uplink.Settings.set_cache('admins', uplink.Admin.UID_ADMIN_DB)
    uplink.Settings.set_cache('reputations', uplink.Reputation.UID_REPUTATION_DB)
    uplink.Settings.set_cache('channels', uplink.Channel.UID_CHANNEL_DB)
    uplink.Settings.set_cache('sasl', uplink.Sasl.DB_SASL)
    uplink.Settings.set_cache('modules', uplink.ModuleUtils.DB_MODULES)
    uplink.Settings.set_cache('module_headers', uplink.ModuleUtils.DB_MODULE_HEADERS)

    # Remove heartbeat thread.
    _running_threads = uplink.Base.running_threads.copy()
    for dthread in _running_threads:
        if dthread.thread.name == 'heartbeat':
            dthread.event.clear()
            while dthread.thread.is_alive():
                continue
            uplink.Base.running_threads.remove(dthread)

    _was_rpc_connected = uplink.RpcServer.live
    if _was_rpc_connected:
        await uplink.RpcServer.stop_rpc_server()

    restart_flag = False
    config_model_bakcup = uplink.Config.copy()
    _count_reloaded_modules = len(REHASH_MODULES)

    for mod in REHASH_MODULES:
        if mod in sys.modules:
            del sys.modules[mod]
        importlib.import_module(mod)

    del uplink.Utils, uplink.Config
    uplink.Utils = sys.modules['core.utils']
    uplink.Config = uplink.ConfModule.Configuration(uplink).configuration_model
    uplink.Config.HSID = config_model_bakcup.HSID
    uplink.Config.DEFENDER_REHASH = config_model_bakcup.DEFENDER_REHASH
    uplink.Config.DEFENDER_INIT = config_model_bakcup.DEFENDER_INIT
    uplink.Config.DEFENDER_RESTART = config_model_bakcup.DEFENDER_RESTART
    uplink.Config.SSL_VERSION = config_model_bakcup.SSL_VERSION
    uplink.Config.CURRENT_VERSION = config_model_bakcup.CURRENT_VERSION
    uplink.Config.LATEST_VERSION = config_model_bakcup.LATEST_VERSION

    conf_bkp_dict: dict = config_model_bakcup.to_dict()
    config_dict: dict = uplink.Config.to_dict()

    for key, value in conf_bkp_dict.items():
        if config_dict[key] != value and key != 'COLORS':
            await uplink.Irc.Protocol.send_priv_msg(
                nick_from=uplink.Config.SERVICE_NICKNAME,
                msg=f'[{key}]: {value} ==> {config_dict[key]}', 
                channel=uplink.Config.SERVICE_CHANLOG
                )
            if key in need_a_restart:
                restart_flag = True

    if config_model_bakcup.SERVICE_NICKNAME != uplink.Config.SERVICE_NICKNAME:
        await uplink.Irc.Protocol.send_set_nick(uplink.Config.SERVICE_NICKNAME)

    if restart_flag:
        uplink.Config.SERVEUR_ID = config_model_bakcup.SERVEUR_ID
        await uplink.Irc.Protocol.send_priv_msg(
            nick_from=uplink.Config.SERVICE_NICKNAME,
            channel=uplink.Config.SERVICE_CHANLOG, 
            msg='You need to restart defender!')

    # Reload Main Commands Module
    del uplink.Commands
    uplink.Commands = uplink.CommandModule.Command(uplink)
    uplink.Commands.DB_COMMANDS = uplink.Settings.get_cache('commands')

    uplink.Base.db_close()

    del (uplink.User, uplink.Admin, uplink.Channel,
         uplink.Reputation, uplink.ModuleUtils, uplink.Sasl,
         uplink.Irc.Protocol, uplink.RpcServer, uplink.Base)

    uplink.Base = uplink.BaseModule.Base(uplink)
    uplink.User = sys.modules['core.classes.modules.user'].User(uplink)
    uplink.Admin = sys.modules['core.classes.modules.admin'].Admin(uplink)
    uplink.Channel = sys.modules['core.classes.modules.channel'].Channel(uplink)
    uplink.Reputation = sys.modules['core.classes.modules.reputation'].Reputation(uplink)
    uplink.ModuleUtils = sys.modules['core.module'].Module(uplink)
    uplink.Sasl = sys.modules['core.classes.modules.sasl'].Sasl(uplink)

    # Backup data
    uplink.User.UID_DB = uplink.Settings.get_cache('users')
    uplink.Admin.UID_ADMIN_DB = uplink.Settings.get_cache('admins')
    uplink.Channel.UID_CHANNEL_DB = uplink.Settings.get_cache('channels')
    uplink.Reputation.UID_REPUTATION_DB = uplink.Settings.get_cache('reputations')
    uplink.Sasl.DB_SASL = uplink.Settings.get_cache('sasl')
    uplink.ModuleUtils.DB_MODULE_HEADERS = uplink.Settings.get_cache('module_headers')
    uplink.ModuleUtils.DB_MODULES = uplink.Settings.get_cache('modules')

    uplink.Irc.Protocol = uplink.PFactory.get()
    uplink.Irc.Protocol.register_command()

    uplink.RpcServer = uplink.RpcServerModule.JSonRpcServer(uplink)
    if _was_rpc_connected:
        # if rpc server was running then start the RPC server
        uplink.DAsyncio.create_safe_task(uplink.RpcServer.start_rpc_server())

    # Reload Service modules
    for module in uplink.ModuleUtils.model_get_loaded_modules().copy():
        await uplink.ModuleUtils.reload_one_module(module.module_name, nickname)

    uplink.Base.create_thread(uplink.Utils.heartbeat, uplink, uplink.Irc.beat, run_once=True)

    await uplink.Irc.Protocol.send_priv_msg(
        uplink.Config.SERVICE_NICKNAME,
        tr("[ %sREHASH INFO%s ] Rehash completed! %s modules reloaded.", _colors.green, _colors.nogc, _count_reloaded_modules),
        uplink.Config.SERVICE_CHANLOG)

    del (config_dict, _was_rpc_connected, config_model_bakcup,
         conf_bkp_dict, _count_reloaded_modules, _running_threads)

    # Run the python garbage collector.
    gc.collect()

    uplink.Config.DEFENDER_REHASH = 0

    return None

async def shutdown(uplink: 'Loader') -> None:
        """Methode qui va préparer l'arrêt complêt du service
        """
        # Stop RpcServer if running
        await uplink.RpcServer.stop_rpc_server()

        # unload modules.
        uplink.Logs.debug(f"=======> Unloading all modules!")
        for module in uplink.ModuleUtils.model_get_loaded_modules().copy():
            await uplink.ModuleUtils.unload_one_module(module.module_name)

        uplink.Base.stop_all_sockets()
        await uplink.Base.stop_all_timers()
        uplink.Base.stop_all_threads()
        uplink.Base.stop_all_io_threads()
        await uplink.Base.stop_all_tasks()

        if uplink.Settings.RUNNING_ASYNC_TASKS:
            await asyncio.wait([_dtask.task for _dtask in uplink.Settings.RUNNING_ASYNC_TASKS])

        uplink.Base.running_timers.clear()
        uplink.Base.running_threads.clear()
        uplink.Base.running_iotasks.clear()
        uplink.Base.running_iothreads.clear()
        uplink.Base.running_sockets.clear()
        uplink.Base.db_close()

        return None

async def force_shutdown(uplink: 'Loader') -> None:
    await asyncio.sleep(10)
    uplink.Logs.critical("The system has been killed because something is blocking the loop")
    uplink.Logs.critical(asyncio.all_tasks())
    sys.exit('The system has been killed')
