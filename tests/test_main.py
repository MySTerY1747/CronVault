#  conftest.py
#  unit tests for main function of the program

from json import dumps, loads
import os

import CronVault.utils.utils
import pytest
from pathlib import Path


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
        "-n",
        "--name",
        "-m",
        "--max-backup-size",
        "-p",
        "--path",
        "-d",
        "--destination",
        "-f",
        "--naming-format",
        "-t",
        "--time-period",
    ]
    help_command: str = "python3 src/CronVault/main.py create -h"
    result: str = os.popen(help_command).read()
    for option in options:
        assert option in result.lower()


def test_name_unique(mocker):
    mock_expanduser = mocker.patch("CronVault.utils.utils.os.path.expanduser")
    mock_expanduser.return_value = "/Users/stefanos/.config/CronVault/"

    mock_os_path_exists = mocker.patch("CronVault.utils.utils.os.path.exists")
    mock_os_path_exists.return_value = True

    mock_listdir = mocker.patch("CronVault.utils.utils.os.listdir")
    mock_listdir.return_value = ["Backup1.json", "Backup2.json", "Backup3.json"]

    result: str = CronVault.utils.utils.parse_name("Backup 4")

    assert result == "Backup 4"
    mock_listdir.assert_called_once_with("/Users/stefanos/.config/CronVault/")


def test_add_duplicate_name(mocker):
    mock_expanduser = mocker.patch("CronVault.utils.utils.os.path.expanduser")
    mock_expanduser.return_value = "/Users/stefanos/.config/CronVault/"

    mock_os_path_exists = mocker.patch("CronVault.utils.utils.os.path.exists")
    mock_os_path_exists.return_value = True

    mock_listdir = mocker.patch("CronVault.utils.utils.os.listdir")
    mock_listdir.return_value = ["Backup1.json", "Backup2.json", "Backup3.json"]

    with pytest.raises(ValueError):
        CronVault.utils.utils.parse_name("Backup3")

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
        CronVault.utils.utils.parse_path("")


def test_path_exists_wrong_format():
    with pytest.raises(OSError):
        CronVault.utils.utils.parse_path("124 \\ 54 kd & # (! ")
    with pytest.raises(AssertionError):
        CronVault.utils.utils.parse_path("")


def test_path_exists_nonexistent(mocker):
    mock_os_path_exists = mocker.patch("CronVault.utils.utils.os.path.exists")
    mock_os_path_exists.return_value = False

    with pytest.raises(OSError):
        CronVault.utils.utils.parse_path("/non/existent/path")


def test_path_exists_existent(mocker):
    mock_os_path_exists = mocker.patch("CronVault.utils.utils.os.path.exists")
    mock_os_path_exists.return_value = True

    assert (
        CronVault.utils.utils.parse_path("/definitely/real/directory")
        == "/definitely/real/directory"
    )


def test_parse_name_format_long_name():
    with pytest.raises(AssertionError):
        CronVault.utils.utils.parse_name_format(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )


def test_parse_name_format_datetime():
    input_parameter: str = "%y test 123"
    result: str = CronVault.utils.utils.parse_name_format(input_parameter)
    assert result == "%y_test_123"


def test_parse_name_format_invalid_filename():
    input_parameter: str = "abc:548?"
    result: str = CronVault.utils.utils.parse_name_format(input_parameter)
    assert result == "abc_548_"


@pytest.mark.parametrize(
    "input_period, expected",
    [
        ("4m30s", 4 * 60 + 30),
        ("5 days", 60 * 60 * 24 * 5),
        ("5 days 10 hours", (60 * 60 * 24 * 5) + (60 * 60 * 10)),
        ("172 hrs", 60 * 60 * 172),
        ("10 weeks", 60 * 60 * 24 * 7 * 10),
        ("10w", 60 * 60 * 24 * 7 * 10),
    ],
)
def test_parse_time_period(input_period: str, expected: int):
    assert CronVault.utils.utils.parse_time_period(input_period) == expected


