from calendar import c
import socket
import psutil
import requests
import mods.defender.threads as dthreads
from json import loads
from re import match
from typing import TYPE_CHECKING, Optional
from mods.defender.schemas import FloodUser

if TYPE_CHECKING:
    from core.definition import MUser
    from mods.defender.mod_defender import Defender

def handle_on_reputation(uplink: 'Defender', srvmsg: list[str]):
    """Handle reputation server message
    >>> srvmsg = [':001', 'REPUTATION', '128.128.128.128', '0']
    >>> srvmsg = [':001', 'REPUTATION', '128.128.128.128', '*0']
    Args:
        irc_instance (Irc): The Irc instance
        srvmsg (list[str]): The Server MSG
    """
    ip = srvmsg[2]
    score = srvmsg[3]

    if str(ip).find('*') != -1:
        # If the reputation changed, we do not need to scan the IP
        return

    # Possibilité de déclancher les bans a ce niveau.
    if not uplink.Base.is_valid_ip(ip):
        return

def handle_on_mode(uplink: 'Defender', srvmsg: list[str]):
    """_summary_
    >>> srvmsg = ['@unrealircd.org/...', ':001C0MF01', 'MODE', '#services', '+l', '1']
    >>> srvmsg = ['...', ':001XSCU0Q', 'MODE', '#jail', '+b', '~security-group:unknown-users']
    Args:
        irc_instance (Irc): The Irc instance
        srvmsg (list[str]): The Server MSG
        confmodel (ModConfModel): The Module Configuration
    """
    irc = uplink.Irc
    gconfig = uplink.Config
    p = uplink.Protocol
    confmodel = uplink.ModConfig

    channel = str(srvmsg[3])
    mode = str(srvmsg[4])
    group_to_check = str(srvmsg[5:])
    group_to_unban = '~security-group:unknown-users'

    if confmodel.autolimit == 1:
        if mode == '+l' or mode == '-l':
            chan = irc.Channel.get_Channel(channel)
            p.send2socket(f":{gconfig.SERVICE_ID} MODE {chan.name} +l {len(chan.uids) + confmodel.autolimit_amount}")

    if gconfig.SALON_JAIL == channel:
        if mode == '+b' and group_to_unban in group_to_check:
            p.send2socket(f":{gconfig.SERVICE_ID} MODE {gconfig.SALON_JAIL} -b ~security-group:unknown-users")
            p.send2socket(f":{gconfig.SERVICE_ID} MODE {gconfig.SALON_JAIL} -eee ~security-group:webirc-users ~security-group:known-users ~security-group:websocket-users")

def handle_on_privmsg(uplink: 'Defender', srvmsg: list[str]):
    # ['@mtag....',':python', 'PRIVMSG', '#defender', ':zefzefzregreg', 'regg', 'aerg']
    action_on_flood(uplink, srvmsg)
    return None

def handle_on_sjoin(uplink: 'Defender', srvmsg: list[str]):
    """If Joining a new channel, it applies group bans.

    >>> srvmsg = ['@msgid..', ':001', 'SJOIN', '1702138958', '#welcome', ':0015L1AHL']

    Args:
        irc_instance (Irc): The Irc instance
        srvmsg (list[str]): The Server MSG
        confmodel (ModConfModel): The Module Configuration
    """
    irc = uplink.Irc
    p = irc.Protocol
    gconfig = uplink.Config
    confmodel = uplink.ModConfig

    parsed_chan = srvmsg[4] if irc.Channel.Is_Channel(srvmsg[4]) else None
    parsed_UID = irc.User.clean_uid(srvmsg[5])

    if parsed_chan is None or parsed_UID is None:
        return

    if confmodel.reputation == 1:
        get_reputation = irc.Reputation.get_Reputation(parsed_UID)

        if parsed_chan != gconfig.SALON_JAIL:
            p.send2socket(f":{gconfig.SERVICE_ID} MODE {parsed_chan} +b ~security-group:unknown-users")
            p.send2socket(f":{gconfig.SERVICE_ID} MODE {parsed_chan} +eee ~security-group:webirc-users ~security-group:known-users ~security-group:websocket-users")

        if get_reputation is not None:
            isWebirc = get_reputation.isWebirc

            if not isWebirc:
                if parsed_chan != gconfig.SALON_JAIL:
                    p.send_sapart(nick_to_sapart=get_reputation.nickname, channel_name=parsed_chan)

            if confmodel.reputation_ban_all_chan == 1 and not isWebirc:
                if parsed_chan != gconfig.SALON_JAIL:
                    p.send2socket(f":{gconfig.SERVICE_ID} MODE {parsed_chan} +b {get_reputation.nickname}!*@*")
                    p.send2socket(f":{gconfig.SERVICE_ID} KICK {parsed_chan} {get_reputation.nickname}")

            irc.Logs.debug(f'SJOIN parsed_uid : {parsed_UID}')

