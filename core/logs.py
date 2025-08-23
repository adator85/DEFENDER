import logging
from os import path, makedirs, sep
from typing import Optional

class ServiceLogging:

        def __init__(self, loggin_name: str = "defender"):
            """Create the Logging object
            """
            self.OS_SEP = sep
            self.LOGGING_NAME = loggin_name
            self.remove_logger(loggin_name) # Remove logger if exists

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

        def remove_logger(self, logger_name: Optional[str] = None) -> None:
            
            if logger_name is None:
                logger_name = self.LOGGING_NAME

            # Récupérer le logger
            logger = logging.getLogger(logger_name)

            # Retirer tous les gestionnaires du logger et les fermer
            for handler in logger.handlers[:]:  # Utiliser une copie de la liste
                # print(handler)
                logger.removeHandler(handler)
                handler.close()

            # Supprimer le logger du dictionnaire global
            logging.Logger.manager.loggerDict.pop(logger_name, None)

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
            self.logs.debug(f"[STDOUT LEVEL] New level {level}")
            self.stdout_handler.setLevel(level)

        def set_file_handler_level(self, level: int) -> None:
            self.logs.debug(f"[LOG FILE LEVEL] new level {level}")
            self.file_handler.setLevel(level)

        def update_handler_format(self, debug_hard: bool = False) -> None:
            """Updating logging formatter format!

            Args:
                debug_hard (bool, optional): If true you will have filename, 
                function name and the line number. Defaults to False.
            """
            # Updating logging formatter
            if debug_hard:
                new_formatter = logging.Formatter(
                    fmt='%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(funcName)s:%(lineno)d)',
                    datefmt='%Y-%m-%d %H:%M:%S'
                    )
            else:
                new_formatter = logging.Formatter(
                    fmt='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                    )

            for handler in self.logs.handlers:
                handler.setFormatter(new_formatter)

        def regenerate_handlers(self, logger: logging.Logger) -> logging.Logger:
            os_sep = self.OS_SEP
            logging_name = self.LOGGING_NAME
            debug_file_level = self.DEBUG_FILE_LEVEL
            debug_stdout_level = self.DEBUG_STDOUT_LEVEL

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
            logger.addHandler(self.file_handler)
            logger.addHandler(self.stdout_handler)

            # Apply the filter
            logger.addFilter(self.replace_filter)
            logger.info(f'REGENRATING LOGGER {self.LOGGING_NAME}')

            return logger

        def replace_filter(self, record: logging.LogRecord) -> bool:

            response = True
            filter: list[str] = self.LOG_FILTERS

            # record.msg = record.getMessage().replace("PING", "[REDACTED]")
            # if self.LOGGING_CONSOLE:
            #     print(record.getMessage())

            for f in filter:
                if f in record.getMessage():
                    response = False

            return response  # Retourne True to write the log!
