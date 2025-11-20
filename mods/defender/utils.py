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
    from core.loader import Loader
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
    if not uplink.ctx.Base.is_valid_ip(ip):
        return

async def handle_on_mode(uplink: 'Defender', srvmsg: list[str]):
    """_summary_
    >>> srvmsg = ['@unrealircd.org/...', ':001C0MF01', 'MODE', '#services', '+l', '1']
    >>> srvmsg = ['...', ':001XSCU0Q', 'MODE', '#jail', '+b', '~security-group:unknown-users']
    Args:
        irc_instance (Irc): The Irc instance
        srvmsg (list[str]): The Server MSG
        confmodel (ModConfModel): The Module Configuration
    """
    irc = uplink.ctx.Irc
    gconfig = uplink.ctx.Config
    p = irc.Protocol
    confmodel = uplink.mod_config

    channel = str(srvmsg[3])
    mode = str(srvmsg[4])
    group_to_check = str(srvmsg[5:])
    group_to_unban = '~security-group:unknown-users'

    if confmodel.autolimit == 1:
        if mode == '+l' or mode == '-l':
            chan = uplink.ctx.Channel.get_channel(channel)
            await p.send2socket(f":{gconfig.SERVICE_ID} MODE {chan.name} +l {len(chan.uids) + confmodel.autolimit_amount}")

    if gconfig.SALON_JAIL == channel:
        if mode == '+b' and group_to_unban in group_to_check:
            await p.send2socket(f":{gconfig.SERVICE_ID} MODE {gconfig.SALON_JAIL} -b ~security-group:unknown-users")
            await p.send2socket(f":{gconfig.SERVICE_ID} MODE {gconfig.SALON_JAIL} -eee ~security-group:webirc-users ~security-group:known-users ~security-group:websocket-users")

async def handle_on_privmsg(uplink: 'Defender', srvmsg: list[str]):
    # ['@mtag....',':python', 'PRIVMSG', '#defender', ':zefzefzregreg', 'regg', 'aerg']

    sender, reciever, channel, message = uplink.ctx.Irc.Protocol.parse_privmsg(srvmsg)
    if uplink.mod_config.sentinel == 1 and channel.name != uplink.ctx.Config.SERVICE_CHANLOG:
        await uplink.ctx.Irc.Protocol.send_priv_msg(uplink.ctx.Config.SERVICE_NICKNAME, f"{sender.nickname} say on {channel.name}: {' '.join(message)}", uplink.ctx.Config.SERVICE_CHANLOG)

    await action_on_flood(uplink, srvmsg)
    return None

async def handle_on_sjoin(uplink: 'Defender', srvmsg: list[str]):
    """If Joining a new channel, it applies group bans.

    >>> srvmsg = ['@msgid..', ':001', 'SJOIN', '1702138958', '#welcome', ':0015L1AHL']

    Args:
        irc_instance (Irc): The Irc instance
        srvmsg (list[str]): The Server MSG
        confmodel (ModConfModel): The Module Configuration
    """
    irc = uplink.ctx.Irc
    p = irc.Protocol
    gconfig = uplink.ctx.Config
    confmodel = uplink.mod_config

    parsed_chan = srvmsg[4] if uplink.ctx.Channel.is_valid_channel(srvmsg[4]) else None
    parsed_UID = uplink.ctx.Utils.clean_uid(srvmsg[5])

    if parsed_chan is None or parsed_UID is None:
        return

    if confmodel.reputation == 1:
        get_reputation = uplink.ctx.Reputation.get_reputation(parsed_UID)

        if parsed_chan != gconfig.SALON_JAIL:
            await p.send2socket(f":{gconfig.SERVICE_ID} MODE {parsed_chan} +b ~security-group:unknown-users")
            await p.send2socket(f":{gconfig.SERVICE_ID} MODE {parsed_chan} +eee ~security-group:webirc-users ~security-group:known-users ~security-group:websocket-users")

        if get_reputation is not None:
            isWebirc = get_reputation.isWebirc

            if not isWebirc:
                if parsed_chan != gconfig.SALON_JAIL:
                    await p.send_sapart(nick_to_sapart=get_reputation.nickname, channel_name=parsed_chan)

            if confmodel.reputation_ban_all_chan == 1 and not isWebirc:
                if parsed_chan != gconfig.SALON_JAIL:
                    await p.send2socket(f":{gconfig.SERVICE_ID} MODE {parsed_chan} +b {get_reputation.nickname}!*@*")
                    await p.send2socket(f":{gconfig.SERVICE_ID} KICK {parsed_chan} {get_reputation.nickname}")

            uplink.ctx.Logs.debug(f'SJOIN parsed_uid : {parsed_UID}')