def handle_on_slog(uplink: 'Defender', srvmsg: list[str]):
    """Handling SLOG messages
    >>> srvmsg = ['@unrealircd...', ':001', 'SLOG', 'info', 'blacklist', 'BLACKLIST_HIT', ':[Blacklist]', 'IP', '162.x.x.x', 'matches', 'blacklist', 'dronebl', '(dnsbl.dronebl.org/reply=6)']
    Args:
        irc_instance (Irc): The Irc instance
        srvmsg (list[str]): The Server MSG
        confmodel (ModConfModel): The Module Configuration
    """
    ['@unrealircd...', ':001', 'SLOG', 'info', 'blacklist', 'BLACKLIST_HIT', ':[Blacklist]', 'IP', '162.x.x.x', 'matches', 'blacklist', 'dronebl', '(dnsbl.dronebl.org/reply=6)']

    if not uplink.Base.is_valid_ip(srvmsg[8]):
        return None

    # if self.ModConfig.local_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
    #     self.localscan_remote_ip.append(cmd[7])

    # if self.ModConfig.psutil_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
    #     self.psutil_remote_ip.append(cmd[7])

    # if self.ModConfig.abuseipdb_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
    #     self.abuseipdb_remote_ip.append(cmd[7])

    # if self.ModConfig.freeipapi_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
    #     self.freeipapi_remote_ip.append(cmd[7])

    # if self.ModConfig.cloudfilt_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
    #     self.cloudfilt_remote_ip.append(cmd[7])

    return None

def handle_on_nick(uplink: 'Defender', srvmsg: list[str]):
    """_summary_
    >>> srvmsg = ['@unrealircd.org...', ':001MZQ0RB', 'NICK', 'newnickname', '1754663712']
    Args:
        irc_instance (Irc): The Irc instance
        srvmsg (list[str]): The Server MSG
        confmodel (ModConfModel): The Module Configuration
    """
    uid = uplink.User.clean_uid(str(srvmsg[1]))
    p = uplink.Protocol
    confmodel = uplink.ModConfig

    get_reputation = uplink.Reputation.get_Reputation(uid)
    jail_salon = uplink.Config.SALON_JAIL
    service_id = uplink.Config.SERVICE_ID

    if get_reputation is None:
        uplink.Logs.debug(f'This UID: {uid} is not listed in the reputation dataclass')
        return None

    # Update the new nickname
    oldnick = get_reputation.nickname
    newnickname = srvmsg[3]
    get_reputation.nickname = newnickname

    # If ban in all channel is ON then unban old nickname an ban the new nickname
    if confmodel.reputation_ban_all_chan == 1:
        for chan in uplink.Channel.UID_CHANNEL_DB:
            if chan.name != jail_salon:
                p.send2socket(f":{service_id} MODE {chan.name} -b {oldnick}!*@*")
                p.send2socket(f":{service_id} MODE {chan.name} +b {newnickname}!*@*")

