import importlib
import sys
import time
from typing import TYPE_CHECKING
import socket

if TYPE_CHECKING:
    from core.loader import Loader

# Modules impacted by rehashing!
REHASH_MODULES = [
    'core.definition',
    'core.utils',
    'core.classes.modules.config',
    'core.base',
    'core.classes.modules.commands',
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
    uplink.Client.CLIENT_DB.clear()           # Clear Client object
    uplink.Irc.Protocol.Handler.DB_IRCDCOMMS.clear()

    # Reload Service modules
    for module in uplink.ModuleUtils.model_get_loaded_modules().copy():
        await uplink.ModuleUtils.reload_one_module(module.module_name, uplink.Settings.current_admin)

    uplink.Irc.signal = True
    await uplink.Irc.run()
    uplink.Config.DEFENDER_RESTART = 0

async def rehash_service(uplink: 'Loader', nickname: str) -> None:
    need_a_restart = ["SERVEUR_ID"]
    uplink.Settings.set_cache('db_commands', uplink.Commands.DB_COMMANDS)
    
    await uplink.RpcServer.stop_server()

    restart_flag = False
    config_model_bakcup = uplink.Config
    mods = REHASH_MODULES
    for mod in mods:
        importlib.reload(sys.modules[mod])
        await uplink.Irc.Protocol.send_priv_msg(
            nick_from=uplink.Config.SERVICE_NICKNAME,
            msg=f'[REHASH] Module [{mod}] reloaded', 
            channel=uplink.Config.SERVICE_CHANLOG
            )
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
    uplink.Commands.DB_COMMANDS = uplink.Settings.get_cache('db_commands')

    uplink.Base = uplink.BaseModule.Base(uplink)
    uplink.Irc.Protocol = uplink.PFactory.get()
    uplink.Irc.Protocol.register_command()

    uplink.RpcServer = uplink.RpcServerModule.JSonRpcServer(uplink)
    uplink.Base.create_asynctask(uplink.RpcServer.start_server())

    # Reload Service modules
    for module in uplink.ModuleUtils.model_get_loaded_modules().copy():
        await uplink.ModuleUtils.reload_one_module(module.module_name, nickname)

    return None