def handle_on_slog(uplink: 'Defender', srvmsg: list[str]):
    """Handling SLOG messages
    >>> srvmsg = ['@unrealircd...', ':001', 'SLOG', 'info', 'blacklist', 'BLACKLIST_HIT', ':[Blacklist]', 'IP', '162.x.x.x', 'matches', 'blacklist', 'dronebl', '(dnsbl.dronebl.org/reply=6)']
    Args:
        irc_instance (Irc): The Irc instance
        srvmsg (list[str]): The Server MSG
        confmodel (ModConfModel): The Module Configuration
    """
    ['@unrealircd...', ':001', 'SLOG', 'info', 'blacklist', 'BLACKLIST_HIT', ':[Blacklist]', 'IP', '162.x.x.x', 'matches', 'blacklist', 'dronebl', '(dnsbl.dronebl.org/reply=6)']

    if not uplink.ctx.Base.is_valid_ip(srvmsg[8]):
        return None

    # if self.mod_config.local_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
    #     self.localscan_remote_ip.append(cmd[7])

    # if self.mod_config.psutil_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
    #     self.psutil_remote_ip.append(cmd[7])

    # if self.mod_config.abuseipdb_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
    #     self.abuseipdb_remote_ip.append(cmd[7])

    # if self.mod_config.freeipapi_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
    #     self.freeipapi_remote_ip.append(cmd[7])

    # if self.mod_config.cloudfilt_scan == 1 and not cmd[7] in self.Config.WHITELISTED_IP:
    #     self.cloudfilt_remote_ip.append(cmd[7])

    return None

async def handle_on_nick(uplink: 'Defender', srvmsg: list[str]):
    """Handle nickname changes.
    >>> srvmsg = ['@unrealircd.org...', ':001MZQ0RB', 'NICK', 'newnickname', '1754663712']
    >>> [':97KAAAAAC', 'NICK', 'testinspir', '1757360740']
    Args:
        irc_instance (Irc): The Irc instance
        srvmsg (list[str]): The Server MSG
        confmodel (ModConfModel): The Module Configuration
    """
    p = uplink.ctx.Irc.Protocol
    u, new_nickname, timestamp = p.parse_nick(srvmsg)

    if u is None:
        uplink.ctx.Logs.error(f"[USER OBJ ERROR {timestamp}] - {srvmsg}")
        return None

    uid = u.uid
    confmodel = uplink.mod_config

    get_reputation = uplink.ctx.Reputation.get_reputation(uid)
    jail_salon = uplink.ctx.Config.SALON_JAIL
    service_id = uplink.ctx.Config.SERVICE_ID

    if get_reputation is None:
        uplink.ctx.Logs.debug(f'This UID: {uid} is not listed in the reputation dataclass')
        return None

    # Update the new nickname
    oldnick = get_reputation.nickname
    newnickname = new_nickname
    get_reputation.nickname = newnickname

    # If ban in all channel is ON then unban old nickname an ban the new nickname
    if confmodel.reputation_ban_all_chan == 1:
        for chan in uplink.ctx.Channel.UID_CHANNEL_DB:
            if chan.name != jail_salon:
                await p.send2socket(f":{service_id} MODE {chan.name} -b {oldnick}!*@*")
                await p.send2socket(f":{service_id} MODE {chan.name} +b {newnickname}!*@*")

async def handle_on_quit(uplink: 'Defender', srvmsg: list[str]):
    """Handle on quit message
    >>> srvmsg = ['@unrealircd.org...', ':001MZQ0RB', 'QUIT', ':Quit:', 'quit message']
    Args:
        uplink (Irc): The Defender Module instance
        srvmsg (list[str]): The Server MSG
    """
    p = uplink.ctx.Irc.Protocol
    userobj, reason = p.parse_quit(srvmsg)
    confmodel = uplink.mod_config
    
    if userobj is None:
        uplink.ctx.Logs.debug(f"This UID do not exist anymore: {srvmsg}")
        return None

    ban_all_chan = uplink.ctx.Base.int_if_possible(confmodel.reputation_ban_all_chan)
    jail_salon = uplink.ctx.Config.SALON_JAIL
    service_id = uplink.ctx.Config.SERVICE_ID
    get_user_reputation = uplink.ctx.Reputation.get_reputation(userobj.uid)

    if get_user_reputation is not None:
        final_nickname = get_user_reputation.nickname
        for chan in uplink.ctx.Channel.UID_CHANNEL_DB:
            if chan.name != jail_salon and ban_all_chan == 1:
                await p.send2socket(f":{service_id} MODE {chan.name} -b {final_nickname}!*@*")
                uplink.ctx.Logs.debug(f"Mode -b {final_nickname} on channel {chan.name}")

        uplink.ctx.Reputation.delete(userobj.uid)
        uplink.ctx.Logs.debug(f"Client {get_user_reputation.nickname} has been removed from Reputation local DB")