def handle_on_quit(uplink: 'Defender', srvmsg: list[str]):
    """_summary_
    >>> srvmsg = ['@unrealircd.org...', ':001MZQ0RB', 'QUIT', ':Quit:', 'quit message']
    Args:
        uplink (Irc): The Defender Module instance
        srvmsg (list[str]): The Server MSG
    """
    p = uplink.Protocol
    confmodel = uplink.ModConfig

    ban_all_chan = uplink.Base.int_if_possible(confmodel.reputation_ban_all_chan)
    final_UID = uplink.User.clean_uid(str(srvmsg[1]))
    jail_salon = uplink.Config.SALON_JAIL
    service_id = uplink.Config.SERVICE_ID
    get_user_reputation = uplink.Reputation.get_Reputation(final_UID)

    if get_user_reputation is not None:
        final_nickname = get_user_reputation.nickname
        for chan in uplink.Channel.UID_CHANNEL_DB:
            if chan.name != jail_salon and ban_all_chan == 1:
                p.send2socket(f":{service_id} MODE {chan.name} -b {final_nickname}!*@*")
                uplink.Logs.debug(f"Mode -b {final_nickname} on channel {chan.name}")

        uplink.Reputation.delete(final_UID)
        uplink.Logs.debug(f"Client {get_user_reputation.nickname} has been removed from Reputation local DB")

def handle_on_uid(uplink: 'Defender', srvmsg: list[str]):
    """_summary_
    >>> ['@s2s-md...', ':001', 'UID', 'nickname', '0', '1754675249', '...', '125-168-141-239.hostname.net', '001BAPN8M', 
    '0', '+iwx', '*', '32001BBE.25ACEFE7.429FE90D.IP', 'ZA2ic7w==', ':realname']

    Args:
        uplink (Defender): The Defender instance
        srvmsg (list[str]): The Server MSG
    """
    gconfig = uplink.Config
    irc = uplink.Irc
    confmodel = uplink.ModConfig

    # If Init then do nothing
    if gconfig.DEFENDER_INIT == 1:
        return None

    # Get User information
    _User = irc.User.get_User(str(srvmsg[8]))

    if _User is None:
        irc.Logs.warning(f'This UID: [{srvmsg[8]}] is not available please check why')
        return

    # If user is not service or IrcOp then scan them
    if not match(r'^.*[S|o?].*$', _User.umodes):
        uplink.Schemas.DB_ABUSEIPDB_USERS.append(_User) if confmodel.abuseipdb_scan == 1 and _User.remote_ip not in gconfig.WHITELISTED_IP else None
        uplink.Schemas.DB_FREEIPAPI_USERS.append(_User) if confmodel.freeipapi_scan == 1 and _User.remote_ip not in gconfig.WHITELISTED_IP else None
        uplink.Schemas.DB_CLOUDFILT_USERS.append(_User) if confmodel.cloudfilt_scan == 1 and _User.remote_ip not in gconfig.WHITELISTED_IP else None
        uplink.Schemas.DB_PSUTIL_USERS.append(_User) if confmodel.psutil_scan == 1 and _User.remote_ip not in gconfig.WHITELISTED_IP else None
        uplink.Schemas.DB_LOCALSCAN_USERS.append(_User) if confmodel.local_scan == 1 and _User.remote_ip not in gconfig.WHITELISTED_IP else None

    reputation_flag = confmodel.reputation
    reputation_seuil = confmodel.reputation_seuil

    if gconfig.DEFENDER_INIT == 0:
        # Si le user n'es pas un service ni un IrcOP
        if not match(r'^.*[S|o?].*$', _User.umodes):
            if reputation_flag == 1 and _User.score_connexion <= reputation_seuil:
                # currentDateTime = self.Base.get_datetime()
                irc.Reputation.insert(
                    irc.Loader.Definition.MReputation(
                        **_User.to_dict(),
                        secret_code=irc.Base.get_random(8)
                    )
                )
                if irc.Reputation.is_exist(_User.uid):
                    if reputation_flag == 1 and _User.score_connexion <= reputation_seuil:
                        action_add_reputation_sanctions(uplink, _User.uid)
                        irc.Logs.info(f'[REPUTATION] Reputation system ON (Nickname: {_User.nickname}, uid: {_User.uid})')

