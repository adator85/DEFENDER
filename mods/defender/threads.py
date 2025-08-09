from typing import TYPE_CHECKING
from time import sleep

if TYPE_CHECKING:
    from mods.defender.mod_defender import Defender

def thread_apply_reputation_sanctions(uplink: 'Defender'):
    while uplink.reputationTimer_isRunning:
        uplink.Utils.action_apply_reputation_santions(uplink)
        sleep(5)

def thread_cloudfilt_scan(uplink: 'Defender'):

    while uplink.cloudfilt_isRunning:
        list_to_remove:list = []
        for user in uplink.Schemas.DB_CLOUDFILT_USERS:
            uplink.Utils.action_scan_client_with_cloudfilt(uplink, user)
            list_to_remove.append(user)
            sleep(1)

        for user_model in list_to_remove:
            uplink.Schemas.DB_CLOUDFILT_USERS.remove(user_model)

        sleep(1)

def thread_freeipapi_scan(uplink: 'Defender'):

    while uplink.freeipapi_isRunning:

        list_to_remove: list = []
        for user in uplink.Schemas.DB_FREEIPAPI_USERS:
            uplink.Utils.action_scan_client_with_freeipapi(uplink, user)
            list_to_remove.append(user)
            sleep(1)

        for user_model in list_to_remove:
            uplink.Schemas.DB_FREEIPAPI_USERS.remove(user_model)

        sleep(1)

def thread_abuseipdb_scan(uplink: 'Defender'):

    while uplink.abuseipdb_isRunning:

        list_to_remove: list = []
        for user in uplink.Schemas.DB_ABUSEIPDB_USERS:
            uplink.Utils.action_scan_client_with_abuseipdb(uplink, user)
            list_to_remove.append(user)
            sleep(1)

        for user_model in list_to_remove:
            uplink.Schemas.DB_ABUSEIPDB_USERS.remove(user_model)

        sleep(1)

def thread_local_scan(uplink: 'Defender'):

    while uplink.localscan_isRunning:
        list_to_remove:list = []
        for user in uplink.Schemas.DB_LOCALSCAN_USERS:
            uplink.Utils.action_scan_client_with_local_socket(uplink, user)
            list_to_remove.append(user)
            sleep(1)

        for user_model in list_to_remove:
            uplink.Schemas.DB_LOCALSCAN_USERS.remove(user_model)

        sleep(1)

def thread_psutil_scan(uplink: 'Defender'):

        while uplink.psutil_isRunning:

            list_to_remove:list = []
            for user in uplink.Schemas.DB_PSUTIL_USERS:
                uplink.Utils.action_scan_client_with_psutil(uplink, user)
                list_to_remove.append(user)
                sleep(1)

            for user_model in list_to_remove:
                uplink.Schemas.DB_PSUTIL_USERS.remove(user_model)

            sleep(1)

def thread_autolimit(uplink: 'Defender'):

    if uplink.ModConfig.autolimit == 0:
        uplink.Logs.debug("autolimit deactivated ... canceling the thread")
        return None

    while uplink.Irc.autolimit_started:
        sleep(0.2)

    uplink.Irc.autolimit_started = True
    init_amount = uplink.ModConfig.autolimit_amount
    p = uplink.Protocol
    INIT = 1

    # Copy Channels to a list of dict
    chanObj_copy: list[dict[str, int]] = [{"name": c.name, "uids_count": len(c.uids)} for c in uplink.Channel.UID_CHANNEL_DB]
    chan_list: list[str] = [c.name for c in uplink.Channel.UID_CHANNEL_DB]

    while uplink.autolimit_isRunning:

        if uplink.ModConfig.autolimit == 0:
            uplink.Logs.debug("autolimit deactivated ... stopping the current thread")
            break

        for chan in uplink.Channel.UID_CHANNEL_DB:
            for chan_copy in chanObj_copy:
                if chan_copy["name"] == chan.name and len(chan.uids) != chan_copy["uids_count"]:
                    p.send2socket(f":{uplink.Config.SERVICE_ID} MODE {chan.name} +l {len(chan.uids) + uplink.ModConfig.autolimit_amount}")
                    chan_copy["uids_count"] = len(chan.uids)

            if chan.name not in chan_list:
                chan_list.append(chan.name)
                chanObj_copy.append({"name": chan.name, "uids_count": 0})

        # Verifier si un salon a été vidé
        current_chan_in_list = [d.name for d in uplink.Channel.UID_CHANNEL_DB]
        for c in chan_list:
            if c not in current_chan_in_list:
                chan_list.remove(c)

        # Si c'est la premiere execution
        if INIT == 1:
            for chan in uplink.Channel.UID_CHANNEL_DB:
                p.send2socket(f":{uplink.Config.SERVICE_ID} MODE {chan.name} +l {len(chan.uids) + uplink.ModConfig.autolimit_amount}")

        # Si le nouveau amount est différent de l'initial
        if init_amount != uplink.ModConfig.autolimit_amount:
            init_amount = uplink.ModConfig.autolimit_amount
            for chan in uplink.Channel.UID_CHANNEL_DB:
                p.send2socket(f":{uplink.Config.SERVICE_ID} MODE {chan.name} +l {len(chan.uids) + uplink.ModConfig.autolimit_amount}")

        INIT = 0

        if uplink.autolimit_isRunning:
            sleep(uplink.ModConfig.autolimit_interval)

    for chan in uplink.Channel.UID_CHANNEL_DB:
        p.send2socket(f":{uplink.Config.SERVICE_ID} MODE {chan.name} -l")

    uplink.Irc.autolimit_started = False

    return None

def timer_release_mode_mute(uplink: 'Defender', action: str, channel: str):
    """DO NOT EXECUTE THIS FUNCTION WITHOUT THREADING

    Args:
        action (str): _description_
        channel (str): The related channel

    """
    service_id = uplink.Config.SERVICE_ID

    if not uplink.Channel.Is_Channel(channel):
        uplink.Logs.debug(f"Channel is not valid {channel}")
        return

    match action:
        case 'mode-m':
            # Action -m sur le salon
            uplink.Protocol.send2socket(f":{service_id} MODE {channel} -m")
        case _:
            pass
