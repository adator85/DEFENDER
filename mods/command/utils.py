from typing import TYPE_CHECKING, Literal, Optional

if TYPE_CHECKING:
    from mods.command.mod_command import Command


async def set_automode(uplink: 'Command', cmd: list[str], client: str) -> None:

    command: str = str(cmd[0]).lower()
    option: str = str(cmd[1]).lower()
    allowed_modes: list[str] = uplink.ctx.Settings.PROTOCTL_PREFIX # ['q','a','o','h','v']
    dnickname = uplink.ctx.Config.SERVICE_NICKNAME
    service_id = uplink.ctx.Config.SERVICE_ID
    fromuser = client

    match option:
        case 'set':
            if len(cmd) < 5:
                await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {command.upper()} [nickname] [+/-mode] [#channel]")
                await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"AutoModes available: {' / '.join(allowed_modes)}")
                return None

            nickname = str(cmd[2])
            mode = str(cmd[3])
            chan: str = str(cmd[4]).lower() if uplink.ctx.Channel.is_valid_channel(cmd[4]) else None
            sign = mode[0] if mode.startswith( ('+', '-')) else None
            clean_mode = mode[1:] if len(mode) > 0 else None

            if sign is None:
                await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg="You must provide the flag mode + or -")
                return None

            if clean_mode not in allowed_modes:
                await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"You should use one of those modes {' / '.join(allowed_modes)}")
                return None

            if chan is None:
                await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"You should use one of those modes {' / '.join(allowed_modes)}")
                return None

            db_data: dict[str, str] = {"nickname": nickname, "channel": chan}
            db_query = await uplink.ctx.Base.db_execute_query(query="SELECT id FROM command_automode WHERE nickname = :nickname and channel = :channel", params=db_data)
            db_result = db_query.fetchone()

            if db_result is not None:
                if sign == '+':
                    db_data = {"updated_on": uplink.ctx.Utils.get_sdatetime(), "nickname": nickname, "channel": chan, "mode": mode}
                    db_result = await uplink.ctx.Base.db_execute_query(query="UPDATE command_automode SET mode = :mode, updated_on = :updated_on WHERE nickname = :nickname and channel = :channel",
                                                    params=db_data)
                    if db_result.rowcount > 0:
                        await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Automode {mode} edited for {nickname} in {chan}")
                elif sign == '-':
                    db_data = {"nickname": nickname, "channel": chan, "mode": f"+{clean_mode}"}
                    db_result = await uplink.ctx.Base.db_execute_query(query="DELETE FROM command_automode WHERE nickname = :nickname and channel = :channel and mode = :mode",
                                                    params=db_data)
                    if db_result.rowcount > 0:
                        await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Automode {mode} deleted for {nickname} in {chan}")
                    else:
                        await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"The mode [{mode}] has not been found for {nickname} in channel {chan}")

                return None

            # Instert a new automode
            if sign == '+':
                db_data = {"created_on": uplink.ctx.Utils.get_sdatetime(), "updated_on": uplink.ctx.Utils.get_sdatetime(), "nickname": nickname, "channel": chan, "mode": mode}
                db_query = await uplink.ctx.Base.db_execute_query(
                    query="INSERT INTO command_automode (created_on, updated_on, nickname, channel, mode) VALUES (:created_on, :updated_on, :nickname, :channel, :mode)",
                    params=db_data
                )

                if db_query.rowcount > 0:
                    await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"Automode {mode} applied to {nickname} in {chan}")
                    if uplink.ctx.Channel.is_user_present_in_channel(chan, uplink.ctx.User.get_uid(nickname)):
                        await uplink.ctx.Irc.Protocol.send2socket(f":{service_id} MODE {chan} {mode} {nickname}")
            else:
                await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"AUTOMODE {mode} cannot be added to {nickname} in {chan} because it doesn't exist")

        case 'list':
            db_query = await uplink.ctx.Base.db_execute_query("SELECT nickname, channel, mode FROM command_automode")
            db_results = db_query.fetchall()

            if not db_results:
                await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,
                                            msg="There is no automode to display.")

            for db_result in db_results:
                db_nickname, db_channel, db_mode = db_result
                await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser,
                                            msg=f"Nickname: {db_nickname} | Channel: {db_channel} | Mode: {db_mode}")

        case _:
            await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {command.upper()} SET [nickname] [+/-mode] [#channel]")
            await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"/msg {dnickname} {command.upper()} LIST")
            await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=fromuser, msg=f"[AUTOMODES AVAILABLE] are {' / '.join(allowed_modes)}")

