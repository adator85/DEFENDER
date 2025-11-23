import asyncio
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mods.defender.mod_defender import Defender

async def coro_apply_reputation_sanctions(uplink: 'Defender'):
    uplink.reputationTimer_isRunning = True
    while uplink.reputationTimer_isRunning:
        await uplink.mod_utils.action_apply_reputation_santions(uplink)
        await asyncio.sleep(5)

async def coro_cloudfilt_scan(uplink: 'Defender'):
    uplink.cloudfilt_isRunning = True
    service_id = uplink.ctx.Config.SERVICE_ID
    service_chanlog = uplink.ctx.Config.SERVICE_CHANLOG
    color_red = uplink.ctx.Config.COLORS.red
    nogc = uplink.ctx.Config.COLORS.nogc
    nogc = uplink.ctx.Config.COLORS.nogc
    p = uplink.ctx.Irc.Protocol

    while uplink.cloudfilt_isRunning:
        try:
            list_to_remove:list = []
            for user in uplink.Schemas.DB_CLOUDFILT_USERS:
                if user.remote_ip not in uplink.ctx.Config.WHITELISTED_IP:
                    result: Optional[dict] = await uplink.ctx.Base.create_thread_io(
                        uplink.mod_utils.action_scan_client_with_cloudfilt,
                        uplink, user
                    )
                    list_to_remove.append(user)

                    if not result:
                        continue

                    remote_ip = user.remote_ip
                    fullname = f'{user.nickname}!{user.username}@{user.hostname}'

                    r_host = result.get('host', None)
                    r_countryiso = result.get('countryiso', None)
                    r_listed = result.get('listed', False)
                    r_listedby = result.get('listed_by', None)

                    await p.send_priv_msg(
                        nick_from=service_id,
                        msg=f"[ {color_red}CLOUDFILT_SCAN{nogc} ] : Connexion de {fullname} ({remote_ip}) ==> Host: {r_host} | country: {r_countryiso} | listed: {r_listed} | listed by : {r_listedby}",
                        channel=service_chanlog)
                    
                    uplink.ctx.Logs.debug(f"[CLOUDFILT SCAN] ({fullname}) connected from ({r_countryiso}), Listed: {r_listed}, by: {r_listedby}")

                    if r_listed:
                        await p.send2socket(f":{service_id} GLINE +*@{remote_ip} {uplink.ctx.Config.GLINE_DURATION} Your connexion is listed as dangerous {r_listed} {r_listedby} - detected by cloudfilt")
                        uplink.ctx.Logs.debug(f"[CLOUDFILT SCAN GLINE] Dangerous connection ({fullname}) from ({r_countryiso}) Listed: {r_listed}, by: {r_listedby}")


                    await asyncio.sleep(1)

                for user_model in list_to_remove:
                    uplink.Schemas.DB_CLOUDFILT_USERS.remove(user_model)

            await asyncio.sleep(1.5)
        except ValueError as ve:
            uplink.ctx.Logs.debug(f"The value to remove is not in the list. {ve}")
        except TimeoutError as te:
            uplink.ctx.Logs.debug(f"Timeout Error {te}")

async def coro_freeipapi_scan(uplink: 'Defender'):
    uplink.freeipapi_isRunning = True
    service_id = uplink.ctx.Config.SERVICE_ID
    service_chanlog = uplink.ctx.Config.SERVICE_CHANLOG
    color_red = uplink.ctx.Config.COLORS.red
    nogc = uplink.ctx.Config.COLORS.nogc
    p = uplink.ctx.Irc.Protocol
    
    while uplink.freeipapi_isRunning:
        try:
            list_to_remove: list = []
            for user in uplink.Schemas.DB_FREEIPAPI_USERS:
                if user.remote_ip not in uplink.ctx.Config.WHITELISTED_IP:
                    result: Optional[dict] = await uplink.ctx.Base.create_thread_io(
                        uplink.mod_utils.action_scan_client_with_freeipapi,
                        uplink, user
                    )

                    if not result:
                        continue

                    # pseudo!ident@host
                    remote_ip = user.remote_ip
                    fullname = f'{user.nickname}!{user.username}@{user.hostname}'

                    await p.send_priv_msg(
                        nick_from=service_id,
                        msg=f"[ {color_red}FREEIPAPI_SCAN{nogc} ] : Connexion de {fullname} ({remote_ip}) ==> Proxy: {str(result['isProxy'])} | Country : {str(result['countryCode'])}",
                        channel=service_chanlog)    
                    uplink.ctx.Logs.debug(f"[FREEIPAPI SCAN] ({fullname}) connected from ({result['countryCode']}), Proxy: {result['isProxy']}") 

                    if result['isProxy']:
                        await p.send2socket(f":{service_id} GLINE +*@{remote_ip} {uplink.ctx.Config.GLINE_DURATION} This server do not allow proxy connexions {str(result['isProxy'])} - detected by freeipapi")
                        uplink.ctx.Logs.debug(f"[FREEIPAPI SCAN GLINE] Server do not allow proxy connexions {result['isProxy']}")

                    list_to_remove.append(user)
                    await asyncio.sleep(1)

            # remove users from the list
            for user_model in list_to_remove:
                uplink.Schemas.DB_FREEIPAPI_USERS.remove(user_model)

            await asyncio.sleep(1.5)
        except ValueError as ve:
            uplink.ctx.Logs.debug(f"The value to remove is not in the list. {ve}")
        except TimeoutError as te:
            uplink.ctx.Logs.debug(f"Timeout Error {te}")

