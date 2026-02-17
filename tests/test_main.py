#  test_main.py
#  unit tests for main function of the program

import os
import CronVault.utils.utils


def test_help():
    blurb: str = (
        "CronVault - Flexible Python-based backup automation tool via cron jobs"
    )
    help_command: str = "python3 src/CronVault/main.py -h"
    result: str = os.popen(help_command).read()
    assert blurb in result


def test_cli_args():
    options: list[str] = [
        "-h, --help",
        "-v, --verbose",
        "-n, --name",
    ]
    help_command: str = "python3 src/CronVault/main.py -h"
    result: str = os.popen(help_command).read()
    for option in options:
        assert option in result


def test_name_unique(mocker):
    mock_expanduser = mocker.patch("CronVault.utils.utils.os.path.expanduser")
    mock_expanduser.return_value = "/Users/stefanos/.config/CronVault/"

    mock_listdir = mocker.patch("CronVault.utils.utils.os.listdir")
    mock_listdir.return_value = ["Backup1", "Backup2", "Backup3"]

    result: bool = CronVault.utils.utils.check_if_name_unique("Backup 4")

    assert result is True
    mock_listdir.assert_called_once_with("/Users/stefanos/.config/CronVault/")


def test_add_duplicate_name(mocker):
    mock_expanduser = mocker.patch("CronVault.utils.utils.os.path.expanduser")
    mock_expanduser.return_value = "/Users/stefanos/.config/CronVault/"

    mock_listdir = mocker.patch("CronVault.utils.utils.os.listdir")
    mock_listdir.return_value = ["Backup1", "Backup2", "Backup3"]

    result: bool = CronVault.utils.utils.check_if_name_unique("Backup3")

    assert result is False
    mock_listdir.assert_called_once_with("/Users/stefanos/.config/CronVault/")


def test_add_empty_name():
    pass