async def handle_on_uid(uplink: 'Defender', srvmsg: list[str]):
    """_summary_
    >>> ['@s2s-md...', ':001', 'UID', 'nickname', '0', '1754675249', '...', '125-168-141-239.hostname.net', '001BAPN8M', 
    '0', '+iwx', '*', '32001BBE.25ACEFE7.429FE90D.IP', 'ZA2ic7w==', ':realname']

    Args:
        uplink (Defender): The Defender instance
        srvmsg (list[str]): The Server MSG
    """
    irc = uplink.ctx.Irc
    _User = irc.Protocol.parse_uid(srvmsg)
    gconfig = uplink.ctx.Config
    confmodel = uplink.mod_config

    # If Init then do nothing
    if gconfig.DEFENDER_INIT == 1:
        return None

    # Get User information
    if _User is None:
        uplink.ctx.Logs.warning(f'Error when parsing UID', exc_info=True)
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
                uplink.ctx.Reputation.insert(
                    uplink.ctx.Definition.MReputation(
                        **_User.to_dict(),
                        secret_code=uplink.ctx.Utils.generate_random_string(8)
                    )
                )
                if uplink.ctx.Reputation.is_exist(_User.uid):
                    if reputation_flag == 1 and _User.score_connexion <= reputation_seuil:
                        await action_add_reputation_sanctions(uplink, _User.uid)
                        uplink.ctx.Logs.info(f'[REPUTATION] Reputation system ON (Nickname: {_User.nickname}, uid: {_User.uid})')

####################
# ACTION FUNCTIONS #
####################
# [:<sid>] UID <uid> <ts> <nick> <real-host> <displayed-host> <real-user> <ip> <signon> <modes> [<mode-parameters>]+ :<real>
# [:<sid>] UID nickname hopcount timestamp username hostname uid servicestamp umodes virthost cloakedhost ip :gecos
async def action_on_flood(uplink: 'Defender', srvmsg: list[str]):

    confmodel = uplink.mod_config
    if confmodel.flood == 0:
            return None

    irc = uplink.ctx.Irc
    gconfig = uplink.ctx.Config
    p = irc.Protocol
    flood_users = uplink.Schemas.DB_FLOOD_USERS

    user_trigger = str(srvmsg[1]).replace(':','')
    channel = srvmsg[3]
    User = uplink.ctx.User.get_user(user_trigger)

    if User is None or not uplink.ctx.Channel.is_valid_channel(channel_to_check=channel):
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
    unixtime = uplink.ctx.Utils.get_unixtime()
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
        uplink.ctx.Logs.info('system de flood detecté')
        await p.send_priv_msg(
            nick_from=dnickname,
            msg=f"{color_red} {color_bold} Flood detected. Apply the +m mode (Ô_o)",
            channel=channel
        )
        await p.send2socket(f":{service_id} MODE {channel} +m")
        uplink.ctx.Logs.info(f'FLOOD Détecté sur {get_detected_nickname} mode +m appliqué sur le salon {channel}')
        fu.nbr_msg = 0
        fu.first_msg_time = unixtime
        uplink.ctx.Base.create_asynctask(dthreads.coro_release_mode_mute(uplink, 'mode-m', channel))