####################
# ACTION FUNCTIONS #
####################

def action_on_flood(uplink: 'Defender', srvmsg: list[str]):

    confmodel = uplink.ModConfig
    if confmodel.flood == 0:
            return None

    irc = uplink.Irc
    gconfig = uplink.Config
    p = uplink.Protocol
    flood_users = uplink.Schemas.DB_FLOOD_USERS

    user_trigger = str(srvmsg[1]).replace(':','')
    channel = srvmsg[3]
    User = irc.User.get_User(user_trigger)

    if User is None or not irc.Channel.Is_Channel(channel_to_check=channel):
        return

    flood_time = confmodel.flood_time
    flood_message = confmodel.flood_message
    flood_timer = confmodel.flood_timer
    service_id = gconfig.SERVICE_ID
    dnickname = gconfig.SERVICE_NICKNAME
    color_red = gconfig.COLORS.red
    color_bold = gconfig.COLORS.bold

    get_detected_uid = User.uid
    get_detected_nickname = User.nickname
    unixtime = irc.Base.get_unixtime()
    get_diff_secondes = 0

    def get_flood_user(uid: str) -> Optional[FloodUser]:
        for flood_user in flood_users:
            if flood_user.uid == uid:
                return flood_user

    fu = get_flood_user(get_detected_uid)
    if fu is None:
        fu = FloodUser(get_detected_uid, 0, unixtime)
        flood_users.append(fu)

    fu.nbr_msg += 1

    get_diff_secondes = unixtime - fu.first_msg_time
    if get_diff_secondes > flood_time:
        fu.first_msg_time = unixtime
        fu.nbr_msg = 0
        get_diff_secondes = unixtime - fu.first_msg_time
    elif fu.nbr_msg > flood_message:
        irc.Logs.info('system de flood detecté')
        p.send_priv_msg(
            nick_from=dnickname,
            msg=f"{color_red} {color_bold} Flood detected. Apply the +m mode (Ô_o)",
            channel=channel
        )
        p.send2socket(f":{service_id} MODE {channel} +m")
        irc.Logs.info(f'FLOOD Détecté sur {get_detected_nickname} mode +m appliqué sur le salon {channel}')
        fu.nbr_msg = 0
        fu.first_msg_time = unixtime
        irc.Base.create_timer(flood_timer, dthreads.timer_release_mode_mute, (uplink, 'mode-m', channel))

def action_add_reputation_sanctions(uplink: 'Defender', jailed_uid: str ):

    irc = uplink.Irc
    gconfig = uplink.Config
    p = uplink.Protocol
    confmodel = uplink.ModConfig

    get_reputation = irc.Reputation.get_Reputation(jailed_uid)

    if get_reputation is None:
        irc.Logs.warning(f'UID {jailed_uid} has not been found')
        return

    salon_logs = gconfig.SERVICE_CHANLOG
    salon_jail = gconfig.SALON_JAIL

    code = get_reputation.secret_code
    jailed_nickname = get_reputation.nickname
    jailed_score = get_reputation.score_connexion

    color_red = gconfig.COLORS.red
    color_black = gconfig.COLORS.black
    color_bold = gconfig.COLORS.bold
    nogc = gconfig.COLORS.nogc
    service_id = gconfig.SERVICE_ID
    service_prefix = gconfig.SERVICE_PREFIX
    reputation_ban_all_chan = confmodel.reputation_ban_all_chan

    if not get_reputation.isWebirc:
        # Si le user ne vient pas de webIrc
        p.send_sajoin(nick_to_sajoin=jailed_nickname, channel_name=salon_jail)
        p.send_priv_msg(nick_from=gconfig.SERVICE_NICKNAME,
            msg=f" [{color_red} REPUTATION {nogc}] : Connexion de {jailed_nickname} ({jailed_score}) ==> {salon_jail}",
            channel=salon_logs
            )
        p.send_notice(
                nick_from=gconfig.SERVICE_NICKNAME, 
                nick_to=jailed_nickname,
                msg=f"[{color_red} {jailed_nickname} {color_black}] : Merci de tapez la commande suivante {color_bold}{service_prefix}code {code}{color_bold}"
            )
        if reputation_ban_all_chan == 1:
            for chan in irc.Channel.UID_CHANNEL_DB:
                if chan.name != salon_jail:
                    p.send2socket(f":{service_id} MODE {chan.name} +b {jailed_nickname}!*@*")
                    p.send2socket(f":{service_id} KICK {chan.name} {jailed_nickname}")

        irc.Logs.info(f"[REPUTATION] {jailed_nickname} jailed (UID: {jailed_uid}, score: {jailed_score})")
    else:
        irc.Logs.info(f"[REPUTATION] {jailed_nickname} skipped (trusted or WebIRC)")
        irc.Reputation.delete(jailed_uid)

