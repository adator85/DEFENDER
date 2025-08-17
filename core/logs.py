import logging
from os import path, makedirs, sep

class ServiceLogging:

        def __init__(self, loggin_name: str = "defender"):
            """Create the Logging object
            """
            self.OS_SEP = sep
            self.LOGGING_NAME = loggin_name
            self.DEBUG_LEVEL, self.DEBUG_FILE_LEVEL, self.DEBUG_STDOUT_LEVEL = (10, 10, 10)
            self.SERVER_PREFIX = None
            self.LOGGING_CONSOLE = True

            self.LOG_FILTERS: list[str] = ['PING', f":{self.SERVER_PREFIX}auth", "['PASS'"]

            self.file_handler = None
            self.stdout_handler = None

            self.logs: logging.Logger = self.start_log_system()

        def get_logger(self) -> logging.Logger:

             logs_obj: logging.Logger = self.logs

             return logs_obj

        def remove_logger(self) -> None:

            # Récupérer le logger
            logger = logging.getLogger(self.LOGGING_NAME)

            # Retirer tous les gestionnaires du logger et les fermer
            for handler in logger.handlers[:]:  # Utiliser une copie de la liste
                # print(handler)
                logger.removeHandler(handler)
                handler.close()

            # Supprimer le logger du dictionnaire global
            logging.Logger.manager.loggerDict.pop(self.LOGGING_NAME, None)

            return None

        def start_log_system(self) -> logging.Logger:

            os_sep = self.OS_SEP
            logging_name = self.LOGGING_NAME
            debug_level = self.DEBUG_LEVEL
            debug_file_level = self.DEBUG_FILE_LEVEL
            debug_stdout_level = self.DEBUG_STDOUT_LEVEL

            # Create folder if not available
            logs_directory = f'logs{os_sep}'
            if not path.exists(f'{logs_directory}'):
                makedirs(logs_directory)

            # Init logs object
            logs = logging.getLogger(logging_name)
            logs.setLevel(debug_level)

            # Add Handlers
            self.file_handler = logging.FileHandler(f'logs{os_sep}{logging_name}.log',encoding='UTF-8')
            self.file_handler.setLevel(debug_file_level)

            self.stdout_handler = logging.StreamHandler()
            self.stdout_handler.setLevel(debug_stdout_level)

            # Define log format
            formatter = logging.Formatter(
                fmt='%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(funcName)s:%(lineno)d)',
                datefmt='%Y-%m-%d %H:%M:%S'
                )

            # Apply log format
            self.file_handler.setFormatter(formatter)
            self.stdout_handler.setFormatter(formatter)

            # Add handler to logs
            logs.addHandler(self.file_handler)
            logs.addHandler(self.stdout_handler)

            # Apply the filter
            logs.addFilter(self.replace_filter)

            logs.info(f'#################### STARTING {self.LOGGING_NAME} ####################')

            return logs

        def set_stdout_handler_level(self, level: int) -> None:
            self.stdout_handler.setLevel(level)

        def set_file_handler_level(self, level: int) -> None:
            self.file_handler.setLevel(level)

        def replace_filter(self, record: logging.LogRecord) -> bool:

            response = True
            filter: list[str] = ['PING', f":{self.SERVER_PREFIX}auth", "['PASS'"]

            # record.msg = record.getMessage().replace("PING", "[REDACTED]")
            # if self.LOGGING_CONSOLE:
            #     print(record.getMessage())

            for f in filter:
                if f in record.getMessage():
                    response = False

            return response  # Retourne True pour permettre l'affichage du message
