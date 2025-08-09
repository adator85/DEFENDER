from re import findall
from typing import Any, Optional, Literal, TYPE_CHECKING
from core.classes import user

if TYPE_CHECKING:
    from core.definition import MChannel
    from core.base import Base

class Channel:

    UID_CHANNEL_DB: list['MChannel'] = []
    """List that contains all the Channels objects (ChannelModel)
    """

    def __init__(self, baseObj: 'Base') -> None:

        self.Logs = baseObj.logs
        self.Base = baseObj

        return None

    def insert(self, newChan: 'MChannel') -> bool:
        """This method will insert a new channel and if the channel exist it will update the user list (uids)

        Args:
            newChan (ChannelModel): The channel model object

        Returns:
            bool: True if new channel, False if channel exist (However UID could be updated)
        """
        result = False
        exist = False

        if not self.Is_Channel(newChan.name):
            self.Logs.error(f"The channel {newChan.name} is not valid, channel must start with #")
            return False

        for record in self.UID_CHANNEL_DB:
            if record.name.lower() == newChan.name.lower():
                # If the channel exist, update the user list and do not go further
                exist = True
                # self.Logs.debug(f'{record.name} already exist')

                for user in newChan.uids:
                    record.uids.append(user)

                # Supprimer les doublons
                del_duplicates = list(set(record.uids))
                record.uids = del_duplicates
                # self.Logs.debug(f'Updating a new UID to the channel {record}')
                return result

        if not exist:
            # If the channel don't exist, then create it
            newChan.name = newChan.name.lower()
            self.UID_CHANNEL_DB.append(newChan)
            result = True
            # self.Logs.debug(f'New Channel Created: ({newChan})')

        if not result:
            self.Logs.critical(f'The Channel Object was not inserted {newChan}')

        self.clean_channel()

        return result

    def delete(self, channel_name: str) -> bool:

        chanObj = self.get_Channel(channel_name)

        if chanObj is None:
            return False

        self.UID_CHANNEL_DB.remove(chanObj)

        return True

    def delete_user_from_channel(self, channel_name: str, uid:str) -> bool:
        try:
            result = False

            chanObj = self.get_Channel(channel_name.lower())

            if chanObj is None:
                return result

            for userid in chanObj.uids:
                if self.Base.clean_uid(userid) == self.Base.clean_uid(uid):
                    chanObj.uids.remove(userid)
                    result = True

            self.clean_channel()

            return result
        except ValueError as ve:
            self.Logs.error(f'{ve}')

    def delete_user_from_all_channel(self, uid:str) -> bool:
        try:
            result = False

            for record in self.UID_CHANNEL_DB:
                for user_id in record.uids:
                    if self.Base.clean_uid(user_id) == self.Base.clean_uid(uid):
                        record.uids.remove(user_id)
                        # self.Logs.debug(f'The UID {uid} has been removed, here is the new object: {record}')
                        result = True

            self.clean_channel()

            return result
        except ValueError as ve:
            self.Logs.error(f'{ve}')

    def add_user_to_a_channel(self, channel_name: str, uid: str) -> bool:
        try:
            result = False
            chanObj = self.get_Channel(channel_name)
            self.Logs.debug(f"** {__name__}")

            if chanObj is None:
                result = self.insert(MChannel(channel_name, uids=[uid]))
                # self.Logs.debug(f"** {__name__} - result: {result}")
                # self.Logs.debug(f'New Channel Created: ({chanObj})')
                return result

            chanObj.uids.append(uid)
            del_duplicates = list(set(chanObj.uids))
            chanObj.uids = del_duplicates
            # self.Logs.debug(f'New Channel Created: ({chanObj})')

            return True
        except Exception as err:
            self.Logs.error(f'{err}')

    def is_user_present_in_channel(self, channel_name: str, uid: str) -> bool:
        """Check if a user is present in the channel

        Args:
            channel_name (str): The channel to check
            uid (str): The UID

        Returns:
            bool: True if the user is present in the channel
        """
        user_found = False
        chan = self.get_Channel(channel_name=channel_name)
        if chan is None:
            return user_found

        clean_uid = self.Base.clean_uid(uid=uid)
        for chan_uid in chan.uids:
            if self.Base.clean_uid(chan_uid) == clean_uid:
                user_found = True
                break

        return user_found

    def clean_channel(self) -> None:
        """Remove Channels if empty
        """
        try:
            for record in self.UID_CHANNEL_DB:
                if not record.uids:
                    self.UID_CHANNEL_DB.remove(record)
                    # self.Logs.debug(f'The Channel {record.name} has been removed, here is the new object: {record}')
            return None
        except Exception as err:
            self.Logs.error(f'{err}')

    def get_Channel(self, channel_name: str) -> Optional['MChannel']:

        for record in self.UID_CHANNEL_DB:
            if record.name == channel_name:
                return record

        return None

    def get_channel_asdict(self, chan_name: str) -> Optional[dict[str, Any]]:

        channel_obj: Optional['MChannel'] = self.get_Channel(chan_name=chan_name)

        if channel_obj is None:
            return None
        
        return channel_obj.to_dict()

    def Is_Channel(self, channelToCheck: str) -> bool:
        """Check if the string has the # caractere and return True if this is a channel

        Args:
            channelToCheck (str): The string to test if it is a channel or not

        Returns:
            bool: True if the string is a channel / False if this is not a channel
        """
        try:
            
            if channelToCheck is None:
                return False

            pattern = fr'^#'
            isChannel = findall(pattern, channelToCheck)

            if not isChannel:
                return False
            else:
                return True
        except TypeError as te:
            self.Logs.error(f'TypeError: [{channelToCheck}] - {te}')
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
            channel_name = channel_name.lower() if self.Is_Channel(channel_name) else None
            core_table = self.Base.Config.TABLE_CHANNEL

            if not channel_name:
                self.Logs.warning(f'The channel [{channel_name}] is not correct')
                return False

            match action:

                case 'add':
                    mes_donnees = {'module_name': module_name, 'channel_name': channel_name}
                    response = self.Base.db_execute_query(f"SELECT id FROM {core_table} WHERE module_name = :module_name AND channel_name = :channel_name", mes_donnees)
                    isChannelExist = response.fetchone()

                    if isChannelExist is None:
                        mes_donnees = {'datetime': self.Base.get_datetime(), 'channel_name': channel_name, 'module_name': module_name}
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

