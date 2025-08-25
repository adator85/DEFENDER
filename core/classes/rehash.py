import importlib
import sys
import time
from typing import TYPE_CHECKING
import socket
from core.classes.protocol import Protocol

if TYPE_CHECKING:
    from core.irc import Irc

# Modules impacted by rehashing!
REHASH_MODULES = [
    'core.definition',
    'core.utils',
    'core.classes.config',
    'core.base',
    'core.classes.commands',
    'core.classes.protocols.unreal6',
    'core.classes.protocols.inspircd',
    'core.classes.protocol'
]


def restart_service(uplink: 'Irc', reason: str = "Restarting with no reason!") -> None:

    # reload modules.
    for module in uplink.ModuleUtils.model_get_loaded_modules().copy():
        uplink.ModuleUtils.unload_one_module(uplink, module.module_name)

    uplink.ModuleUtils.model_clear()          # Clear loaded modules.
    uplink.User.UID_DB.clear()                # Clear User Object
    uplink.Channel.UID_CHANNEL_DB.clear()     # Clear Channel Object
    uplink.Client.CLIENT_DB.clear()           # Clear Client object
    uplink.Base.garbage_collector_thread()

    # Reload configuration
    uplink.Config = uplink.Loader.ConfModule.Configuration(uplink.Loader).get_config_model()
    uplink.Base = uplink.Loader.BaseModule.Base(uplink.Loader)
    uplink.Protocol = Protocol(uplink.Config.SERVEUR_PROTOCOL, uplink.ircObject).Protocol
    uplink.Logs.debug(f'[{uplink.Config.SERVICE_NICKNAME} RESTART]: Reloading configuration!')

    uplink.Protocol.send_squit(server_id=uplink.Config.SERVEUR_ID, server_link=uplink.Config.SERVEUR_LINK, reason="Defender Power off")

    uplink.Logs.debug('Restarting Defender ...')
    uplink.IrcSocket.shutdown(socket.SHUT_RDWR)
    uplink.IrcSocket.close()

    while uplink.IrcSocket.fileno() != -1:
        time.sleep(0.5)
        uplink.Logs.warning('-- Waiting for socket to close ...')

    uplink.init_service_user()
    uplink.Utils.create_socket(uplink)
    uplink.Protocol.send_link()
    uplink.join_saved_channels()
    uplink.ModuleUtils.db_load_all_existing_modules(uplink)
    uplink.Config.DEFENDER_RESTART = 0

def rehash_service(uplink: 'Irc', nickname: str) -> None:
    need_a_restart = ["SERVEUR_ID"]
    uplink.Settings.set_cache('db_commands', uplink.Commands.DB_COMMANDS)
    restart_flag = False
    config_model_bakcup = uplink.Config
    mods = REHASH_MODULES
    for mod in mods:
        importlib.reload(sys.modules[mod])
        uplink.Protocol.send_priv_msg(
            nick_from=uplink.Config.SERVICE_NICKNAME,
            msg=f'[REHASH] Module [{mod}] reloaded', 
            channel=uplink.Config.SERVICE_CHANLOG
            )
    uplink.Utils = sys.modules['core.utils']
    uplink.Config = uplink.Loader.ConfModule.Configuration(uplink.Loader).get_config_model()
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
            uplink.Protocol.send_priv_msg(
                nick_from=uplink.Config.SERVICE_NICKNAME,
                msg=f'[{key}]: {value} ==> {config_dict[key]}', 
                channel=uplink.Config.SERVICE_CHANLOG
                )
            if key in need_a_restart:
                restart_flag = True

    if config_model_bakcup.SERVICE_NICKNAME != uplink.Config.SERVICE_NICKNAME:
        uplink.Protocol.send_set_nick(uplink.Config.SERVICE_NICKNAME)

    if restart_flag:
        uplink.Config.SERVEUR_ID = config_model_bakcup.SERVEUR_ID
        uplink.Protocol.send_priv_msg(
            nick_from=uplink.Config.SERVICE_NICKNAME,
            channel=uplink.Config.SERVICE_CHANLOG, 
            msg='You need to restart defender !')

    # Reload Main Commands Module
    uplink.Commands = uplink.Loader.CommandModule.Command(uplink.Loader)
    uplink.Commands.DB_COMMANDS = uplink.Settings.get_cache('db_commands')

    uplink.Base = uplink.Loader.BaseModule.Base(uplink.Loader)
    uplink.Protocol = Protocol(uplink.Config.SERVEUR_PROTOCOL, uplink.ircObject).Protocol

    # Reload Service modules
    for module in uplink.ModuleUtils.model_get_loaded_modules().copy():
        uplink.ModuleUtils.reload_one_module(uplink, module.module_name, nickname)

    return None