async def set_deopall(uplink: 'Command', channel_name: str) -> None:

    service_id = uplink.ctx.Config.SERVICE_ID
    await uplink.ctx.Irc.Protocol.send2socket(f":{service_id} SVSMODE {channel_name} -o")
    return None

async def set_devoiceall(uplink: 'Command', channel_name: str) -> None:
    
    service_id = uplink.ctx.Config.SERVICE_ID
    await uplink.ctx.Irc.Protocol.send2socket(f":{service_id} SVSMODE {channel_name} -v")
    return None

async def set_mode_to_all(uplink: 'Command', channel_name: str, action: Literal['+', '-'], pmode: str) -> None:
    
    chan_info = uplink.ctx.Channel.get_channel(channel_name)
    service_id = uplink.ctx.Config.SERVICE_ID
    dnickname = uplink.ctx.Config.SERVICE_NICKNAME
    set_mode = pmode
    mode:str = ''
    users:str = ''
    uids_split = [chan_info.uids[i:i + 6] for i in range(0, len(chan_info.uids), 6)]

    await uplink.ctx.Irc.Protocol.send2socket(f":{service_id} MODE {channel_name} {action}{set_mode} {dnickname}")
    for uid in uids_split:
        for i in range(0, len(uid)):
            mode += set_mode
            users += f'{uplink.ctx.User.get_nickname(uplink.ctx.Utils.clean_uid(uid[i]))} '
            if i == len(uid) - 1:
                await uplink.ctx.Irc.Protocol.send2socket(f":{service_id} MODE {channel_name} {action}{mode} {users}")
                mode = ''
                users = ''

async def set_operation(uplink: 'Command', cmd: list[str], channel_name: Optional[str], client: str, mode: str) -> None:

    dnickname = uplink.ctx.Config.SERVICE_NICKNAME
    service_id = uplink.ctx.Config.SERVICE_ID
    if channel_name is None:
        await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=client, msg=f" Right command : /msg {dnickname} {mode} [#SALON] [NICKNAME]")
        return False

    if len(cmd) == 1:
        # await uplink.ctx.Irc.Protocol.send2socket(f":{service_id} MODE {channel_name} {mode} {client}")
        await uplink.ctx.Irc.Protocol.send_set_mode(mode, nickname=client, channel_name=channel_name)
        return None

    # deop nickname
    if len(cmd) == 2:
        nickname = cmd[1]
        # await uplink.ctx.Irc.Protocol.send2socket(f":{service_id} MODE {channel_name} {mode} {nickname}")
        await uplink.ctx.Irc.Protocol.send_set_mode(mode, nickname=nickname, channel_name=channel_name)
        return None

    nickname = cmd[2]
    # await uplink.ctx.Irc.Protocol.send2socket(f":{service_id} MODE {channel_name} {mode} {nickname}")
    await uplink.ctx.Irc.Protocol.send_set_mode(mode, nickname=nickname, channel_name=channel_name)
    return None

async def set_ban(uplink: 'Command', cmd: list[str], action: Literal['+', '-'], client: str) -> None:
    
    command = str(cmd[0])
    dnickname = uplink.ctx.Config.SERVICE_NICKNAME
    service_id = uplink.ctx.Config.SERVICE_ID
    sentchannel = str(cmd[1]) if uplink.ctx.Channel.is_valid_channel(cmd[1]) else None

    if sentchannel is None:
        await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=client, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON] [NICKNAME]")
        return None

    nickname = cmd[2]

    await uplink.ctx.Irc.Protocol.send2socket(f":{service_id} MODE {sentchannel} {action}b {nickname}!*@*")
    uplink.ctx.Logs.debug(f'{client} has banned {nickname} from {sentchannel}')
    return None