async def action_add_reputation_sanctions(uplink: 'Defender', jailed_uid: str ):

    irc = uplink.ctx.Irc
    gconfig = uplink.ctx.Config
    p = irc.Protocol
    confmodel = uplink.mod_config

    get_reputation = uplink.ctx.Reputation.get_reputation(jailed_uid)

    if get_reputation is None:
        uplink.ctx.Logs.warning(f'UID {jailed_uid} has not been found')
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
        await p.send_sajoin(nick_to_sajoin=jailed_nickname, channel_name=salon_jail)
        await p.send_priv_msg(nick_from=gconfig.SERVICE_NICKNAME,
            msg=f" [{color_red} REPUTATION {nogc}] : Connexion de {jailed_nickname} ({jailed_score}) ==> {salon_jail}",
            channel=salon_logs
            )
        await p.send_notice(
                nick_from=gconfig.SERVICE_NICKNAME, 
                nick_to=jailed_nickname,
                msg=f"[{color_red} {jailed_nickname} {color_black}] : Merci de tapez la commande suivante {color_bold}{service_prefix}code {code}{color_bold}"
            )
        if reputation_ban_all_chan == 1:
            for chan in uplink.ctx.Channel.UID_CHANNEL_DB:
                if chan.name != salon_jail:
                    await p.send2socket(f":{service_id} MODE {chan.name} +b {jailed_nickname}!*@*")
                    await p.send2socket(f":{service_id} KICK {chan.name} {jailed_nickname}")

        uplink.ctx.Logs.info(f"[REPUTATION] {jailed_nickname} jailed (UID: {jailed_uid}, score: {jailed_score})")
    else:
        uplink.ctx.Logs.info(f"[REPUTATION] {jailed_nickname} skipped (trusted or WebIRC)")
        uplink.ctx.Reputation.delete(jailed_uid)

async def action_apply_reputation_santions(uplink: 'Defender') -> None:

    irc = uplink.ctx.Irc
    gconfig = uplink.ctx.Config
    p = irc.Protocol
    confmodel = uplink.mod_config

    reputation_flag = confmodel.reputation
    reputation_timer = confmodel.reputation_timer
    reputation_seuil = confmodel.reputation_seuil
    ban_all_chan = confmodel.reputation_ban_all_chan
    service_id = gconfig.SERVICE_ID
    dchanlog = gconfig.SERVICE_CHANLOG
    color_red = gconfig.COLORS.red
    nogc = gconfig.COLORS.nogc
    salon_jail = gconfig.SALON_JAIL
    uid_to_clean = []

    if reputation_flag == 0 or reputation_timer == 0 or not uplink.ctx.Reputation.UID_REPUTATION_DB:
        return None

    for user in uplink.ctx.Reputation.UID_REPUTATION_DB:
        if not user.isWebirc: # Si il ne vient pas de WebIRC
            if uplink.ctx.User.get_user_uptime_in_minutes(user.uid) >= reputation_timer and int(user.score_connexion) <= int(reputation_seuil):
                await p.send_priv_msg(
                    nick_from=service_id,
                    msg=f"[{color_red} REPUTATION {nogc}] : Action sur {user.nickname} aprés {str(reputation_timer)} minutes d'inactivité",
                    channel=dchanlog
                    )
                await p.send2socket(f":{service_id} KILL {user.nickname} After {str(reputation_timer)} minutes of inactivity you should reconnect and type the password code")
                await p.send2socket(f":{gconfig.SERVEUR_LINK} REPUTATION {user.remote_ip} 0")

                uplink.ctx.Logs.info(f"Nickname: {user.nickname} KILLED after {str(reputation_timer)} minutes of inactivity")
                uid_to_clean.append(user.uid)

    for uid in uid_to_clean:
        # Suppression des éléments dans {UID_DB} et {REPUTATION_DB}
        for chan in uplink.ctx.Channel.UID_CHANNEL_DB:
            if chan.name != salon_jail and ban_all_chan == 1:
                get_user_reputation = uplink.ctx.Reputation.get_reputation(uid)
                await p.send2socket(f":{service_id} MODE {chan.name} -b {get_user_reputation.nickname}!*@*")

        # Lorsqu'un utilisateur quitte, il doit être supprimé de {UID_DB}.
        uplink.ctx.Channel.delete_user_from_all_channel(uid)
        uplink.ctx.Reputation.delete(uid)
        uplink.ctx.User.delete(uid)

