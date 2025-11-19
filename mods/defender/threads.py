import asyncio
from typing import TYPE_CHECKING
from time import sleep

if TYPE_CHECKING:
    from mods.defender.mod_defender import Defender

async def coro_apply_reputation_sanctions(uplink: 'Defender'):
    while uplink.reputationTimer_isRunning:
        await uplink.mod_utils.action_apply_reputation_santions(uplink)
        await asyncio.sleep(5)

async def coro_cloudfilt_scan(uplink: 'Defender'):

    while uplink.cloudfilt_isRunning:
        list_to_remove:list = []
        for user in uplink.Schemas.DB_CLOUDFILT_USERS:
            uplink.mod_utils.action_scan_client_with_cloudfilt(uplink, user)
            list_to_remove.append(user)
            await asyncio.sleep(1)

        for user_model in list_to_remove:
            uplink.Schemas.DB_CLOUDFILT_USERS.remove(user_model)

        await asyncio.sleep(1)

async def coro_freeipapi_scan(uplink: 'Defender'):

    while uplink.freeipapi_isRunning:

        list_to_remove: list = []
        for user in uplink.Schemas.DB_FREEIPAPI_USERS:
            uplink.mod_utils.action_scan_client_with_freeipapi(uplink, user)
            list_to_remove.append(user)
            await asyncio.sleep(1)

        for user_model in list_to_remove:
            uplink.Schemas.DB_FREEIPAPI_USERS.remove(user_model)

        await asyncio.sleep(1)

async def coro_abuseipdb_scan(uplink: 'Defender'):

    while uplink.abuseipdb_isRunning:

        list_to_remove: list = []
        for user in uplink.Schemas.DB_ABUSEIPDB_USERS:
            uplink.mod_utils.action_scan_client_with_abuseipdb(uplink, user)
            list_to_remove.append(user)
            await asyncio.sleep(1)

        for user_model in list_to_remove:
            uplink.Schemas.DB_ABUSEIPDB_USERS.remove(user_model)

        await asyncio.sleep(1)

async def coro_local_scan(uplink: 'Defender'):

    while uplink.localscan_isRunning:
        list_to_remove:list = []
        for user in uplink.Schemas.DB_LOCALSCAN_USERS:
            uplink.mod_utils.action_scan_client_with_local_socket(uplink, user)
            list_to_remove.append(user)
            await asyncio.sleep(1)

        for user_model in list_to_remove:
            uplink.Schemas.DB_LOCALSCAN_USERS.remove(user_model)

        await asyncio.sleep(1)

async def coro_psutil_scan(uplink: 'Defender'):

        while uplink.psutil_isRunning:

            list_to_remove:list = []
            for user in uplink.Schemas.DB_PSUTIL_USERS:
                uplink.mod_utils.action_scan_client_with_psutil(uplink, user)
                list_to_remove.append(user)
                await asyncio.sleep(1)

            for user_model in list_to_remove:
                uplink.Schemas.DB_PSUTIL_USERS.remove(user_model)

            await asyncio.sleep(1)

async def coro_autolimit(uplink: 'Defender'):

    if uplink.mod_config.autolimit == 0:
        uplink.ctx.Logs.debug("autolimit deactivated ... canceling the thread")
        return None

    while uplink.ctx.Irc.autolimit_started:
        await asyncio.sleep(0.2)

    uplink.ctx.Irc.autolimit_started = True
    init_amount = uplink.mod_config.autolimit_amount
    p = uplink.ctx.Irc.Protocol
    INIT = 1

    # Copy Channels to a list of dict
    chanObj_copy: list[dict[str, int]] = [{"name": c.name, "uids_count": len(c.uids)} for c in uplink.ctx.Channel.UID_CHANNEL_DB]
    chan_list: list[str] = [c.name for c in uplink.ctx.Channel.UID_CHANNEL_DB]

    while uplink.autolimit_isRunning:

        if uplink.mod_config.autolimit == 0:
            uplink.ctx.Logs.debug("autolimit deactivated ... stopping the current thread")
            break

        for chan in uplink.ctx.Channel.UID_CHANNEL_DB:
            for chan_copy in chanObj_copy:
                if chan_copy["name"] == chan.name and len(chan.uids) != chan_copy["uids_count"]:
                    await p.send2socket(f":{uplink.ctx.Config.SERVICE_ID} MODE {chan.name} +l {len(chan.uids) + uplink.mod_config.autolimit_amount}")
                    chan_copy["uids_count"] = len(chan.uids)

            if chan.name not in chan_list:
                chan_list.append(chan.name)
                chanObj_copy.append({"name": chan.name, "uids_count": 0})

        # Verifier si un salon a été vidé
        current_chan_in_list = [d.name for d in uplink.ctx.Channel.UID_CHANNEL_DB]
        for c in chan_list:
            if c not in current_chan_in_list:
                chan_list.remove(c)

        # Si c'est la premiere execution
        if INIT == 1:
            for chan in uplink.ctx.Channel.UID_CHANNEL_DB:
                await p.send2socket(f":{uplink.ctx.Config.SERVICE_ID} MODE {chan.name} +l {len(chan.uids) + uplink.mod_config.autolimit_amount}")

        # Si le nouveau amount est différent de l'initial
        if init_amount != uplink.mod_config.autolimit_amount:
            init_amount = uplink.mod_config.autolimit_amount
            for chan in uplink.ctx.Channel.UID_CHANNEL_DB:
                await p.send2socket(f":{uplink.ctx.Config.SERVICE_ID} MODE {chan.name} +l {len(chan.uids) + uplink.mod_config.autolimit_amount}")

        INIT = 0

        if uplink.autolimit_isRunning:
            await asyncio.sleep(uplink.mod_config.autolimit_interval)

    for chan in uplink.ctx.Channel.UID_CHANNEL_DB:
        # await p.send2socket(f":{uplink.ctx.Config.SERVICE_ID} MODE {chan.name} -l")
        await p.send_set_mode('-l', channel_name=chan.name)

    uplink.ctx.Irc.autolimit_started = False

    return None

async def coro_release_mode_mute(uplink: 'Defender', action: str, channel: str):
    """DO NOT EXECUTE THIS FUNCTION DIRECTLY
    IT WILL BLOCK THE PROCESS

    Args:
        action (str): mode-m
        channel (str): The related channel

    """
    service_id = uplink.ctx.Config.SERVICE_ID
    timeout = uplink.mod_config.flood_timer
    await asyncio.sleep(timeout)

    if not uplink.ctx.Channel.is_valid_channel(channel):
        uplink.ctx.Logs.debug(f"Channel is not valid {channel}")
        return

    match action:
        case 'mode-m':
            # Action -m sur le salon
            await uplink.ctx.Irc.Protocol.send2socket(f":{service_id} MODE {channel} -m")
        case _:
            pass
