import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mods.clone.mod_clone import Clone

async def coro_connect_clones(uplink: 'Clone', 
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
            await uplink.ctx.Irc.Protocol.send_uid(clone.nickname, clone.username, clone.hostname, clone.uid, clone.umodes, clone.vhost, clone.remote_ip, clone.realname, clone.geoip, print_log=False)
            await uplink.ctx.Irc.Protocol.send_join_chan(uidornickname=clone.uid, channel=uplink.ctx.Config.CLONE_CHANNEL, password=uplink.ctx.Config.CLONE_CHANNEL_PASSWORD, print_log=False)

        await asyncio.sleep(interval)
        clone.connected = True

async def thread_kill_clones(uplink: 'Clone'):

    clone_to_kill = uplink.Clone.UID_CLONE_DB.copy()

    for clone in clone_to_kill:
        await uplink.ctx.Irc.Protocol.send_quit(clone.uid, 'Gooood bye', print_log=False)
        uplink.Clone.delete(clone.uid)

    del clone_to_kill