async def coro_abuseipdb_scan(uplink: 'Defender'):

    uplink.abuseipdb_isRunning = True
    service_id = uplink.ctx.Config.SERVICE_ID
    service_chanlog = uplink.ctx.Config.SERVICE_CHANLOG
    color_red = uplink.ctx.Config.COLORS.red
    nogc = uplink.ctx.Config.COLORS.nogc
    p = uplink.ctx.Irc.Protocol
    
    while uplink.abuseipdb_isRunning:
        try:
            list_to_remove: list = []
            for user in uplink.Schemas.DB_ABUSEIPDB_USERS:
                if user.remote_ip not in uplink.ctx.Config.WHITELISTED_IP:

                    result: Optional[dict] = await uplink.ctx.Base.create_thread_io(
                        uplink.mod_utils.action_scan_client_with_abuseipdb,
                        uplink, user
                    )
                    list_to_remove.append(user)

                    if not result:
                        continue

                    remote_ip = user.remote_ip
                    fullname = f'{user.nickname}!{user.username}@{user.hostname}'

                    await p.send_priv_msg(
                        nick_from=service_id,
                        msg=f"[ {color_red}ABUSEIPDB_SCAN{nogc} ] : Connexion de {fullname} ({remote_ip}) ==> Score: {str(result['score'])} | Country : {result['country']} | Tor : {str(result['isTor'])} | Total Reports : {str(result['totalReports'])}",
                        channel=service_chanlog
                        )
                    uplink.ctx.Logs.debug(f"[ABUSEIPDB SCAN] ({fullname}) connected from ({result['country']}), Score: {result['score']}, Tor: {result['isTor']}")

                    if result['isTor']:
                        await p.send2socket(f":{service_id} GLINE +*@{remote_ip} {uplink.ctx.Config.GLINE_DURATION} This server do not allow Tor connexions {str(result['isTor'])} - Detected by Abuseipdb")
                        uplink.ctx.Logs.debug(f"[ABUSEIPDB SCAN GLINE] Server do not allow Tor connections Tor: {result['isTor']}, Score: {result['score']}")
                    elif result['score'] >= 95:
                        await p.send2socket(f":{service_id} GLINE +*@{remote_ip} {uplink.ctx.Config.GLINE_DURATION} You were banned from this server because your abuse score is = {str(result['score'])} - Detected by Abuseipdb")
                        uplink.ctx.Logs.debug(f"[ABUSEIPDB SCAN GLINE] Server do not high risk connections Country: {result['country']}, Score: {result['score']}")

                await asyncio.sleep(1)

            for user_model in list_to_remove:
                uplink.Schemas.DB_ABUSEIPDB_USERS.remove(user_model)

            await asyncio.sleep(1.5)
        except ValueError as ve:
            uplink.ctx.Logs.debug(f"The value to remove is not in the list. {ve}", exc_info=True)
        except TimeoutError as te:
            uplink.ctx.Logs.debug(f"Timeout Error {te}", exc_info=True)

