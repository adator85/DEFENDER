import asyncio
import gc
import importlib
import sys
import core.classes.modules.check_refs as cr
from types import ModuleType, FunctionType
from typing import TYPE_CHECKING
from core.utils import tr

if TYPE_CHECKING:
    from core.loader import Loader

# Modules impacted by rehashing!
REHASH_MODULES = [
    'core.utils',
    'core.base',
    'core.module',
    # 'core.definition',
    # 'core.constants',
    # 'core.classes.modules.settings',
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
    'core.classes.protocols.command_handler',
    'core.classes.interfaces.iprotocol',
    'core.classes.protocols.unreal6',
    'core.classes.protocols.inspircd',
    'core.classes.protocols.factory',
    # 'core.classes.interfaces.imodule',
]

async def restart_service_v2(uplink: 'Loader', reason: str = 'Restarting without reason!'):
    # Create a new subprocess.
    # Clean & Quit defender.
    # Start a new & clean instance of defender
    import subprocess

    logs = uplink.Logs
    await shutdown(uplink)
    uplink.Irc.signal = False
    uplink.Config.DEFENDER_EXIT_STATUS = 42 # set exit status to 42 (restart mode).

    try:
        if uplink.Irc.writer:
            uplink.Irc.writer.close()
            await uplink.Irc.writer.wait_closed()
    except Exception:
        pass

    if not uplink.Config.DEFENDER_STARTED_FROM_SYSTEMCTL:
        # If defender has started manually! restart through a new subprocess.
        logs.warning("Signal Off! Defender started manually, this is not recommended. Restaring a new instance.")
        subprocess.Popen(['.pyenv/bin/python', 'defender.py'])
        logs.debug("Kill main process.")

