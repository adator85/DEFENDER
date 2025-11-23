from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mods.jsonrpc.mod_jsonrpc import Jsonrpc

async def thread_subscribe(uplink: 'Jsonrpc') -> None:

    snickname = uplink.ctx.Config.SERVICE_NICKNAME
    schannel = uplink.ctx.Config.SERVICE_CHANLOG
    if uplink.is_streaming:
        await uplink.ctx.Irc.Protocol.send_priv_msg(nick_from=snickname,
                msg=f"[{uplink.ctx.Config.COLORS.green}JSONRPC INFO{uplink.ctx.Config.COLORS.nogc}] IRCd Json-rpc already connected!", 
                channel=schannel
            )
        return None

    uplink.is_streaming = True
    response = await uplink.LiveRpc.subscribe(["all"])

    if response.error.code != 0:
        await uplink.ctx.Irc.Protocol.send_priv_msg(nick_from=snickname,
                msg=f"[{uplink.ctx.Config.COLORS.red}JSONRPC ERROR{uplink.ctx.Config.COLORS.nogc}] {response.error.message}", 
                channel=schannel
            )

    code = response.error.code
    message = response.error.message

    if code == 0:
        await uplink.ctx.Irc.Protocol.send_priv_msg(
                nick_from=snickname,
                msg=f"[{uplink.ctx.Config.COLORS.green}JSONRPC{uplink.ctx.Config.COLORS.nogc}] Stream is OFF", 
                channel=schannel
            )
        uplink.is_streaming = False
    else:
        await uplink.ctx.Irc.Protocol.send_priv_msg(
                nick_from=snickname,
                msg=f"[{uplink.ctx.Config.COLORS.red}JSONRPC{uplink.ctx.Config.COLORS.nogc}] Stream has crashed! {code} - {message}", 
                channel=schannel
            )
        uplink.is_streaming = False

async def thread_unsubscribe(uplink: 'Jsonrpc') -> None:

    snickname = uplink.ctx.Config.SERVICE_NICKNAME
    schannel = uplink.ctx.Config.SERVICE_CHANLOG

    if not uplink.is_streaming:
        await uplink.ctx.Irc.Protocol.send_priv_msg(nick_from=snickname,
                msg=f"[{uplink.ctx.Config.COLORS.green}JSONRPC INFO{uplink.ctx.Config.COLORS.nogc}] IRCd Json-rpc is already off!", 
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
                msg=f"[{uplink.ctx.Config.COLORS.red}JSONRPC ERROR{uplink.ctx.Config.COLORS.nogc}] {message} ({code})", 
                channel=schannel
            )