async def coro_local_scan(uplink: 'Defender'):
    uplink.localscan_isRunning = True
    service_id = uplink.ctx.Config.SERVICE_ID
    service_chanlog = uplink.ctx.Config.SERVICE_CHANLOG
    color_red = uplink.ctx.Config.COLORS.red
    nogc = uplink.ctx.Config.COLORS.nogc
    p = uplink.ctx.Irc.Protocol

    while uplink.localscan_isRunning:
        try:
            list_to_remove:list = []
            for user in uplink.Schemas.DB_LOCALSCAN_USERS:
                if user.remote_ip not in uplink.ctx.Config.WHITELISTED_IP:
                    list_to_remove.append(user)
                    result = await uplink.ctx.Base.create_thread_io(
                        uplink.mod_utils.action_scan_client_with_local_socket,
                        uplink, user
                        )

                    if not result:
                        continue
                   
                    fullname = f'{user.nickname}!{user.username}@{user.hostname}'
                    opened_ports = result['opened_ports']
                    closed_ports = result['closed_ports']
                    if opened_ports:
                        await p.send_priv_msg(
                            nick_from=service_id,
                            msg=f"[ {color_red}LOCAL_SCAN{nogc} ] {fullname} ({user.remote_ip}) : The Port(s) {opened_ports} are opened on this remote ip [{user.remote_ip}]",
                            channel=service_chanlog
                            )
                    if closed_ports:
                        await p.send_priv_msg(
                            nick_from=service_id,
                            msg=f"[ {color_red}LOCAL_SCAN{nogc} ] {fullname} ({user.remote_ip}) : The Port(s) {closed_ports} are closed on this remote ip [{user.remote_ip}]",
                            channel=service_chanlog
                            )
                    
                    await asyncio.sleep(1)

            for user_model in list_to_remove:
                uplink.Schemas.DB_LOCALSCAN_USERS.remove(user_model)

            await asyncio.sleep(1.5)
        except ValueError as ve:
            uplink.ctx.Logs.debug(f"The value to remove is not in the list. {ve}")
        except TimeoutError as te:
            uplink.ctx.Logs.debug(f"Timeout Error {te}")

async def coro_psutil_scan(uplink: 'Defender'):
    uplink.psutil_isRunning = True
    service_id = uplink.ctx.Config.SERVICE_ID
    service_chanlog = uplink.ctx.Config.SERVICE_CHANLOG
    color_red = uplink.ctx.Config.COLORS.red
    nogc = uplink.ctx.Config.COLORS.nogc
    p = uplink.ctx.Irc.Protocol

    while uplink.psutil_isRunning:
        try:
            list_to_remove:list = []
            for user in uplink.Schemas.DB_PSUTIL_USERS:
                result = await uplink.ctx.Base.create_thread_io(uplink.mod_utils.action_scan_client_with_psutil, uplink, user)
                list_to_remove.append(user)
                if not result:
                    continue
                
                fullname = f'{user.nickname}!{user.username}@{user.hostname}'
                await p.send_priv_msg(
                    nick_from=service_id,
                    msg=f"[ {color_red}PSUTIL_SCAN{nogc} ] {fullname} ({user.remote_ip}) is using ports {result}",
                    channel=service_chanlog
                )
                await asyncio.sleep(1)

            for user_model in list_to_remove:
                uplink.Schemas.DB_PSUTIL_USERS.remove(user_model)

            await asyncio.sleep(1.5)
        except ValueError as ve:
            uplink.ctx.Logs.debug(f"The value to remove is not in the list. {ve}")
        except TimeoutError as te:
            uplink.ctx.Logs.debug(f"Timeout Error {te}")

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
                    await p.send_set_mode('+l', channel_name=chan.name, params=len(chan.uids) + uplink.mod_config.autolimit_amount)
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
                await p.send_set_mode('+l', channel_name=chan.name, params=len(chan.uids) + uplink.mod_config.autolimit_amount)

        # Si le nouveau amount est différent de l'initial
        if init_amount != uplink.mod_config.autolimit_amount:
            init_amount = uplink.mod_config.autolimit_amount
            for chan in uplink.ctx.Channel.UID_CHANNEL_DB:
                await p.send_set_mode('+l', channel_name=chan.name, params=len(chan.uids) + uplink.mod_config.autolimit_amount)

        INIT = 0

        if uplink.autolimit_isRunning:
            await asyncio.sleep(uplink.mod_config.autolimit_interval)

    for chan in uplink.ctx.Channel.UID_CHANNEL_DB:
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
    timeout = uplink.mod_config.flood_timer
    await asyncio.sleep(timeout)

    if not uplink.ctx.Channel.is_valid_channel(channel):
        uplink.ctx.Logs.debug(f"Channel is not valid {channel}")
        return

    match action:
        case 'mode-m':
            # Action -m sur le salon
            await uplink.ctx.Irc.Protocol.send_set_mode('-m', channel_name=channel)
        case _:
            pass