async def rehash_service(uplink: 'Loader', nickname: str) -> None:

    _colors = uplink.Const.Colors
    _protocol = uplink.Irc.Protocol
    _debug_level = uplink.Config.DEBUG_LEVEL
    _debug_hard = uplink.Config.DEBUG_HARD

    oldrefs = {}
    if _debug_level == 10 and _debug_hard:
        oldrefs = cr.snapshot_refs(uplink)
        uplink.Utils.write_gc_to_file()

    await (_protocol
           .send_priv_msg(
               uplink.Config.SERVICE_NICKNAME,
               msg=f'[ {_colors.blue}{_colors.bold}REHASH INFO{_colors.nogc}{_colors.reset} ] The system is going to rehash!',
               channel=uplink.Config.SERVICE_CHANLOG))
    del _protocol

    # Unload modules.
    for module in uplink.ModuleUtils.model_get_loaded_modules().copy():
        await uplink.ModuleUtils.unload_one_module(module.module_name)

    uplink.Config.DEFENDER_REHASH = 1
    need_a_restart = ["SERVEUR_ID"]
    uplink.Settings.set_cache('commands', uplink.Commands.DB_COMMANDS)
    uplink.Settings.set_cache('users', uplink.User.UID_DB)
    uplink.Settings.set_cache('admins', uplink.Admin.UID_ADMIN_DB)
    uplink.Settings.set_cache('reputations', uplink.Reputation.UID_REPUTATION_DB)
    uplink.Settings.set_cache('channels', uplink.Channel.UID_CHANNEL_DB)
    uplink.Settings.set_cache('sasl', uplink.Sasl.DB_SASL)
    uplink.Settings.set_cache('modules', uplink.ModuleUtils.DB_MODULES)

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

    await uplink.Base.stop_all_tasks()

    del (uplink.Utils, uplink.Config,
         uplink.Const, uplink.Definition)

    for mod in REHASH_MODULES:
        if mod in sys.modules:
            del sys.modules[mod]
        importlib.import_module(mod)

    _refresh_module_bindings([name for name in list(sys.modules)
         if name in ('core', 'mods')
         or name.startswith(('core.', 'mods.'))]
        + REHASH_MODULES)
    _refresh_loader_bindings(uplink)

    uplink.Const = sys.modules['core.constants']
    uplink.Definition = sys.modules['core.definition']
    uplink.Utils = sys.modules['core.utils']
    uplink.Config = uplink.ConfModule.Configuration(uplink).configuration_model
    uplink.Config.HSID = config_model_bakcup.HSID
    uplink.Config.DEFENDER_REHASH = config_model_bakcup.DEFENDER_REHASH
    uplink.Config.DEFENDER_INIT = config_model_bakcup.DEFENDER_INIT
    uplink.Config.DEFENDER_RESTART = config_model_bakcup.DEFENDER_RESTART
    uplink.Config.SSL_VERSION = config_model_bakcup.SSL_VERSION
    uplink.Config.CURRENT_VERSION = config_model_bakcup.CURRENT_VERSION
    uplink.Config.LATEST_VERSION = config_model_bakcup.LATEST_VERSION
    uplink.Config.DEFENDER_CONNEXION_DATETIME = config_model_bakcup.DEFENDER_CONNEXION_DATETIME
    uplink.Config.DEFENDER_STARTED_FROM_SYSTEMCTL = config_model_bakcup.DEFENDER_STARTED_FROM_SYSTEMCTL

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

    # Remove IRCd commands.
    uplink.Irc.Protocol.Handler.destroy()

    del (uplink.User, uplink.Admin, uplink.Channel,
         uplink.Reputation, uplink.ModuleUtils, uplink.Sasl,
         uplink.Irc.Protocol.Handler,
         uplink.Irc.Protocol, uplink.RpcServer, uplink.Base,
         _colors)

    uplink.Base = uplink.BaseModule.Base(uplink)
    uplink.User = sys.modules['core.classes.modules.user'].User(uplink)
    uplink.Settings.global_user = uplink.User
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
    uplink.ModuleUtils.DB_MODULES = uplink.Settings.get_cache('modules')

    uplink.Irc.Protocol = uplink.PFactory.get()

    if not uplink.Irc.Protocol.Handler.DB_IRCDCOMMS:
        uplink.Irc.Protocol.register_command()

    uplink.RpcServer = uplink.RpcServerModule.JSonRpcServer(uplink)
    if _was_rpc_connected:
        # if rpc server was running then start the RPC server
        uplink.DAsyncio.create_safe_task(uplink.RpcServer.start_rpc_server())

    # Reload Service modules
    # for module in uplink.ModuleUtils.model_get_loaded_modules().copy():
    #    await uplink.ModuleUtils.reload_one_module(module.module_name, nickname)
    if await uplink.ModuleUtils.db_load_all_existing_modules():
        uplink.Logs.debug('All modules loaded')

    uplink.Base.create_thread(uplink.Utils.heartbeat, uplink, uplink.Irc.beat, run_once=True)

    _colors = uplink.Const.Colors
    await uplink.Irc.Protocol.send_priv_msg(
        uplink.Config.SERVICE_NICKNAME,
        tr("[ %sREHASH INFO%s ] Rehash completed! %s modules reloaded.", _colors.green, _colors.nogc, _count_reloaded_modules),
        uplink.Config.SERVICE_CHANLOG)

    del (config_dict, _was_rpc_connected, config_model_bakcup,
         conf_bkp_dict, _count_reloaded_modules, _running_threads,
         _colors)

    uplink.Config.DEFENDER_REHASH = 0
    uplink.DAsyncio.create_task(uplink.Utils.run_garbage_collector,
                                  uplink,
                                  task_name='Defender Collect Garbarge',
                                  run_once=True,
                                  task_flag=True)

    # Run the python garbage collector.
    if _debug_level == 10 and _debug_hard:
        uplink.Utils.write_gc_to_file()
        collected = gc.collect()
        uplink.DAsyncio.create_safe_task(
            _report_leaks_later(uplink, nickname, oldrefs, collected),
            async_name='Defender Leak Report')

    return None

async def shutdown(uplink: 'Loader') -> None:
        """Methode qui va préparer l'arrêt complêt du service
        """
        _proto = uplink.Irc.Protocol
        _colors = uplink.Const.Colors
        _list_mods = uplink.ModuleUtils.model_get_loaded_modules().copy()

        await (_proto.send_priv_msg(
               uplink.Config.SERVICE_NICKNAME,
               msg=f'[ {_colors.blue}{_colors.bold}QUIT INFO{_colors.nogc}{_colors.reset} ] Shutting down!',
               channel=uplink.Config.SERVICE_CHANLOG))

        await uplink.Base.on_serv_shutdown()
        return None

        uplink.Logs.debug("=======> Unloading all modules!")
        _tasks: list[asyncio.Task] = [asyncio.create_task(uplink.RpcServer.stop_rpc_server()),
                                      asyncio.create_task(uplink.Base.stop_all_timers()),
                                      asyncio.create_task(uplink.Base.stop_all_tasks())]
        for module in uplink.ModuleUtils.model_get_loaded_modules().copy():
            _tasks.append(
                asyncio.create_task(
                    uplink.ModuleUtils.unload_one_module(module.module_name)
                )
            )

        uplink.Base.stop_all_sockets()
        uplink.Base.stop_all_threads()
        uplink.Base.stop_all_io_threads()

        await asyncio.gather(*_tasks)

        if uplink.Settings.RUNNING_ASYNC_TASKS:
            await asyncio.wait([t.task for t in uplink.Settings.RUNNING_ASYNC_TASKS if t.task is not None])

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

