from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from mods.votekick.mod_votekick import Votekick

def add_vote_channel_to_database(uplink: 'Votekick', channel: str) -> bool:
    """Adds a new channel to the votekick database if it doesn't already exist.

    This function checks if the specified channel is already registered in the 
    `votekick_channel` table. If not, it inserts a new entry with the current timestamp.

    Args:
        uplink (Votekick): The main votekick system instance that provides access to utilities and database operations.
        channel (str): The name of the channel to be added to the database.

    Returns:
        bool: True if the channel was successfully inserted into the database.
              False if the channel already exists or the insertion failed.
    """
    current_datetime = uplink.Utils.get_sdatetime()
    mes_donnees = {'channel': channel}

    response = uplink.Base.db_execute_query("SELECT id FROM votekick_channel WHERE channel = :channel", mes_donnees)

    is_channel_exist = response.fetchone()

    if is_channel_exist is None:
        mes_donnees = {'datetime': current_datetime, 'channel': channel}
        insert = uplink.Base.db_execute_query(f"INSERT INTO votekick_channel (datetime, channel) VALUES (:datetime, :channel)", mes_donnees)
        if insert.rowcount > 0:
            return True
        else:
            return False
    else:
        return False

def delete_vote_channel_from_database(uplink: 'Votekick', channel: str) -> bool:
    """Deletes a channel entry from the votekick database.

    This function removes the specified channel from the `votekick_channel` table
    if it exists. It returns True if the deletion was successful.

    Args:
        uplink (Votekick): The main votekick system instance used to execute the database operation.
        channel (str): The name of the channel to be removed from the database.

    Returns:
        bool: True if the channel was successfully deleted, False if no rows were affected.
    """
    mes_donnes = {'channel': channel}
    response = uplink.Base.db_execute_query("DELETE FROM votekick_channel WHERE channel = :channel", mes_donnes)
    
    affected_row = response.rowcount

    if affected_row > 0:
        return True
    else:
        return False

async def join_saved_channels(uplink: 'Votekick') -> None:

    param = {'module_name': uplink.module_name}
    result = uplink.Base.db_execute_query(f"SELECT id, channel_name FROM {uplink.Config.TABLE_CHANNEL} WHERE module_name = :module_name", param)

    channels = result.fetchall()

    for channel in channels:
        id_, chan = channel
        uplink.VoteKickManager.activate_new_channel(chan)
        await uplink.Protocol.send_sjoin(channel=chan)
        await uplink.Protocol.send2socket(f":{uplink.Config.SERVICE_NICKNAME} SAMODE {chan} +o {uplink.Config.SERVICE_NICKNAME}")

    return None