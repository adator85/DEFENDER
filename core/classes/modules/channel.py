from re import findall
from typing import Optional, Literal, TYPE_CHECKING
from core.definition import MChannel, ChannelMembers

if TYPE_CHECKING:
    from core.loader import Loader

class Channel:

    def __init__(self, loader: 'Loader'):
        """

        Args:
            loader (Loader): The Loader Instance
        """
        self._ctx = loader
        self.UID_CHANNEL_DB: list[MChannel] = []
        """List that contains all the Channels objects (ChannelModel)
        """

    def insert(self, new_channel: MChannel) -> bool:
        """This method will insert a new channel and if the channel exist it will update the user list (uids)

        Args:
            new_channel (MChannel): The channel model object

        Returns:
            bool: True if new channel, False if channel exist (However UID could be updated)
        """

        if not self.is_valid_channel(new_channel.name):
            self._ctx.Logs.error('The channel %s is not valid, channel must start with #',
                                 new_channel.name)
            return False

        _channel = self.get_channel(new_channel.name)
        s_to_m = self._ctx.Settings.PROTOCTL_PREFIX_SIGNES_MODES

        # Clean UID of new channels.
        for member in new_channel.members:
            member.uid = self._ctx.Utils.clean_uid(member.uid)
            if member.uid != self._ctx.Config.SERVICE_ID:
                converted_level = ''
                for level in member.level:
                    converted_level += s_to_m.get(level, '*')
                
                member.level = converted_level
                
        if _channel:
            # Channel alredy exist Update all levels
            # available: [{'A': 0}, {'B': 2}]
            # new: [{'B': 1}, {'C': 0}]

            # Update the channel mode
            if _channel.mode == '':
                _channel.mode += new_channel.mode

            # Update the members
            for new_member in new_channel.members:
                is_new = True
                for available_member in _channel.members:
                    if new_member.uid == available_member.uid:
                        # Update available member.
                        available_member = new_member
                        is_new = False

                if is_new:
                    _channel.members.append(new_member)

            self.clean_channel()
            return True
        else:
            new_channel.name = new_channel.name.lower()
            self.UID_CHANNEL_DB.append(new_channel)
            self.clean_channel()
            return True

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

    def delete_user_from_channel(self, channel_name: str, uid: str) -> bool:
        """Delete a user from a channel

        Args:
            channel_name (str): The channel name
            uid (str): The Client UID

        Returns:
            bool: True if the client has been deleted from the channel
        """
        try:
            _channel = self.get_channel(channel_name)

            if _channel:
                _members = _channel.members.copy()
                for _member in _members:
                    if self._ctx.Utils.clean_uid(_member.uid) == self._ctx.Utils.clean_uid(uid):
                        _channel.members.remove(_member)
                        self.clean_channel()
                        return True

            return False

        except ValueError as ve:
            self._ctx.Logs.error('ValueError: %s', ve)
            return False

    def delete_user_from_all_channel(self, uid: str) -> bool:
        """Delete a client from all channels

        Args:
            uid (str): The client UID

        Returns:
            bool: True if the client has been deleted from all channels
        """
        try:
            for _channel in self.UID_CHANNEL_DB:
                for _member in _channel.members:
                    if self._ctx.Utils.clean_uid(_member.uid) == self._ctx.Utils.clean_uid(uid):
                        _channel.members.remove(_member)

            self.clean_channel()

            return True

        except ValueError as ve:
            self._ctx.Logs.error('ValueError: %s', ve)
            return False

    def append_user_mode_from_channel(self, channel: str, uid: str, mode: str) -> bool:
        
        _logs = self._ctx.Logs
        _channel = self.get_channel(channel)
        _signe = ''

        if len(mode) != 2:
            return False

        if _channel is None:
            return False
        
        _signe = mode[0]
        _mode = mode[1]

        for member in _channel.members:
            if member.uid == self._ctx.Utils.clean_uid(uid):
                if _signe == '+':
                    member.level += _mode
                    member.level = member.level.replace(_signe, '')
                    member.level = ''.join(set(list(member.level)))
                    _logs.debug('[APPEND USER MODE] %s has been granted with %s mode', uid, _mode)
                elif _signe == '-':
                    member.level = member.level.replace(_mode, '')
                    _logs.debug('[APPEND USER MODE] %s has been remove with %s mode', uid, _mode)
                else:
                    _logs.debug('[APPEND USER MODE] ERROR Updating mode %s', mode)
                    return False

                return True

        _logs.error('[APPEND USER MODE] Nothing happened for %s | %s | %s', channel, uid, mode)
        return False

    def append_channel_mode(self, channel: str, modes: str) -> bool:
        
        _logs = self._ctx.Logs
        _channel = self.get_channel(channel)

        if modes[0] not in {'+', '-'}:
            return False

        signe = modes[0]

        if _channel is not None:
            # Modes: +lnt
            for mode in modes[1:]:
                if signe == '+':
                    _channel.mode += mode
                    _channel.mode = _channel.mode.replace(signe, '')
                    _channel.mode = ''.join(set(list(_channel.mode)))
                    _channel.mode = signe + _channel.mode
                elif signe == '-':
                    _channel.mode = _channel.mode.replace(mode, '')
                else:
                    _logs.error('[APPEND CHANNEL MODE] Wrong sign in modes %s', signe)
                    return False

            _logs.debug('[APPEND CHANNEL MODE] Mode of %s has been updated to %s',
                        _channel.name, _channel.mode)

            return True

        _logs.error('[APPEND CHANNEL MODE] Nothing happened for, channel: %s | Modes: %s', channel, modes)
        return False

    def add_user_to_a_channel(self, channel_name: str, uid: str, level: str) -> bool:
        """Add a client to a channel

        Args:
            channel_name (str): The channel name
            uid (str): The client UID
            level (str): The level of the client

        Returns:
            bool: True is the clien has been added
        """
        try:
            _channel = self.get_channel(channel_name)

            if _channel is None:
                # Create a new channel if the channel don't exist
                self._ctx.Logs.debug("New channel will be created (%s - %s)", channel_name, uid)
                return self.insert(MChannel(channel_name, '', [ChannelMembers(uid=uid, level=level)]))

            _channel.members.append(ChannelMembers(uid, level))
            _channel.members = list(set(_channel.members))
            return True

        except Exception as err:
            self._ctx.Logs.error('General Error: %s', err)
            return False

    def is_user_present_in_channel(self, channel_name: str, uid: str) -> bool:
        """Check if a user is present in the channel

        Args:
            channel_name (str): The channel name to check
            uid (str): The client UID

        Returns:
            bool: True if the user is present in the channel
        """
        _channel = self.get_channel(channel_name=channel_name)

        if _channel:
            clean_uid = self._ctx.Utils.clean_uid(uid=uid)
            for _member in _channel.members:
                if self._ctx.Utils.clean_uid(_member.uid) == clean_uid:
                    return True

        return False

    def clean_channel(self) -> None:
        """If channel doesn't contain any client this method will remove the channel
        """
        try:
            _channels = self.UID_CHANNEL_DB.copy()
            for _channel in _channels:
                if not _channel.members:
                    self.UID_CHANNEL_DB.remove(_channel)

            del _channels
            return None
        except Exception as err:
            self._ctx.Logs.error('General Error: %s', err, exc_info=True)

    def get_channel(self, channel_name: str) -> Optional[MChannel]:
        """Get the channel object

        Args:
            channel_name (str): The Channel name

        Returns:
            MChannel: The channel object model if exist else None
        """

        for _channel in self.UID_CHANNEL_DB:
            if _channel.name.lower() == channel_name.lower():
                return _channel

        return None

    def is_valid_channel(self, channel_to_check: str) -> bool:
        """Check if the string has the # caractere and return True if this is a valid channel

        Args:
            channel_to_check (str): The string to test if it is a channel or not

        Returns:
            bool: True if the string is a channel / False if this is not a channel
        """
        try:
            
            if not channel_to_check:
                return False

            pattern = fr'^#'
            is_channel = findall(pattern, channel_to_check)

            if not is_channel:
                return False
            else:
                return True
        except TypeError as te:
            self._ctx.Logs.error('Type Error: [%s] - %s', channel_to_check, te)
            return False
        except Exception as err:
            self._ctx.Logs.error('General Error: %s', err, exc_info=True)
            return False

    async def db_query_channel(self, action: Literal['add','del'], module_name: str, channel_name: str) -> bool:
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
            core_table = self._ctx.Base.Config.TABLE_CHANNEL

            if not channel_name:
                self._ctx.Logs.warning('The channel [%s] is not correct', channel_name)
                return False

            match action:

                case 'add':
                    mes_donnees = {'module_name': module_name, 'channel_name': channel_name}
                    response = await self._ctx.Base.db_execute_query(f"SELECT id FROM {core_table} WHERE module_name = :module_name AND channel_name = :channel_name", mes_donnees)
                    is_channel_exist = response.fetchone()

                    if is_channel_exist is None:
                        mes_donnees = {'datetime': self._ctx.Utils.get_sdatetime(), 'channel_name': channel_name, 'module_name': module_name}
                        insert = await self._ctx.Base.db_execute_query(f"INSERT INTO {core_table} (datetime, channel_name, module_name) VALUES (:datetime, :channel_name, :module_name)", mes_donnees)
                        if insert.rowcount > 0:
                            self._ctx.Logs.debug('Channel added to DB: channel=%s / module_name=%s',
                                                 channel_name, module_name)
                            return True
                        else:
                            return False
                    else:
                        return False

                case 'del':
                    mes_donnes = {'channel_name': channel_name, 'module_name': module_name}
                    response = await self._ctx.Base.db_execute_query(f"DELETE FROM {core_table} WHERE channel_name = :channel_name AND module_name = :module_name", mes_donnes)

                    if response.rowcount > 0:
                        self._ctx.Logs.debug('Channel deleted from DB: channel=%s / module: %s',
                                             channel_name, module_name)
                        return True
                    else:
                        return False

        except Exception as err:
            self._ctx.Logs.error('GeneralError: %s', err)
            return False

    async def db_join_saved_channels(self) -> None:
        """## Joining saved channels"""
        exec_query = await self._ctx.Base.db_execute_query(f'SELECT distinct channel_name FROM {self._ctx.Config.TABLE_CHANNEL}')
        result_query = exec_query.fetchall()

        if result_query:
            for chan_name in result_query:
                chan = chan_name[0]
                await self._ctx.Irc.Protocol.send_sjoin(channel=chan)
