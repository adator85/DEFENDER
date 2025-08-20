import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mods.jsonrpc.mod_jsonrpc import Jsonrpc

def thread_subscribe(uplink: 'Jsonrpc') -> None:
    response: dict[str, dict] = {}
    snickname = uplink.Config.SERVICE_NICKNAME
    schannel = uplink.Config.SERVICE_CHANLOG

    if uplink.UnrealIrcdRpcLive.get_error.code == 0:
        uplink.is_streaming = True
        response = asyncio.run(uplink.UnrealIrcdRpcLive.subscribe(["all"]))
    else:
        uplink.Protocol.send_priv_msg(nick_from=snickname,
                msg=f"[{uplink.Config.COLORS.red}JSONRPC ERROR{uplink.Config.COLORS.nogc}] {uplink.UnrealIrcdRpcLive.get_error.message}", 
                channel=schannel
            )

    if response is None:
        return

    code = response.get('error', {}).get('code', 0)
    message = response.get('error', {}).get('message', None)

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

    response: dict[str, dict] = asyncio.run(uplink.UnrealIrcdRpcLive.unsubscribe())
    uplink.Logs.debug("[JSONRPC UNLOAD] Unsubscribe from the stream!")
    uplink.is_streaming = False
    uplink.update_configuration('jsonrpc', 0)
    snickname = uplink.Config.SERVICE_NICKNAME
    schannel = uplink.Config.SERVICE_CHANLOG

    if response is None:
        return None

    code = response.get('error', {}).get('code', 0)
    message = response.get('error', {}).get('message', None)

    if code != 0:
        uplink.Protocol.send_priv_msg(
                nick_from=snickname,
                msg=f"[{uplink.Config.COLORS.red}JSONRPC ERROR{uplink.Config.COLORS.nogc}] {message} ({code})", 
                channel=schannel
            )
