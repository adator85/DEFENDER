import logging
import random
from typing import Optional, TYPE_CHECKING
from faker import Faker

logging.getLogger('faker').setLevel(logging.CRITICAL)

if TYPE_CHECKING:
    from mods.clone.mod_clone import Clone

def create_faker_object(faker_local: Optional[str] = 'en_GB') -> Faker:
    """Create a new faker object

    Args:
        faker_local (Optional[str], optional): _description_. Defaults to 'en_GB'.

    Returns:
        Faker: The Faker Object
    """
    if faker_local not in ['en_GB', 'fr_FR']:
        faker_local = 'en_GB'

    return Faker(faker_local)

def generate_uid_for_clone(faker_instance: 'Faker', server_id: str) -> str:
    chaine = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    return server_id + ''.join(faker_instance.random_sample(chaine, 6))

def generate_vhost_for_clone(faker_instance: 'Faker') -> str:
    """Generate new vhost for the clone

    Args:
        faker_instance (Faker): The Faker instance

    Returns:
        str: _description_
    """
    rand_1 = faker_instance.random_elements(['A','B','C','D','E','F','0','1','2','3','4','5','6','7','8','9'], unique=True, length=8)
    rand_2 = faker_instance.random_elements(['A','B','C','D','E','F','0','1','2','3','4','5','6','7','8','9'], unique=True, length=8)
    rand_3 = faker_instance.random_elements(['A','B','C','D','E','F','0','1','2','3','4','5','6','7','8','9'], unique=True, length=8)

    vhost = ''.join(rand_1) + '.' + ''.join(rand_2) + '.' + ''.join(rand_3) + '.IP'
    return vhost

def generate_username_for_clone(faker_instance: 'Faker') -> str:
    """Generate vhosts for clones

    Returns:
        str: The vhost
    """
    chaine = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(faker_instance.random_sample(chaine, 9))

def generate_realname_for_clone(faker_instance: 'Faker') -> tuple[int, str, str]:
    """Generate realname for clone
    Ex: XX F|M Department
    Args:
        faker_instance (Faker): _description_

    Returns:
        tuple: Age | Gender | Department
    """
    # Create realname XX F|M Department
    gender = faker_instance.random_choices(['F','M'], 1)
    gender = ''.join(gender)
    age = random.randint(20, 60)
    if faker_instance.locales[0] == 'fr_FR':
        department = faker_instance.department_name()
    else:
        department = faker_instance.city()

    return (age, gender, department)

def generate_nickname_for_clone(faker_instance: 'Faker', gender: Optional[str] = 'AUTO') -> str:
    """Generate nickname for clone

    Args:
        faker_instance (Faker): The Faker Instance
        gender (str): The Gender.Default F

    Returns:
        str: Nickname Based on the Gender
    """
    if gender.upper() == 'AUTO' or gender.upper() not in ['F', 'M']:
        # Generate new gender
        gender = faker_instance.random_choices(['F','M'], 1)
        gender = ''.join(gender)

    if gender.upper() == 'F':
        return faker_instance.first_name_female()
    elif gender.upper() == 'M':
        return faker_instance.first_name_male()

def generate_ipv4_for_clone(faker_instance: 'Faker', auto: bool = True) -> str:
    """Generate remote ipv4 for clone

    Args:
        faker_instance (Faker): The Faker Instance
        auto (bool): Set auto generation of ip or 127.0.0.1 will be returned

    Returns:
        str: Remote IPV4
    """
    return faker_instance.ipv4_private() if auto else '127.0.0.1'

def generate_hostname_for_clone(faker_instance: 'Faker') -> str:
    """Generate hostname for clone

    Args:
        faker_instance (Faker): The Faker Instance

    Returns:
        str: New hostname
    """
    return faker_instance.hostname()

def create_new_clone(uplink: 'Clone', faker_instance: 'Faker', group: str = 'Default', auto_remote_ip: bool = False) -> bool:
    """Create a new Clone object in the DB_CLONES.

    Args:
        faker_instance (Faker): The Faker instance

    Returns:
        bool: True if it was created
    """
    faker = faker_instance

    uid = generate_uid_for_clone(faker, uplink.Config.SERVEUR_ID)
    umodes = uplink.Config.CLONE_UMODES

    # Generate Username
    username = generate_username_for_clone(faker)

    # Generate realname (XX F|M Department)
    age, gender, department = generate_realname_for_clone(faker)
    realname = f'{age} {gender} {department}'

    # Generate nickname
    nickname = generate_nickname_for_clone(faker, gender)

    # Generate decoded ipv4 and hostname
    decoded_ip = generate_ipv4_for_clone(faker, auto_remote_ip)
    hostname = generate_hostname_for_clone(faker)
    vhost = generate_vhost_for_clone(faker)

    checkNickname = uplink.Clone.nickname_exists(nickname)
    checkUid = uplink.Clone.uid_exists(uid=uid)

    while checkNickname:
        caracteres = '0123456789'
        randomize = ''.join(random.choice(caracteres) for _ in range(2))
        nickname = nickname + str(randomize)
        checkNickname = uplink.Clone.nickname_exists(nickname)

    while checkUid:
        uid = generate_uid_for_clone(faker, uplink.Config.SERVEUR_ID)
        checkUid = uplink.Clone.uid_exists(uid=uid)

    clone = uplink.Schemas.MClone(
                connected=False,
                nickname=nickname,
                username=username,
                realname=realname,
                hostname=hostname,
                umodes=umodes,
                uid=uid,
                remote_ip=decoded_ip,
                vhost=vhost,
                group=group,
                channels=[]
                )

    uplink.Clone.insert(clone)

    return True

def handle_on_privmsg(uplink: 'Clone', srvmsg: list[str]):
    
    uid_sender = uplink.Irc.Utils.clean_uid(srvmsg[1])
    senderObj = uplink.User.get_User(uid_sender)

    if senderObj.hostname in uplink.Config.CLONE_LOG_HOST_EXEMPT:
        return

    if not senderObj is None:
        senderMsg = ' '.join(srvmsg[4:])
        clone_obj = uplink.Clone.get_clone(srvmsg[3])

        if clone_obj is None:
            return

        if clone_obj.uid != uplink.Config.SERVICE_ID:
            final_message = f"{senderObj.nickname}!{senderObj.username}@{senderObj.hostname} > {senderMsg.lstrip(':')}"
            uplink.Protocol.send_priv_msg(
                nick_from=clone_obj.uid,
                msg=final_message,
                channel=uplink.Config.CLONE_CHANNEL
            )
