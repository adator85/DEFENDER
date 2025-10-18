import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mods.jsonrpc.mod_jsonrpc import Jsonrpc

def thread_subscribe(uplink: 'Jsonrpc') -> None:

    snickname = uplink.Config.SERVICE_NICKNAME
    schannel = uplink.Config.SERVICE_CHANLOG
    uplink.is_streaming = True
    response = asyncio.run(uplink.LiveRpc.subscribe(["all"]))

    if response.error.code != 0:
        uplink.Protocol.send_priv_msg(nick_from=snickname,
                msg=f"[{uplink.Config.COLORS.red}JSONRPC ERROR{uplink.Config.COLORS.nogc}] {response.error.message}", 
                channel=schannel
            )

    code = response.error.code
    message = response.error.message

    if code == 0:
        uplink.Protocol.send_priv_msg(
                nick_from=snickname,
                msg=f"[{uplink.Config.COLORS.green}JSONRPC{uplink.Config.COLORS.nogc}] Stream is OFF", 
                channel=schannel
            )
    else:
        uplink.Protocol.send_priv_msg(
                nick_from=snickname,
                msg=f"[{uplink.Config.COLORS.red}JSONRPC{uplink.Config.COLORS.nogc}] Stream has crashed! {code} - {message}", 
                channel=schannel
            )

def thread_unsubscribe(uplink: 'Jsonrpc') -> None:

    response = asyncio.run(uplink.LiveRpc.unsubscribe())
    uplink.Logs.debug("[JSONRPC UNLOAD] Unsubscribe from the stream!")
    uplink.is_streaming = False
    uplink.update_configuration('jsonrpc', 0)
    snickname = uplink.Config.SERVICE_NICKNAME
    schannel = uplink.Config.SERVICE_CHANLOG

    code = response.error.code
    message = response.error.message

    if code != 0:
        uplink.Protocol.send_priv_msg(
                nick_from=snickname,
                msg=f"[{uplink.Config.COLORS.red}JSONRPC ERROR{uplink.Config.COLORS.nogc}] {message} ({code})", 
                channel=schannel
            )