async def action_scan_client_with_cloudfilt(uplink: 'Defender', user_model: 'MUser') -> Optional[dict[str, str]]:
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
    p = uplink.ctx.Irc.Protocol

    if remote_ip in uplink.ctx.Config.WHITELISTED_IP:
        return None
    if uplink.mod_config.cloudfilt_scan == 0:
        return None
    if uplink.cloudfilt_key == '':
        return None

    service_id = uplink.ctx.Config.SERVICE_ID
    service_chanlog = uplink.ctx.Config.SERVICE_CHANLOG
    color_red = uplink.ctx.Config.COLORS.red
    nogc = uplink.ctx.Config.COLORS.nogc

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
        uplink.ctx.Logs.warning(f'Error connecting to cloudfilt API | Code: {str(status_code)}')
        return

    result = {
        'countryiso': decoded_response.get('countryiso', None),
        'listed': decoded_response.get('listed', None),
        'listed_by': decoded_response.get('listed_by', None),
        'host': decoded_response.get('host', None)
    }

    # pseudo!ident@host
    fullname = f'{nickname}!{username}@{hostname}'

    await p.send_priv_msg(
        nick_from=service_id,
        msg=f"[ {color_red}CLOUDFILT_SCAN{nogc} ] : Connexion de {fullname} ({remote_ip}) ==> Host: {str(result['host'])} | country: {str(result['countryiso'])} | listed: {str(result['listed'])} | listed by : {str(result['listed_by'])}",
        channel=service_chanlog)
    
    uplink.ctx.Logs.debug(f"[CLOUDFILT SCAN] ({fullname}) connected from ({result['countryiso']}), Listed: {result['listed']}, by: {result['listed_by']}")    

    if result['listed']:
        await p.send2socket(f":{service_id} GLINE +*@{remote_ip} {uplink.ctx.Config.GLINE_DURATION} Your connexion is listed as dangerous {str(result['listed'])} {str(result['listed_by'])} - detected by cloudfilt")
        uplink.ctx.Logs.debug(f"[CLOUDFILT SCAN GLINE] Dangerous connection ({fullname}) from ({result['countryiso']}) Listed: {result['listed']}, by: {result['listed_by']}")

    response.close()

    return result

async def action_scan_client_with_freeipapi(uplink: 'Defender', user_model: 'MUser') -> Optional[dict[str, str]]:
    """Analyse l'ip avec Freeipapi
        Cette methode devra etre lancer toujours via un thread ou un timer.
    Args:
        uplink (Defender): The Defender object Instance

    Returns:
        dict[str, any] | None: les informations du provider
        keys : 'countryCode', 'isProxy'
    """
    p = uplink.ctx.Irc.Protocol
    remote_ip = user_model.remote_ip
    username = user_model.username
    hostname = user_model.hostname
    nickname = user_model.nickname

    if remote_ip in uplink.ctx.Config.WHITELISTED_IP:
        return None
    if uplink.mod_config.freeipapi_scan == 0:
        return None

    service_id = uplink.ctx.Config.SERVICE_ID
    service_chanlog = uplink.ctx.Config.SERVICE_CHANLOG
    color_red = uplink.ctx.Config.COLORS.red
    nogc = uplink.ctx.Config.COLORS.nogc

    url = f'https://freeipapi.com/api/json/{remote_ip}'

    headers = {
        'Accept': 'application/json',
    }

    response = requests.request(method='GET', url=url, headers=headers, timeout=uplink.timeout)

    # Formatted output
    decoded_response: dict = loads(response.text)

    status_code = response.status_code
    if status_code == 429:
        uplink.ctx.Logs.warning('Too Many Requests - The rate limit for the API has been exceeded.')
        return None
    elif status_code != 200:
        uplink.ctx.Logs.warning(f'status code = {str(status_code)}')
        return None

    result = {
        'countryCode': decoded_response.get('countryCode', None),
        'isProxy': decoded_response.get('isProxy', None)
    }

    # pseudo!ident@host
    fullname = f'{nickname}!{username}@{hostname}'

    await p.send_priv_msg(
        nick_from=service_id,
        msg=f"[ {color_red}FREEIPAPI_SCAN{nogc} ] : Connexion de {fullname} ({remote_ip}) ==> Proxy: {str(result['isProxy'])} | Country : {str(result['countryCode'])}",
        channel=service_chanlog)    
    uplink.ctx.Logs.debug(f"[FREEIPAPI SCAN] ({fullname}) connected from ({result['countryCode']}), Proxy: {result['isProxy']}") 

    if result['isProxy']:
        await p.send2socket(f":{service_id} GLINE +*@{remote_ip} {uplink.ctx.Config.GLINE_DURATION} This server do not allow proxy connexions {str(result['isProxy'])} - detected by freeipapi")
        uplink.ctx.Logs.debug(f"[FREEIPAPI SCAN GLINE] Server do not allow proxy connexions {result['isProxy']}")

    response.close()

    return result