def action_apply_reputation_santions(uplink: 'Defender') -> None:

    irc = uplink.Irc
    gconfig = uplink.Config
    p = uplink.Protocol
    confmodel = uplink.ModConfig

    reputation_flag = confmodel.reputation
    reputation_timer = confmodel.reputation_timer
    reputation_seuil = confmodel.reputation_seuil
    ban_all_chan = confmodel.reputation_ban_all_chan
    service_id = gconfig.SERVICE_ID
    dchanlog = gconfig.SERVICE_CHANLOG
    color_red = gconfig.COLORS.red
    nogc = gconfig.COLORS.nogc
    salon_jail = gconfig.SALON_JAIL

    if reputation_flag == 0:
        return None
    elif reputation_timer == 0:
        return None

    uid_to_clean = []

    for user in irc.Reputation.UID_REPUTATION_DB:
        if not user.isWebirc: # Si il ne vient pas de WebIRC
            if irc.User.get_user_uptime_in_minutes(user.uid) >= reputation_timer and int(user.score_connexion) <= int(reputation_seuil):
                p.send_priv_msg(
                    nick_from=service_id,
                    msg=f"[{color_red} REPUTATION {nogc}] : Action sur {user.nickname} aprés {str(reputation_timer)} minutes d'inactivité",
                    channel=dchanlog
                    )
                p.send2socket(f":{service_id} KILL {user.nickname} After {str(reputation_timer)} minutes of inactivity you should reconnect and type the password code")
                p.send2socket(f":{gconfig.SERVEUR_LINK} REPUTATION {user.remote_ip} 0")

                irc.Logs.info(f"Nickname: {user.nickname} KILLED after {str(reputation_timer)} minutes of inactivity")
                uid_to_clean.append(user.uid)

    for uid in uid_to_clean:
        # Suppression des éléments dans {UID_DB} et {REPUTATION_DB}
        for chan in irc.Channel.UID_CHANNEL_DB:
            if chan.name != salon_jail and ban_all_chan == 1:
                get_user_reputation = irc.Reputation.get_Reputation(uid)
                p.send2socket(f":{service_id} MODE {chan.name} -b {get_user_reputation.nickname}!*@*")

        # Lorsqu'un utilisateur quitte, il doit être supprimé de {UID_DB}.
        irc.Channel.delete_user_from_all_channel(uid)
        irc.Reputation.delete(uid)
        irc.User.delete(uid)

