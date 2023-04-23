from io import BytesIO
from logger_tt import logger
import os
from pathlib import Path
import platform
import requests
import sys
import tarfile
from zipfile import ZipFile
from typing import Any, Dict, List, Optional, Tuple

from model.dialogue import (
    show_dialogue_conditional,
    show_fatal_error,
    show_information,
    show_warning,
)
from window.runner_panel import RunnerPanel

import shutil


class SteamcmdInterface:
    """
    Create SteamcmdInterface object to provide an interface for steamcmd functionality
    """

    def __init__(self, storage_path: str) -> None:
        logger.info("SteamcmdInterface initilizing...")
        self.steamcmd_path = Path(storage_path, "steamcmd").resolve()
        self.system = platform.system()
        self.steamcmd_mods_path = Path(storage_path, "steam").resolve()

        if self.system == "Darwin":
            self.steamcmd_url = (
                "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_osx.tar.gz"
            )
        elif self.system == "Linux":
            self.steamcmd_url = (
                "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
            )
        elif self.system == "Windows":
            self.steamcmd_url = (
                "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
            )
        else:
            show_fatal_error(
                "SteamcmdInterface",
                f"Found platform {self.system}. steamcmd is not supported on this platform.",
            )
            return

        if not os.path.exists(self.steamcmd_path):
            os.makedirs(self.steamcmd_path)

        if not os.path.exists(self.steamcmd_mods_path):
            os.makedirs(self.steamcmd_mods_path)

    def download_publishedfileids(
        self, appid: str, publishedfileids: list, runner: RunnerPanel
    ):
        """
        This function downloads a list of mods from a list publishedfileids

        https://developer.valvesoftware.com/wiki/SteamCMD

        :param appid: a Steam AppID to pass to steamcmd
        :param publishedfileids: list of publishedfileids
        """
        runner.message("Checking for steamcmd...")
        if self.steamcmd is not None:
            runner.message(
                f"Got it: {self.steamcmd}\n"
                + f"Downloading list of {str(len(publishedfileids))} "
                + f"publishedfileids to: {self.steamcmd_mods_path}"
            )
            script = [f"force_install_dir {self.steamcmd_mods_path}", "login anonymous"]
            for publishedfileid in publishedfileids:
                script.append(f"workshop_download_item {appid} " + publishedfileid)
            script.extend(
                [
                    # "validate",
                    "quit\n"
                ]
            )
            scripts_path = os.path.join(self.steamcmd_path, "scripts")
            if not os.path.exists(scripts_path):
                os.makedirs(scripts_path)
            script_path = os.path.join(scripts_path, "script.txt")
            with open(script_path, "w") as script_output:
                script_output.write("\n".join(script))
            runner.message(f"Compiled & using script: {script_path}")
            runner.execute(self.steamcmd, [f"+runscript {script_path}"])
            runner.process.waitForFinished()
        else:
            runner.message("steamcmd was not found. Please setup steamcmd first!")

    def get_steamcmd(
        self, symlink_source_path: str, reinstall: bool, runner: RunnerPanel
    ) -> None:
        installed = None
        if reinstall:
            runner.message("Existing steamcmd installation found!")
            runner.message(f"Deleting existing installation from: {self.steamcmd_path}")
            shutil.rmtree(self.steamcmd_path)
            os.makedirs(self.steamcmd_path)
        if self.system == "Windows":  # Windows
            self.steamcmd = os.path.join(self.steamcmd_path, "steamcmd.exe")
            if not os.path.exists(self.steamcmd):
                try:
                    runner.message(
                        f"Downloading & extracting steamcmd release from: {self.steamcmd_url}"
                    )
                    with ZipFile(
                        BytesIO(requests.get(self.steamcmd_url).content)
                    ) as zipobj:
                        zipobj.extractall(self.steamcmd_path)
                    runner.message(f"Installation completed")
                    installed = True
                except:
                    runner.message("Installation failed")
                    show_fatal_error(
                        "SteamcmdInterface",
                        f"Failed to download steamcmd for {self.system}",
                        f"Did the file/url change?\nDoes your environment have access to the internet?",
                    )
            else:
                runner.message("Steamcmd already installed...")
                show_warning(
                    "SteamcmdInterface",
                    f"A steamcmd runner already exists at: {self.steamcmd}",
                )
                answer = show_dialogue_conditional(
                    "Reinstall?",
                    "Would you like to reinstall steamcmd?",
                    f"Existing install: {self.steamcmd_path}",
                )
                if answer == "&Yes":
                    runner.message(f"Reinstalling steamcmd: {self.steamcmd_path}")
                    self.get_steamcmd(symlink_source_path, True, runner)
        else:  # Linux/MacOS
            self.steamcmd = os.path.join(self.steamcmd_path, "steamcmd.sh")
            if not os.path.exists(self.steamcmd):
                try:
                    runner.message(
                        f"Downloading & extracting steamcmd release from: {self.steamcmd_url}"
                    )
                    with requests.get(
                        self.steamcmd_url, stream=True
                    ) as rx, tarfile.open(fileobj=rx.raw, mode="r:gz") as tarobj:
                        tarobj.extractall(self.steamcmd_path)
                    runner.message(f"Installation completed")
                    installed = True
                except:
                    runner.message("Installation failed")
                    show_fatal_error(
                        "SteamcmdInterface",
                        f"Failed to download steamcmd for {self.system}",
                        f"Did the file/url change?\nDoes your environment have access to the internet?",
                    )
            else:
                runner.message("Steamcmd already installed...")
                show_warning(
                    "SteamcmdInterface",
                    f"A steamcmd runner already exists at: {self.steamcmd}",
                )
                answer = show_dialogue_conditional(
                    "Reinstall?",
                    "Would you like to reinstall steamcmd?",
                    f"Existing install: {self.steamcmd_path}",
                )
                if answer == "&Yes":
                    runner.message(f"Reinstalling steamcmd: {self.steamcmd_path}")
                    self.get_steamcmd(symlink_source_path, True, runner)
        if installed:
            workshop_content_path = os.path.join(
                self.steamcmd_mods_path, "steamapps", "workshop", "content"
            )
            if not os.path.exists(workshop_content_path):
                os.makedirs(workshop_content_path)
                runner.message(
                    f"Workshop content path does not exist. Creating for symlinking: {workshop_content_path}"
                )
            symlink_destination_path = os.path.join(workshop_content_path, "294100")
            runner.message(f"Symlink source : {symlink_source_path}")
            runner.message(f"Symlink destination: {symlink_destination_path}")
            if os.path.exists(symlink_destination_path):
                runner.message(
                    f"Symlink destination already exists! Please remove existing destination: {symlink_destination_path}"
                )
            else:
                answer = show_dialogue_conditional(
                    "Create symlink?",
                    "Would you like to create a symlink as followed?",
                    f"[{symlink_source_path}] -> " + symlink_destination_path,
                )
                if answer == "&Yes":
                    runner.message(
                        f"[{symlink_source_path}] -> " + symlink_destination_path
                    )
                    if self.system != "Windows":
                        os.symlink(
                            symlink_source_path,
                            symlink_destination_path,
                            target_is_directory=True,
                        )
                    else:
                        from _winapi import CreateJunction

                        CreateJunction(symlink_source_path, symlink_destination_path)


if __name__ == "__main__":
    sys.exit()