async def set_kick(uplink: 'Command', cmd: list[str], client: str) -> None:

    command = str(cmd[0])
    dnickname = uplink.ctx.Config.SERVICE_NICKNAME
    service_id = uplink.ctx.Config.SERVICE_ID

    sentchannel = str(cmd[1]) if uplink.ctx.Channel.is_valid_channel(cmd[1]) else None
    if sentchannel is None:
        await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=client, msg=f" Right command : /msg {dnickname} {command} [#SALON] [NICKNAME]")
        return False

    nickname = cmd[2]
    final_reason = ' '.join(cmd[3:])

    await uplink.ctx.Irc.Protocol.send2socket(f":{service_id} KICK {sentchannel} {nickname} {final_reason}")
    uplink.ctx.Logs.debug(f'{client} has kicked {nickname} from {sentchannel} : {final_reason}')
    return None

async def set_kickban(uplink: 'Command', cmd: list[str], client: str) -> None:

    command = str(cmd[0])
    dnickname = uplink.ctx.Config.SERVICE_NICKNAME
    service_id = uplink.ctx.Config.SERVICE_ID

    sentchannel = str(cmd[1]) if uplink.ctx.Channel.is_valid_channel(cmd[1]) else None
    if sentchannel is None:
        await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=client, msg=f" Right command : /msg {dnickname} {command} [#SALON] [NICKNAME]")
        return False
    nickname = cmd[2]
    final_reason = ' '.join(cmd[3:])

    await uplink.ctx.Irc.Protocol.send2socket(f":{service_id} KICK {sentchannel} {nickname} {final_reason}")
    await uplink.ctx.Irc.Protocol.send2socket(f":{service_id} MODE {sentchannel} +b {nickname}!*@*")
    uplink.ctx.Logs.debug(f'{client} has kicked and banned {nickname} from {sentchannel} : {final_reason}')

async def set_assign_channel_to_service(uplink: 'Command', cmd: list[str], client: str) -> None:

    if len(cmd) < 2:
        raise IndexError(f"{cmd[0].upper()} is expecting the channel parameter")

    command = str(cmd[0])
    dnickname = uplink.ctx.Config.SERVICE_NICKNAME
    sent_channel = str(cmd[1]) if uplink.ctx.Channel.is_valid_channel(cmd[1]) else None
    if sent_channel is None:
        await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=client, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON]")
        return None

    # self.Protocol.send2socket(f':{service_id} JOIN {sent_channel}')
    await uplink.ctx.Irc.Protocol.send_join_chan(uidornickname=dnickname,channel=sent_channel)
    await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=client, msg=f" Has joined {sent_channel}")
    await uplink.ctx.Channel.db_query_channel('add', uplink.module_name, sent_channel)

    return None

async def set_unassign_channel_to_service(uplink: 'Command', cmd: list[str], client: str) -> None:

    if len(cmd) < 2:
        raise IndexError(f"{cmd[0].upper()} is expecting the channel parameter")

    command = str(cmd[0])
    dnickname = uplink.ctx.Config.SERVICE_NICKNAME
    dchanlog = uplink.ctx.Config.SERVICE_CHANLOG

    sent_channel = str(cmd[1]) if uplink.ctx.Channel.is_valid_channel(cmd[1]) else None
    if sent_channel is None:
        await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=client, msg=f" Right command : /msg {dnickname} {command.upper()} [#SALON]")
        return None

    if sent_channel ==  dchanlog:
        await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=client, msg=f"[!] CAN'T LEFT {sent_channel} AS IT IS LOG CHANNEL [!]")
        return None

    await uplink.ctx.Irc.Protocol.send_part_chan(uidornickname=dnickname, channel=sent_channel)
    await uplink.ctx.Irc.Protocol.send_notice(nick_from=dnickname, nick_to=client, msg=f" Has left {sent_channel}")

    await uplink.ctx.Channel.db_query_channel('del', uplink.module_name, sent_channel)
    return None