def action_scan_client_with_cloudfilt(uplink: 'Defender', user_model: 'MUser') -> Optional[dict[str, str]]:
    """Analyse l'ip avec cloudfilt
        Cette methode devra etre lancer toujours via un thread ou un timer.
    Args:
        uplink (Defender): Defender Instance

    Returns:
        dict[str, any] | None: les informations du provider
        keys : 'countryCode', 'isProxy'
    """

    remote_ip = user_model.remote_ip
    username = user_model.username
    hostname = user_model.hostname
    nickname = user_model.nickname
    p = uplink.Protocol

    if remote_ip in uplink.Config.WHITELISTED_IP:
        return None
    if uplink.ModConfig.cloudfilt_scan == 0:
        return None
    if uplink.cloudfilt_key == '':
        return None

    service_id = uplink.Config.SERVICE_ID
    service_chanlog = uplink.Config.SERVICE_CHANLOG
    color_red = uplink.Config.COLORS.red
    nogc = uplink.Config.COLORS.nogc

    url = "https://developers18334.cloudfilt.com/"

    data = {
        'ip': remote_ip,
        'key': uplink.cloudfilt_key
    }

    response = requests.post(url=url, data=data)
    # Formatted output
    decoded_response: dict = loads(response.text)
    status_code = response.status_code
    if status_code != 200:
        uplink.Logs.warning(f'Error connecting to cloudfilt API | Code: {str(status_code)}')
        return

    result = {
        'countryiso': decoded_response.get('countryiso', None),
        'listed': decoded_response.get('listed', None),
        'listed_by': decoded_response.get('listed_by', None),
        'host': decoded_response.get('host', None)
    }

    # pseudo!ident@host
    fullname = f'{nickname}!{username}@{hostname}'

    p.send_priv_msg(
        nick_from=service_id,
        msg=f"[ {color_red}CLOUDFILT_SCAN{nogc} ] : Connexion de {fullname} ({remote_ip}) ==> Host: {str(result['host'])} | country: {str(result['countryiso'])} | listed: {str(result['listed'])} | listed by : {str(result['listed_by'])}",
        channel=service_chanlog)
    
    uplink.Logs.debug(f"[CLOUDFILT SCAN] ({fullname}) connected from ({result['countryiso']}), Listed: {result['listed']}, by: {result['listed_by']}")    

    if result['listed']:
        p.send2socket(f":{service_id} GLINE +*@{remote_ip} {uplink.Config.GLINE_DURATION} Your connexion is listed as dangerous {str(result['listed'])} {str(result['listed_by'])} - detected by cloudfilt")
        uplink.Logs.debug(f"[CLOUDFILT SCAN GLINE] Dangerous connection ({fullname}) from ({result['countryiso']}) Listed: {result['listed']}, by: {result['listed_by']}")

    response.close()

    return result

def action_scan_client_with_freeipapi(uplink: 'Defender', user_model: 'MUser') -> Optional[dict[str, str]]:
    """Analyse l'ip avec Freeipapi
        Cette methode devra etre lancer toujours via un thread ou un timer.
    Args:
        uplink (Defender): The Defender object Instance

    Returns:
        dict[str, any] | None: les informations du provider
        keys : 'countryCode', 'isProxy'
    """
    p = uplink.Protocol
    remote_ip = user_model.remote_ip
    username = user_model.username
    hostname = user_model.hostname
    nickname = user_model.nickname

    if remote_ip in uplink.Config.WHITELISTED_IP:
        return None
    if uplink.ModConfig.freeipapi_scan == 0:
        return None

    service_id = uplink.Config.SERVICE_ID
    service_chanlog = uplink.Config.SERVICE_CHANLOG
    color_red = uplink.Config.COLORS.red
    nogc = uplink.Config.COLORS.nogc

    url = f'https://freeipapi.com/api/json/{remote_ip}'

    headers = {
        'Accept': 'application/json',
    }

    response = requests.request(method='GET', url=url, headers=headers, timeout=uplink.timeout)

    # Formatted output
    decoded_response: dict = loads(response.text)

    status_code = response.status_code
    if status_code == 429:
        uplink.Logs.warning('Too Many Requests - The rate limit for the API has been exceeded.')
        return None
    elif status_code != 200:
        uplink.Logs.warning(f'status code = {str(status_code)}')
        return None

    result = {
        'countryCode': decoded_response.get('countryCode', None),
        'isProxy': decoded_response.get('isProxy', None)
    }

    # pseudo!ident@host
    fullname = f'{nickname}!{username}@{hostname}'

    p.send_priv_msg(
        nick_from=service_id,
        msg=f"[ {color_red}FREEIPAPI_SCAN{nogc} ] : Connexion de {fullname} ({remote_ip}) ==> Proxy: {str(result['isProxy'])} | Country : {str(result['countryCode'])}",
        channel=service_chanlog)    
    uplink.Logs.debug(f"[FREEIPAPI SCAN] ({fullname}) connected from ({result['countryCode']}), Proxy: {result['isProxy']}") 

    if result['isProxy']:
        p.send2socket(f":{service_id} GLINE +*@{remote_ip} {uplink.Config.GLINE_DURATION} This server do not allow proxy connexions {str(result['isProxy'])} - detected by freeipapi")
        uplink.Logs.debug(f"[FREEIPAPI SCAN GLINE] Server do not allow proxy connexions {result['isProxy']}")

    response.close()

    return result

