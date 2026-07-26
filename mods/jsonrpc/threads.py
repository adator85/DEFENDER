from typing import TYPE_CHECKING
from core.constants import Colors as colors

if TYPE_CHECKING:
    from mods.jsonrpc.mod_jsonrpc import Jsonrpc

async def thread_subscribe(uplink: 'Jsonrpc') -> None:

    snickname = uplink.ctx.Config.SERVICE_NICKNAME
    schannel = uplink.ctx.Config.SERVICE_CHANLOG

    if uplink.is_streaming:
        await uplink.ctx.Irc.Protocol.send_priv_msg(nick_from=snickname,
                msg=f"[ {colors.green}JSONRPC INFO{colors.nogc} ] IRCd Json-rpc already connected!", 
                channel=schannel
            )
        return None

    uplink.is_streaming = True
    response = await uplink.LiveRpc.subscribe(["all"])
    code = response.error.code
    message = response.error.message

    if code == 0:
        await uplink.ctx.Irc.Protocol.send_priv_msg(
                nick_from=snickname,
                msg=f"[ {colors.green}JSONRPC INFO{colors.nogc} ] Stream is OFF on IRCd json-rpc server!",
                channel=schannel
            )
    else:
        await uplink.ctx.Irc.Protocol.send_priv_msg(
                nick_from=snickname,
                msg=f"[ {colors.red}JSONRPC ERROR{colors.nogc} ] Stream has crashed on IRCd json-rpc server! {code} - {message}",
                channel=schannel
            )

    uplink.is_streaming = False
    return None

async def thread_unsubscribe(uplink: 'Jsonrpc') -> None:

    snickname = uplink.ctx.Config.SERVICE_NICKNAME
    schannel = uplink.ctx.Config.SERVICE_CHANLOG

    if not uplink.is_streaming:
        await uplink.ctx.Irc.Protocol.send_priv_msg(nick_from=snickname,
                msg=f"[ {colors.green}JSONRPC INFO{colors.nogc} ] IRCd Json-rpc is already off!",
                channel=schannel
            )
        return None

    response = await uplink.LiveRpc.unsubscribe()
    uplink.ctx.Logs.debug("[JSONRPC UNLOAD] Unsubscribe from the stream!")
    uplink.is_streaming = False
    code = response.error.code
    message = response.error.message

    if code != 0:
        await uplink.ctx.Irc.Protocol.send_priv_msg(
                nick_from=snickname,
                msg=f"[{colors.red}JSONRPC ERROR{colors.nogc}] {message} ({code})",
                channel=schannel
            )