def test_parse_time_period_error():
    empty_input: str = ""
    unknown_values: str = "Alice and Bob"

    with pytest.raises(ValueError):
        CronVault.utils.utils.parse_time_period(empty_input)
    with pytest.raises(ValueError):
        CronVault.utils.utils.parse_time_period(unknown_values)


@pytest.mark.parametrize(
    "source_directory, expected_output",
    [
        ("~/TestDirectory/our_target_directory", "our_target_directory"),
        ("~/TestDirectory/our_target_directory/", "our_target_directory"),
        ("/test/", "test"),
        ("ABC", "ABC"),
        ("/test/directory with spaces/target/", "target"),
    ],
)
def test_default_backup_name(source_directory: str, expected_output: str, mocker):
    mocker.patch("CronVault.utils.utils.parse_name", side_effect=lambda x: x)

    assert (
        CronVault.utils.utils.get_default_backup_name(source_directory)
        == expected_output
    )


@pytest.mark.parametrize(
    "source_directory, expected_output",
    [
        ("~/TestDirectory/our_target_directory", "our_target_directory_4"),
        ("~/TestDirectory/our_target_directory/", "our_target_directory_3"),
        ("/test/", "test_2"),
        ("ABC", "ABC_1"),
        ("/test/directory with spaces/target/", "target_4"),
    ],
)
def test_default_backup_name_not_unique(
    #  a recursively mocked test with a closure
    #  I can't decide if this is the best code I've ever written
    #  or the absolute worst...
    mocker,
    source_directory: str,
    expected_output: str,
):
    def mock_parse_name_generator(expected_output_name: str):
        def mock_parse_name_specified(name: str):
            if name == expected_output_name:
                return name
            else:
                raise ValueError(f"Invalid name: {name}")

        return mock_parse_name_specified

    mocker.patch(
        "CronVault.utils.utils.parse_name",
        side_effect=mock_parse_name_generator(expected_output),
    )
    try:
        assert (
            CronVault.utils.utils.get_default_backup_name(source_directory)
            == expected_output
        )
    except RecursionError:
        raise ValueError(
            f"Recursion error. {source_directory} never turned into {expected_output}"
        )


def test_convert_args_json():
    input_dict = {
        "name": "Test1",
        "max_backup_size": 512000,
        "path": "~/Downloads/Test",
        "name_format": "Test1 %Y-%m-%M",
        "destination": "~/Documents/Test",
        "time_period": 2_592_000,
    }

    output_dict = input_dict.copy()
    output_dict["last_known_backup"] = None
    output_dict["total_backup_count"] = 0
    output_dict["status"] = "active"

    expected_output = dumps(output_dict)

    assert CronVault.utils.utils.convert_user_args_json(**input_dict) == expected_output


def test_config_path(tmp_path):
    result = CronVault.utils.utils.get_config_path("myconfig", tmp_path)

    assert result == tmp_path / "myconfig.json"


def test_config_path_raises_when_file_exists(tmp_path):
    existing_file: Path = tmp_path / "test.json"
    existing_file.write_text("this file exists already")

    with pytest.raises(ValueError):
        CronVault.utils.utils.get_config_path("test", tmp_path)


def test_config_path_dir_missing(tmp_path):
    new_dir: Path = tmp_path / "configs"

    result = CronVault.utils.utils.get_config_path("test", new_dir)

    assert new_dir.exists()
    assert result == new_dir / "test.json"


def test_write_file_writes_contents(tmp_path):
    file_path = tmp_path / "output.json"

    CronVault.utils.utils.write_file(file_path, '{"a": 1}')

    assert file_path.exists()
    assert file_path.read_text() == '{"a": 1}'


def test_filter_active(generate_test_configs):
    configs = generate_test_configs
    active = CronVault.utils.utils.filter_configs_active(configs)
    assert len(active) == 3
    assert all(config["status"] == "active" for config in active)


