import yaml
import yaml.scanner
from os import sep
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.loader import Loader


class Translation:

    def __init__(self, loader: 'Loader') -> None:
        self.Logs = loader.Logs
        self.Settings = loader.Settings
        return None

    def get_translation(self) -> dict[str, list[list[str]]]:
        try:
            translation: dict[str, list[list[str]]] = dict()
            sfs: dict[str, list[list[str]]] = {}

            module_translation_directory = Path("mods")
            core_translation_directory = Path("core")
            sfs_core = self.get_subfolders_name(core_translation_directory.__str__())
            sfs_module = self.get_subfolders_name(module_translation_directory.__str__())

            # Combine the 2 dict
            for d in (sfs_core, sfs_module):
                for k, v in d.items():
                    sfs.setdefault(k, []).extend(v)

            loaded_files: list[str] = []

            for module, filenames in sfs.items():
                translation[module] = []
                for filename in filenames:
                    with open(f"{filename}", "r", encoding="utf-8") as fyaml:
                        data: dict[str, list[dict[str, str]]] = yaml.safe_load(fyaml)

                    if not isinstance(data, dict):
                        continue

                    for key, list_trad in data.items():
                        for vlist in list_trad:
                            translation[module].append([vlist["orig"], vlist["trad"]])

                    loaded_files.append(f"{filename}")

            return translation

        except yaml.scanner.ScannerError as se:
            self.Logs.error(f"[!] {se} [!]")
            return {}
        except yaml.YAMLError as ye:
            if hasattr(ye, 'problem_mark'):
                mark = ye.problem_mark
                self.Logs.error(f"Error YAML: {ye.with_traceback(None)}")
                self.Logs.error("Error position: (%s:%s)" % (mark.line+1, mark.column+1))
            return {}
        except yaml.error.MarkedYAMLError as me:
            self.Logs.error(f"[!] {me} [!]")
            return {}
        except Exception as err:
            self.Logs.error(f'General Error: {err}', exc_info=True)
            return {}

        finally:
            self.Logs.debug("Translation files loaded")
            for f in loaded_files:
                self.Logs.debug(f"   - {f}")

    def get_subfolders_name(self, directory: str) -> dict[str, list[str]]:
        try:
            translation_information: dict[str, list[str]] = dict()
            main_directory = Path(directory)

            # Init the dictionnary
            for subfolder in main_directory.rglob(f'*language{sep}*{sep}*.yaml'):
                if subfolder.name != '__pycache__':
                    translation_information[subfolder.parent.name.lower()] = []
                    

            for subfolder in main_directory.rglob(f'*language{sep}*{sep}*.yaml'):
                if subfolder.name != '__pycache__':
                    translation_information[subfolder.parent.name.lower()].append(subfolder)
           
            return translation_information

        except Exception as err:
            self.Logs.error(f'General Error: {err}')
            return {}
