#  test_main.py
#  unit tests for main function of the program

import os
import CronVault.utils.utils
import pytest


def test_help():
    blurb: str = (
        "CronVault - Flexible Python-based backup automation tool via cron jobs"
    )
    help_command: str = "python3 src/CronVault/main.py -h"
    result: str = os.popen(help_command).read()
    assert blurb in result


def test_cli_args():
    options: list[str] = [
        "-h",
        "--help",
        "-v",
        "--verbose",
        "-n",
        "--name",
        "-m",
        "--max-backup-size",
    ]
    help_command: str = "python3 src/CronVault/main.py -h"
    result: str = os.popen(help_command).read()
    for option in options:
        assert option in result.lower()


def test_name_unique(mocker):
    mock_expanduser = mocker.patch("CronVault.utils.utils.os.path.expanduser")
    mock_expanduser.return_value = "/Users/stefanos/.config/CronVault/"

    mock_os_path_exists = mocker.patch("CronVault.utils.utils.os.path.exists")
    mock_os_path_exists.return_value = True

    mock_listdir = mocker.patch("CronVault.utils.utils.os.listdir")
    mock_listdir.return_value = ["Backup1", "Backup2", "Backup3"]

    result: bool = CronVault.utils.utils.parse_name("Backup 4")

    assert result is True
    mock_listdir.assert_called_once_with("/Users/stefanos/.config/CronVault/")


def test_add_duplicate_name(mocker):
    mock_expanduser = mocker.patch("CronVault.utils.utils.os.path.expanduser")
    mock_expanduser.return_value = "/Users/stefanos/.config/CronVault/"

    mock_os_path_exists = mocker.patch("CronVault.utils.utils.os.path.exists")
    mock_os_path_exists.return_value = True

    mock_listdir = mocker.patch("CronVault.utils.utils.os.listdir")
    mock_listdir.return_value = ["Backup1", "Backup2", "Backup3"]

    result: bool = CronVault.utils.utils.parse_name("Backup3")

    assert result is False
    mock_listdir.assert_called_once_with("/Users/stefanos/.config/CronVault/")


def test_add_empty_name():
    with pytest.raises(AssertionError):
        CronVault.utils.utils.parse_name("")


@pytest.mark.parametrize(
    "size, expected",
    [
        ("15", 15),
        ("15b", 15),
        ("15kB", 15 * 1024),
        ("15k", 15 * 1024),
        ("15mB", 15 * 1024**2),
        ("15M", 15 * 1024**2),
    ],
)
def test_parse_size(size: str, expected: int):
    assert CronVault.utils.utils.parse_size(size) == expected


def test_parse_size_incorrect_input():
    with pytest.raises(ValueError):
        CronVault.utils.utils.parse_size("Mb15")
    with pytest.raises(ValueError):
        CronVault.utils.utils.parse_size("INCORRECT_VALUE")


def test_path_exists_empty():
    with pytest.raises(AssertionError):
        CronVault.utils.utils.parse_folder_name("")


def test_path_exists_wrong_format():
    with pytest.raises(AssertionError):
        CronVault.utils.utils.parse_folder_name("124 \\ 54 kd & # (! ")
    with pytest.raises(AssertionError):
        CronVault.utils.utils.parse_folder_name("")


def test_path_exists_nonexistent(mocker):
    mock_os_path_exists = mocker.patch("CronVault.utils.utils.os.path.exists")
    mock_os_path_exists.return_value = False

    with pytest.raises(OSError):
        CronVault.utils.utils.parse_folder_name("/non/existent/path")