async def action_scan_client_with_abuseipdb(uplink: 'Defender', user_model: 'MUser') -> Optional[dict[str, str]]:
    """Analyse l'ip avec AbuseIpDB
        Cette methode devra etre lancer toujours via un thread ou un timer.
    Args:
        uplink (Defender): Defender instance object
        user_model (MUser): l'objet User qui contient l'ip

    Returns:
        dict[str, str] | None: les informations du provider
    """
    p = uplink.ctx.Irc.Protocol
    remote_ip = user_model.remote_ip
    username = user_model.username
    hostname = user_model.hostname
    nickname = user_model.nickname

    if remote_ip in uplink.ctx.Config.WHITELISTED_IP:
        return None
    if uplink.mod_config.abuseipdb_scan == 0:
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

    service_id = uplink.ctx.Config.SERVICE_ID
    service_chanlog = uplink.ctx.Config.SERVICE_CHANLOG
    color_red = uplink.ctx.Config.COLORS.red
    nogc = uplink.ctx.Config.COLORS.nogc

    # pseudo!ident@host
    fullname = f'{nickname}!{username}@{hostname}'

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

    response.close()

    return result

async def action_scan_client_with_local_socket(uplink: 'Defender', user_model: 'MUser'):
    """local_scan

    Args:
        uplink (Defender): Defender instance object
        user_model (MUser): l'objet User qui contient l'ip
    """
    p = uplink.ctx.Irc.Protocol
    remote_ip = user_model.remote_ip
    username = user_model.username
    hostname = user_model.hostname
    nickname = user_model.nickname
    fullname = f'{nickname}!{username}@{hostname}'

    if remote_ip in uplink.ctx.Config.WHITELISTED_IP:
        return None

    for port in uplink.ctx.Config.PORTS_TO_SCAN:
        try:
            newSocket = ''
            newSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM or socket.SOCK_NONBLOCK)
            newSocket.settimeout(0.5)

            connection = (remote_ip, uplink.ctx.Base.int_if_possible(port))
            newSocket.connect(connection)

            await p.send_priv_msg(
                nick_from=uplink.ctx.Config.SERVICE_NICKNAME,
                msg=f"[ {uplink.ctx.Config.COLORS.red}PROXY_SCAN{uplink.ctx.Config.COLORS.nogc} ] {fullname} ({remote_ip}) :     Port [{str(port)}] ouvert sur l'adresse ip [{remote_ip}]",
                channel=uplink.ctx.Config.SERVICE_CHANLOG
                )
            # print(f"=======> Le port {str(port)} est ouvert !!")
            uplink.ctx.Base.running_sockets.append(newSocket)
            # print(newSocket)
            newSocket.shutdown(socket.SHUT_RDWR)
            newSocket.close()

        except (socket.timeout, ConnectionRefusedError):
            uplink.ctx.Logs.info(f"Le port {remote_ip}:{str(port)} est fermé")
        except AttributeError as ae:
            uplink.ctx.Logs.warning(f"AttributeError ({remote_ip}): {ae}")
        except socket.gaierror as err:
            uplink.ctx.Logs.warning(f"Address Info Error ({remote_ip}): {err}")
        finally:
            # newSocket.shutdown(socket.SHUT_RDWR)
            newSocket.close()
            uplink.ctx.Logs.info('=======> Fermeture de la socket')

async def action_scan_client_with_psutil(uplink: 'Defender', user_model: 'MUser') -> list[int]:
    """psutil_scan for Linux (should be run on the same location as the unrealircd server)

    Args:
        userModel (UserModel): The User Model Object

    Returns:
        list[int]: list of ports
    """
    p = uplink.ctx.Irc.Protocol
    remote_ip = user_model.remote_ip
    username = user_model.username
    hostname = user_model.hostname
    nickname = user_model.nickname

    if remote_ip in uplink.ctx.Config.WHITELISTED_IP:
        return None

    try:
        connections = psutil.net_connections(kind='inet')
        fullname = f'{nickname}!{username}@{hostname}'

        matching_ports = [conn.raddr.port for conn in connections if conn.raddr and conn.raddr.ip == remote_ip]
        uplink.ctx.Logs.info(f"Connexion of {fullname} ({remote_ip}) using ports : {str(matching_ports)}")

        if matching_ports:
            await p.send_priv_msg(
                    nick_from=uplink.ctx.Config.SERVICE_NICKNAME,
                    msg=f"[ {uplink.ctx.Config.COLORS.red}PSUTIL_SCAN{uplink.ctx.Config.COLORS.black} ] {fullname} ({remote_ip}) : is using ports {matching_ports}",
                    channel=uplink.ctx.Config.SERVICE_CHANLOG
                )

        return matching_ports

    except psutil.AccessDenied as ad:
        uplink.ctx.Logs.critical(f'psutil_scan: Permission error: {ad}')