def _refresh_loader_bindings(uplink: 'Loader') -> None:
    """Rebind rehashed modules held by the Loader instance and rebuild PFactory.

    The Loader instance stores module objects (ConfModule, BaseModule,
    CommandModule, RpcServerModule, ...) that are never rebound after a rehash,
    so new subsystem instances would be created from the OLD classes. The
    protocol factory instance itself is never rebuilt either, so it keeps
    returning old protocol classes.
    """
    rehash_set = set(REHASH_MODULES)
    for attr, value in list(vars(uplink).items()):
        if isinstance(value, ModuleType) and value.__name__ in rehash_set:
            new = sys.modules.get(value.__name__)
            if new is not None: # and new is not value:
                setattr(uplink, attr, new)

    factory_mod = sys.modules.get('core.classes.protocols.factory')
    if factory_mod is not None:
        uplink.PFactory = factory_mod.ProtocolFactorty(uplink)

def _refresh_module_bindings(names) -> None:
    """Rebind references to rehashed modules/classes inside the given modules.

    After sys.modules entries are replaced, importers that were not reloaded
    (core.irc, core.loader, core itself, rehash.py, mods helpers, ...) still
    hold the old modules/classes in their dicts, pinning them forever. This
    rebinds module attributes and function/class attributes whose origin module
    was rehashed to the fresh objects now living in sys.modules.
    """
    rehash_set = set(REHASH_MODULES)
    for name in names:
        mod = sys.modules.get(name)
        if mod is None:
            continue
        for attr, value in list(vars(mod).items()):
            if attr.startswith('__') and attr.endswith('__'):
                continue
            if isinstance(value, ModuleType):
                if value.__name__ in rehash_set:
                    new = sys.modules.get(value.__name__)
                    if new is not None and new is not value:
                        setattr(mod, attr, new)
            elif isinstance(value, (FunctionType, type)):
                mod_name = getattr(value, '__module__', None)
                if mod_name in rehash_set:
                    new_mod = sys.modules.get(mod_name or '', None)
                    if new_mod is not None:
                        new_value = getattr(new_mod, value.__name__, None)
                        if new_value is not None and new_value is not value:
                            setattr(mod, attr, new_value)

async def _report_leaks_later(uplink: 'Loader', nickname: str,
                              oldrefs: dict, collected: int) -> None:
    """Report rehash leaks once the rehash call stack has unwound.

    Checking immediately at the end of rehash_service sees transient referrers
    (the in-flight command coroutine, the rehash frame itself) and produces
    false positives, so the check is deferred a couple of seconds.
    """
    await asyncio.sleep(2)

    leaks = cr.check_leaks_v2(oldrefs)
    stale = cr.find_stale_classes()
    stale_modules = cr.find_stale_modules()
    rss_kb = cr.get_rss_kb()
    cr.store_report(nickname, oldrefs, leaks, stale, collected,
                    stale_modules=stale_modules, rss_kb=rss_kb)
    cr.write_report_to_log()

    _alive = len(leaks)
    _released = len(oldrefs) - _alive
    _colors = uplink.Const.Colors
    if _alive or stale or stale_modules:
        _summary = (f'[ {_colors.red}{_colors.bold}REHASH LEAKS{_colors.nogc}{_colors.reset} ] '
                    f'{_released}/{len(oldrefs)} old subsystem object(s) released, '
                    f'{_alive} still referenced, {len(stale)} stale class(es), '
                    f'{len(stale_modules)} stale module(s) - '
                    f'run {uplink.Config.SERVICE_PREFIX}show_leaks')
    else:
        _summary = (f'[ {_colors.green}{_colors.bold}REHASH LEAKS{_colors.nogc}{_colors.reset} ] '
                    f'No stale references: {_released}/{len(oldrefs)} old subsystem object(s) released '
                    f'(rss {rss_kb / 1024:.1f}MiB)')

    await uplink.Irc.Protocol.send_priv_msg(
        nick_from=uplink.Config.SERVICE_NICKNAME,
        msg=_summary,
        channel=uplink.Config.SERVICE_CHANLOG)
