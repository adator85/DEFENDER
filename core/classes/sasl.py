from typing import Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from core.definition import MSasl
    from core.loader import Loader

class Sasl:

    DB_SASL: list['MSasl'] = []

    def __init__(self, loader: 'Loader'):
        self.Logs = loader.Logs # logger

    def insert_sasl_client(self, psasl: 'MSasl') -> bool:
        """Insert a new Sasl authentication

        Args:
            new_user (UserModel): New userModel object

        Returns:
            bool: True if inserted
        """

        if psasl is None:
            return False

        sasl_obj = self.get_sasl_obj(psasl.client_uid)

        if sasl_obj is not None:
            # User already created return False
            return False

        self.DB_SASL.append(psasl)

        return True

    def delete_sasl_client(self, client_uid: str) -> bool:
        """Delete the User starting from the UID

        Args:
            uid (str): UID of the user

        Returns:
            bool: True if deleted
        """

        sasl_obj = self.get_sasl_obj(client_uid)

        if sasl_obj is None:
            return False

        self.DB_SASL.remove(sasl_obj)

        return True

    def get_sasl_obj(self, client_uid: str) -> Optional['MSasl']:
        """Get sasl client Object model

        Args:
            client_uid (str): UID of the client

        Returns:
            UserModel|None: The SASL Object | None
        """

        for record in self.DB_SASL:
            if record.client_uid == client_uid:
                return record

        return None
