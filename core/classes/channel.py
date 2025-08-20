from re import findall
from typing import Any, Optional, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from core.definition import MChannel
    from core.loader import Loader

class Channel:

    UID_CHANNEL_DB: list['MChannel'] = []
    """List that contains all the Channels objects (ChannelModel)
    """

    def __init__(self, loader: 'Loader') -> None:

        self.Logs = loader.Logs
        self.Base = loader.Base
        self.Utils = loader.Utils

        return None

    def insert(self, new_channel: 'MChannel') -> bool:
        """This method will insert a new channel and if the channel exist it will update the user list (uids)

        Args:
            new_channel (MChannel): The channel model object

        Returns:
            bool: True if new channel, False if channel exist (However UID could be updated)
        """
        result = False
        exist = False

        if not self.is_valid_channel(new_channel.name):
            self.Logs.error(f"The channel {new_channel.name} is not valid, channel must start with #")
            return False

        for record in self.UID_CHANNEL_DB:
            if record.name.lower() == new_channel.name.lower():
                # If the channel exist, update the user list and do not go further
                exist = True
                # self.Logs.debug(f'{record.name} already exist')

                for user in new_channel.uids:
                    record.uids.append(user)

                # Supprimer les doublons
                del_duplicates = list(set(record.uids))
                record.uids = del_duplicates
                # self.Logs.debug(f'Updating a new UID to the channel {record}')
                return result

        if not exist:
            # If the channel don't exist, then create it
            new_channel.name = new_channel.name.lower()
            self.UID_CHANNEL_DB.append(new_channel)
            result = True
            # self.Logs.debug(f'New Channel Created: ({new_channel})')

        if not result:
            self.Logs.critical(f'The Channel Object was not inserted {new_channel}')

        self.clean_channel()

        return result

    def delete(self, channel_name: str) -> bool:
        """Delete channel from the UID_CHANNEL_DB

        Args:
            channel_name (str): The Channel name

        Returns:
            bool: True if it was deleted
        """

        chan_obj = self.get_channel(channel_name)

        if chan_obj is None:
            return False

        self.UID_CHANNEL_DB.remove(chan_obj)

        return True

    def delete_user_from_channel(self, channel_name: str, uid:str) -> bool:
        """Delete a user from a channel

        Args:
            channel_name (str): The channel name
            uid (str): The Client UID

        Returns:
            bool: True if the client has been deleted from the channel
        """
        try:
            result = False

            chan_obj = self.get_channel(channel_name.lower())

            if chan_obj is None:
                return result

            for userid in chan_obj.uids:
                if self.Utils.clean_uid(userid) == self.Utils.clean_uid(uid):
                    chan_obj.uids.remove(userid)
                    result = True

            self.clean_channel()

            return result
        except ValueError as ve:
            self.Logs.error(f'{ve}')

    def delete_user_from_all_channel(self, uid:str) -> bool:
        """Delete a client from all channels

        Args:
            uid (str): The client UID

        Returns:
            bool: True if the client has been deleted from all channels
        """
        try:
            result = False

            for record in self.UID_CHANNEL_DB:
                for user_id in record.uids:
                    if self.Utils.clean_uid(user_id) == self.Utils.clean_uid(uid):
                        record.uids.remove(user_id)
                        result = True

            self.clean_channel()

            return result
        except ValueError as ve:
            self.Logs.error(f'{ve}')

    def add_user_to_a_channel(self, channel_name: str, uid: str) -> bool:
        """Add a client to a channel

        Args:
            channel_name (str): The channel name
            uid (str): The client UID

        Returns:
            bool: True is the clien has been added
        """
        try:
            chan_obj = self.get_channel(channel_name)

            if chan_obj is None:
                # Create a new channel if the channel don't exist
                self.Logs.debug(f"New channel will be created ({channel_name} - {uid})")
                return self.insert(MChannel(channel_name, uids=[uid]))

            chan_obj.uids.append(uid)
            del_duplicates = list(set(chan_obj.uids))
            chan_obj.uids = del_duplicates

            return True
        except Exception as err:
            self.Logs.error(f'{err}')
            return False

    def is_user_present_in_channel(self, channel_name: str, uid: str) -> bool:
        """Check if a user is present in the channel

        Args:
            channel_name (str): The channel name to check
            uid (str): The client UID

        Returns:
            bool: True if the user is present in the channel
        """
        chan = self.get_channel(channel_name=channel_name)
        if chan is None:
            return False

        clean_uid = self.Utils.clean_uid(uid=uid)
        for chan_uid in chan.uids:
            if self.Utils.clean_uid(chan_uid) == clean_uid:
                return True

        return False

    def clean_channel(self) -> None:
        """If channel doesn't contain any client this method will remove the channel
        """
        try:
            for record in self.UID_CHANNEL_DB:
                if not record.uids:
                    self.UID_CHANNEL_DB.remove(record)

            return None
        except Exception as err:
            self.Logs.error(f'{err}')

    def get_channel(self, channel_name: str) -> Optional['MChannel']:
        """Get the channel object

        Args:
            channel_name (str): The Channel name

        Returns:
            MChannel: The channel object model if exist else None
        """

        for record in self.UID_CHANNEL_DB:
            if record.name.lower() == channel_name.lower():
                return record

        return None

    def get_channel_asdict(self, channel_name: str) -> Optional[dict[str, Any]]:

        channel_obj: Optional['MChannel'] = self.get_channel(channel_name)

        if channel_obj is None:
            return None
        
        return channel_obj.to_dict()

    def is_valid_channel(self, channel_to_check: str) -> bool:
        """Check if the string has the # caractere and return True if this is a valid channel

        Args:
            channel_to_check (str): The string to test if it is a channel or not

        Returns:
            bool: True if the string is a channel / False if this is not a channel
        """
        try:
            
            if channel_to_check is None:
                return False

            pattern = fr'^#'
            isChannel = findall(pattern, channel_to_check)

            if not isChannel:
                return False
            else:
                return True
        except TypeError as te:
            self.Logs.error(f'TypeError: [{channel_to_check}] - {te}')
        except Exception as err:
            self.Logs.error(f'Error Not defined: {err}')

    def db_query_channel(self, action: Literal['add','del'], module_name: str, channel_name: str) -> bool:
        """You can add a channel or delete a channel.

        Args:
            action (Literal[&#39;add&#39;,&#39;del&#39;]): Action on the database
            module_name (str): The module name (mod_test)
            channel_name (str): The channel name (With #)

        Returns:
            bool: True if action done
        """
        try:
            channel_name = channel_name.lower() if self.is_valid_channel(channel_name) else None
            core_table = self.Base.Config.TABLE_CHANNEL

            if not channel_name:
                self.Logs.warning(f'The channel [{channel_name}] is not correct')
                return False

            match action:

                case 'add':
                    mes_donnees = {'module_name': module_name, 'channel_name': channel_name}
                    response = self.Base.db_execute_query(f"SELECT id FROM {core_table} WHERE module_name = :module_name AND channel_name = :channel_name", mes_donnees)
                    is_channel_exist = response.fetchone()

                    if is_channel_exist is None:
                        mes_donnees = {'datetime': self.Utils.get_sdatetime(), 'channel_name': channel_name, 'module_name': module_name}
                        insert = self.Base.db_execute_query(f"INSERT INTO {core_table} (datetime, channel_name, module_name) VALUES (:datetime, :channel_name, :module_name)", mes_donnees)
                        if insert.rowcount:
                            self.Logs.debug(f'New channel added: channel={channel_name} / module_name={module_name}')
                            return True
                    else:
                        return False

                case 'del':
                    mes_donnes = {'channel_name': channel_name, 'module_name': module_name}
                    response = self.Base.db_execute_query(f"DELETE FROM {core_table} WHERE channel_name = :channel_name AND module_name = :module_name", mes_donnes)

                    if response.rowcount > 0:
                        self.Logs.debug(f'Channel deleted: channel={channel_name} / module: {module_name}')
                        return True
                    else:
                        return False

                case _:
                    return False

        except Exception as err:
            self.Logs.error(err)