def action_scan_client_with_abuseipdb(uplink: 'Defender', user_model: 'MUser') -> Optional[dict[str, str]]:
    """Analyse l'ip avec AbuseIpDB
        Cette methode devra etre lancer toujours via un thread ou un timer.
    Args:
        uplink (Defender): Defender instance object
        user_model (MUser): l'objet User qui contient l'ip

    Returns:
        dict[str, str] | None: les informations du provider
    """
    p = uplink.Protocol
    remote_ip = user_model.remote_ip
    username = user_model.username
    hostname = user_model.hostname
    nickname = user_model.nickname

    if remote_ip in uplink.Config.WHITELISTED_IP:
        return None
    if uplink.ModConfig.abuseipdb_scan == 0:
        return None

    if uplink.abuseipdb_key == '':
        return None

    url = 'https://api.abuseipdb.com/api/v2/check'
    querystring = {
        'ipAddress': remote_ip,
        'maxAgeInDays': '90'
    }

    headers = {
        'Accept': 'application/json',
        'Key': uplink.abuseipdb_key
    }

    response = requests.request(method='GET', url=url, headers=headers, params=querystring, timeout=uplink.timeout)

    # Formatted output
    decoded_response: dict[str, dict] = loads(response.text)

    if 'data' not in decoded_response:
        return None

    result = {
        'score': decoded_response.get('data', {}).get('abuseConfidenceScore', 0),
        'country': decoded_response.get('data', {}).get('countryCode', None),
        'isTor': decoded_response.get('data', {}).get('isTor', None),
        'totalReports': decoded_response.get('data', {}).get('totalReports', 0)
    }

    service_id = uplink.Config.SERVICE_ID
    service_chanlog = uplink.Config.SERVICE_CHANLOG
    color_red = uplink.Config.COLORS.red
    nogc = uplink.Config.COLORS.nogc

    # pseudo!ident@host
    fullname = f'{nickname}!{username}@{hostname}'

    p.send_priv_msg(
        nick_from=service_id,
        msg=f"[ {color_red}ABUSEIPDB_SCAN{nogc} ] : Connexion de {fullname} ({remote_ip}) ==> Score: {str(result['score'])} | Country : {result['country']} | Tor : {str(result['isTor'])} | Total Reports : {str(result['totalReports'])}",
        channel=service_chanlog
        )
    uplink.Logs.debug(f"[ABUSEIPDB SCAN] ({fullname}) connected from ({result['country']}), Score: {result['score']}, Tor: {result['isTor']}")

    if result['isTor']:
        p.send2socket(f":{service_id} GLINE +*@{remote_ip} {uplink.Config.GLINE_DURATION} This server do not allow Tor connexions {str(result['isTor'])} - Detected by Abuseipdb")
        uplink.Logs.debug(f"[ABUSEIPDB SCAN GLINE] Server do not allow Tor connections Tor: {result['isTor']}, Score: {result['score']}")
    elif result['score'] >= 95:
        p.send2socket(f":{service_id} GLINE +*@{remote_ip} {uplink.Config.GLINE_DURATION} You were banned from this server because your abuse score is = {str(result['score'])} - Detected by Abuseipdb")
        uplink.Logs.debug(f"[ABUSEIPDB SCAN GLINE] Server do not high risk connections Country: {result['country']}, Score: {result['score']}")

    response.close()

    return result

