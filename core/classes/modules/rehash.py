import asyncio
import importlib
import sys
import threading
from typing import TYPE_CHECKING
import core.module as module_mod
from core.classes.modules import user, admin, channel, reputation, sasl
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
    # unload modules.
    for module in uplink.ModuleUtils.model_get_loaded_modules().copy():
        await uplink.ModuleUtils.unload_one_module(module.module_name)

    uplink.Base.garbage_collector_thread()

    uplink.Logs.debug(f'[{uplink.Config.SERVICE_NICKNAME} RESTART]: Reloading configuration!')
    await uplink.Irc.Protocol.send_squit(server_id=uplink.Config.SERVEUR_ID, server_link=uplink.Config.SERVEUR_LINK, reason=reason)
    uplink.Logs.debug('Restarting Defender ...')

    for mod in REHASH_MODULES:
        importlib.reload(sys.modules[mod])

    # Reload configuration
    uplink.Config = uplink.ConfModule.Configuration(uplink).configuration_model
    uplink.Base = uplink.BaseModule.Base(uplink)

    uplink.ModuleUtils.model_clear()          # Clear loaded modules.
    uplink.User.UID_DB.clear()                # Clear User Object
    uplink.Channel.UID_CHANNEL_DB.clear()     # Clear Channel Object
    uplink.Irc.Protocol.Handler.DB_IRCDCOMMS.clear()

    # Reload Service modules
    for module in uplink.ModuleUtils.model_get_loaded_modules().copy():
        await uplink.ModuleUtils.reload_one_module(module.module_name, uplink.Settings.current_admin)

    print(f"############ NUMBER OF IO THREADS: {len(uplink.Base.running_iothreads)}")
    print(f"############ NUMBER OF IO TASKS: {len(uplink.Base.running_iotasks)}")
    print(f"############ NUMBER OF THREADS: {len(uplink.Base.running_threads)}")
    await uplink.Irc.run()
    uplink.Config.DEFENDER_RESTART = 0


async def rehash_service(uplink: 'Loader', nickname: str) -> None:
    need_a_restart = ["SERVEUR_ID"]
    uplink.Settings.set_cache('commands', uplink.Commands.DB_COMMANDS)
    uplink.Settings.set_cache('users', uplink.User.UID_DB)
    uplink.Settings.set_cache('admins', uplink.Admin.UID_ADMIN_DB)
    uplink.Settings.set_cache('reputations', uplink.Reputation.UID_REPUTATION_DB)
    uplink.Settings.set_cache('channels', uplink.Channel.UID_CHANNEL_DB)
    uplink.Settings.set_cache('sasl', uplink.Sasl.DB_SASL)
    uplink.Settings.set_cache('modules', uplink.ModuleUtils.DB_MODULES)
    uplink.Settings.set_cache('module_headers', uplink.ModuleUtils.DB_MODULE_HEADERS)

    _was_rpc_connected = uplink.RpcServer.live
    if _was_rpc_connected:
        await uplink.RpcServer.stop_rpc_server()

    restart_flag = False
    config_model_bakcup = uplink.Config
    mods = REHASH_MODULES
    _count_reloaded_modules = len(mods)
    for mod in mods:
        importlib.reload(sys.modules[mod])

    uplink.Utils = sys.modules['core.utils']
    uplink.Config = uplink.ConfModule.Configuration(uplink).configuration_model
    uplink.Config.HSID = config_model_bakcup.HSID
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
            msg='You need to restart defender !')

    # Reload Main Commands Module
    uplink.Commands = uplink.CommandModule.Command(uplink)
    uplink.Commands.DB_COMMANDS = uplink.Settings.get_cache('commands')
    uplink.Base = uplink.BaseModule.Base(uplink)

    uplink.User = user.User(uplink)
    uplink.Admin = admin.Admin(uplink)
    uplink.Channel = channel.Channel(uplink)
    uplink.Reputation = reputation.Reputation(uplink)
    uplink.ModuleUtils = module_mod.Module(uplink)
    uplink.Sasl = sasl.Sasl(uplink)

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
        uplink.Base.create_asynctask(uplink.RpcServer.start_rpc_server())

    # Reload Service modules
    for module in uplink.ModuleUtils.model_get_loaded_modules().copy():
        await uplink.ModuleUtils.reload_one_module(module.module_name, nickname)

    color_green = uplink.Config.COLORS.green
    color_reset = uplink.Config.COLORS.nogc

    await uplink.Irc.Protocol.send_priv_msg(
        uplink.Config.SERVICE_NICKNAME,
        tr("[ %sREHASH INFO%s ] Rehash completed! %s modules reloaded.", color_green, color_reset, _count_reloaded_modules),
        uplink.Config.SERVICE_CHANLOG
    )

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

        uplink.Logs.debug(f"=======> Closing all Threads!")
        for thread in uplink.Base.running_threads:
            if thread.name == 'heartbeat' and thread.is_alive():
                uplink.Base.execute_periodic_action()
                uplink.Logs.debug(f"> Running the last periodic action")
            uplink.Logs.debug(f"> Cancelling {thread.name} {thread.native_id}")

        uplink.Base.stop_all_io_threads()
        await uplink.Base.stop_all_tasks()

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