def test_filter_inactive(generate_test_configs):
    configs = generate_test_configs
    inactive = CronVault.utils.utils.filter_configs_inactive(configs)
    assert len(inactive) == 2
    assert all(config["status"] == "inactive" for config in inactive)


def test_print_configs(generate_test_configs, capsys):
    configs = generate_test_configs
    CronVault.utils.utils.print_configs(configs)
    captured = capsys.readouterr()
    for text in [
        "CONFIGS:",
        "• documents",
        "• photos",
        "• music",
        "• projects",
        "• notes",
        "active",
        "inactive",
    ]:
        assert text in captured.out


def test_get_all_backups_skips_invalid_json_files(
    generate_test_configs, populated_config_directory
):
    configs = generate_test_configs
    write_test_tmp_path: Path = populated_config_directory
    config_results = CronVault.utils.utils.get_all_backups(
        file_path=write_test_tmp_path
    )
    for config in configs:
        assert config in config_results
    assert len(config_results) == 5
    assert "broken" not in [config["name"] for config in config_results]


def test_activate_inactive_file(populated_config_directory):
    write_test_tmp_path = populated_config_directory
    CronVault.utils.utils.change_backup_status("photos", "active", write_test_tmp_path)
    assert (
        loads((write_test_tmp_path / "photos.json").read_text())["status"] == "active"
    )


def test_activate_active_file(populated_config_directory):
    write_test_tmp_path = populated_config_directory
    #  documents should already be active, testing for idempotency
    CronVault.utils.utils.change_backup_status(
        "documents", "active", write_test_tmp_path
    )
    assert (
        loads((write_test_tmp_path / "documents.json").read_text())["status"]
        == "active"
    )


def test_deactivate_active_file(populated_config_directory):
    write_test_tmp_path = populated_config_directory
    CronVault.utils.utils.change_backup_status(
        "documents", "inactive", write_test_tmp_path
    )
    #  main assert
    assert (
        loads((write_test_tmp_path / "documents.json").read_text())["status"]
        == "inactive"
    )
    #  test that other files remain unchanged
    for name, status in (
        ("photos", "inactive"),
        ("projects", "active"),
        ("music", "inactive"),
        ("notes", "active"),
    ):
        assert (
            loads((write_test_tmp_path / f"{name}.json").read_text())["status"]
            == status
        )


def test_activate_missing_file(tmp_path):
    assert (
        CronVault.utils.utils.change_backup_status(
            "non_existent_config", "active", tmp_path
        )
        is None
    )
    #  exited without crashing


def test_change_status_broken_file(populated_config_directory, caplog):
    write_test_tmp_path = populated_config_directory
    CronVault.utils.utils.change_backup_status("broken", "active", write_test_tmp_path)
    assert 'Config file "broken" is malformed or corrupted.' in caplog.text


def test_change_status_invalid_file(populated_config_directory, caplog):
    write_test_tmp_path = populated_config_directory
    CronVault.utils.utils.change_backup_status(
        "invalid_structure", "active", write_test_tmp_path
    )
    assert 'Config file "invalid_structure" is malformed or corrupted.' in caplog.text


def test_change_status_to_invalid_state(tmp_path, caplog):
    CronVault.utils.utils.change_backup_status(
        "non_existent_config", "wrong_value", tmp_path
    )
    assert '"wrong_value" is not a valid config status. Exiting' in caplog.text


def test_delete_backup_config(populated_config_directory):
    initial_file_count = len(list(populated_config_directory.iterdir()))
    CronVault.utils.utils.delete_backup("documents", populated_config_directory)
    assert len(list(populated_config_directory.iterdir())) == initial_file_count - 1
    dir_filenames = [file.name for file in populated_config_directory.iterdir()]
    for file in ("photos.json", "projects.json", "music.json", "notes.json"):
        assert file in dir_filenames


def test_delete_missing_backup_config(populated_config_directory, caplog):
    CronVault.utils.utils.delete_backup("missing_file", populated_config_directory)
    assert "No such config found" in caplog.text