def action_scan_client_with_local_socket(uplink: 'Defender', user_model: 'MUser'):
    """local_scan

    Args:
        uplink (Defender): Defender instance object
        user_model (MUser): l'objet User qui contient l'ip
    """
    p = uplink.Protocol
    remote_ip = user_model.remote_ip
    username = user_model.username
    hostname = user_model.hostname
    nickname = user_model.nickname
    fullname = f'{nickname}!{username}@{hostname}'

    if remote_ip in uplink.Config.WHITELISTED_IP:
        return None

    for port in uplink.Config.PORTS_TO_SCAN:
        try:
            newSocket = ''
            newSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM or socket.SOCK_NONBLOCK)
            newSocket.settimeout(0.5)

            connection = (remote_ip, uplink.Base.int_if_possible(port))
            newSocket.connect(connection)

            p.send_priv_msg(
                nick_from=uplink.Config.SERVICE_NICKNAME,
                msg=f"[ {uplink.Config.COLORS.red}PROXY_SCAN{uplink.Config.COLORS.nogc} ] {fullname} ({remote_ip}) :     Port [{str(port)}] ouvert sur l'adresse ip [{remote_ip}]",
                channel=uplink.Config.SERVICE_CHANLOG
                )
            # print(f"=======> Le port {str(port)} est ouvert !!")
            uplink.Base.running_sockets.append(newSocket)
            # print(newSocket)
            newSocket.shutdown(socket.SHUT_RDWR)
            newSocket.close()

        except (socket.timeout, ConnectionRefusedError):
            uplink.Logs.info(f"Le port {remote_ip}:{str(port)} est fermé")
        except AttributeError as ae:
            uplink.Logs.warning(f"AttributeError ({remote_ip}): {ae}")
        except socket.gaierror as err:
            uplink.Logs.warning(f"Address Info Error ({remote_ip}): {err}")
        finally:
            # newSocket.shutdown(socket.SHUT_RDWR)
            newSocket.close()
            uplink.Logs.info('=======> Fermeture de la socket')

def action_scan_client_with_psutil(uplink: 'Defender', user_model: 'MUser') -> list[int]:
    """psutil_scan for Linux (should be run on the same location as the unrealircd server)

    Args:
        userModel (UserModel): The User Model Object

    Returns:
        list[int]: list of ports
    """
    p = uplink.Protocol
    remote_ip = user_model.remote_ip
    username = user_model.username
    hostname = user_model.hostname
    nickname = user_model.nickname

    if remote_ip in uplink.Config.WHITELISTED_IP:
        return None

    try:
        connections = psutil.net_connections(kind='inet')
        fullname = f'{nickname}!{username}@{hostname}'

        matching_ports = [conn.raddr.port for conn in connections if conn.raddr and conn.raddr.ip == remote_ip]
        uplink.Logs.info(f"Connexion of {fullname} ({remote_ip}) using ports : {str(matching_ports)}")

        if matching_ports:
            p.send_priv_msg(
                    nick_from=uplink.Config.SERVICE_NICKNAME,
                    msg=f"[ {uplink.Config.COLORS.red}PSUTIL_SCAN{uplink.Config.COLORS.black} ] {fullname} ({remote_ip}) : is using ports {matching_ports}",
                    channel=uplink.Config.SERVICE_CHANLOG
                )

        return matching_ports

    except psutil.AccessDenied as ad:
        uplink.Logs.critical(f'psutil_scan: Permission error: {ad}')