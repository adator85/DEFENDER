from typing import TYPE_CHECKING
from time import sleep

if TYPE_CHECKING:
    from mods.clone.mod_clone import Clone

def thread_connect_clones(uplink: 'Clone', 
                          number_of_clones:int , 
                          group: str = 'Default', 
                          auto_remote_ip: bool = False, 
                          interval: float = 0.2
                          ):

    for i in range(0, number_of_clones):
        uplink.Utils.create_new_clone(
            uplink=uplink,
            faker_instance=uplink.Faker,
            group=group,
            auto_remote_ip=auto_remote_ip
        )

    for clone in uplink.Clone.UID_CLONE_DB:

        if uplink.stop:
            print(f"Stop creating clones ...")
            uplink.stop = False
            break

        if not clone.connected:
            uplink.Protocol.send_uid(clone.nickname, clone.username, clone.hostname, clone.uid, clone.umodes, clone.vhost, clone.remote_ip, clone.realname, print_log=False)
            uplink.Protocol.send_join_chan(uidornickname=clone.uid, channel=uplink.Config.CLONE_CHANNEL, password=uplink.Config.CLONE_CHANNEL_PASSWORD, print_log=False)

        sleep(interval)
        clone.connected = True

def thread_kill_clones(uplink: 'Clone'):

    clone_to_kill = uplink.Clone.UID_CLONE_DB.copy()

    for clone in clone_to_kill:
        uplink.Protocol.send_quit(clone.uid, 'Gooood bye', print_log=False)
        uplink.Clone.delete(clone.uid)

    del clone_to_kill
