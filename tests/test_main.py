#  conftest.py
#  unit tests for main function of the program

from json import dumps, loads
import os
from unittest.mock import MagicMock
from CronVault.cli.parse_functions import (
    parse_name,
    parse_name_format,
    parse_path,
    parse_size,
    parse_time_period,
)
from CronVault.core.config import (
    get_default_backup_name,
    get_all_backups,
    get_backup_frequency_from_config,
    get_config_path,
    generate_default_config,
    change_backup_status,
    create_backup_from_args,
    delete_backup,
    filter_configs_active,
    print_configs,
    filter_configs_inactive,
    interactive_config_creator,
    is_name_duplicate,
    fill_missing_create_args,
    write_file,
    convert_user_args_json,
)
from CronVault.core.backup import (
    run_backup_if_needed,
    cleanup_failed_backup,
    find_oldest_backup,
    perform_backup,
    get_directory_size,
    generate_cronvault_marker,
)
from CronVault.core.cron import add_cron_job, ensure_single_cron_job
from CronVault.core.constants import (
    NAME_DEFAULT,
    CRONVAULT_MARKER_FILENAME,
    CONFIG_FILE_NAME,
    DEFAULT_BACKUP_CHECK_INTERVAL_MINUTES,
    FIFTY_GB,
)
import pytest
from pathlib import Path
from datetime import datetime


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
    #  I'm not using `cronvault` here, because it would break the CI/CD pipeline on GitHub
    help_command: str = "python3 src/CronVault/main.py create -h"
    result: str = os.popen(help_command).read()
    for option in options:
        assert option in result.lower()


def test_name_unique(tmp_path: Path):
    for filename in ("Backup1.json", "Backup2.json", "Backup3.json"):
        (tmp_path / filename).touch()

    assert is_name_duplicate("Backup4", tmp_path) is False


def test_add_duplicate_name(tmp_path: Path):
    for filename in ("Backup1.json", "Backup2.json", "Backup3.json"):
        (tmp_path / filename).touch()

    assert is_name_duplicate("Backup3", tmp_path) is True


def test_parse_name_default():
    assert parse_name("") == NAME_DEFAULT


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
    assert parse_size(size) == expected


def test_parse_size_incorrect_input():
    with pytest.raises(ValueError):
        parse_size("Mb15")
    with pytest.raises(ValueError):
        parse_size("INCORRECT_VALUE")


def test_path_exists_wrong_format():
    with pytest.raises(OSError):
        parse_path("124 \\ 54 kd & # (! ")


def test_path_exists_nonexistent():
    with pytest.raises(OSError):
        parse_path("/non/existent/path")


def test_path_exists_existent(tmp_path):
    assert parse_path(str(tmp_path)) == str(tmp_path)


def test_parse_name_format_long_name():
    with pytest.raises(ValueError):
        parse_name_format(
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        )


def test_parse_name_format_datetime():
    input_parameter: str = "%y test 123"
    result: str = parse_name_format(input_parameter)
    assert result == "%y_test_123"


def test_parse_name_format_invalid_filename():
    input_parameter: str = "abc:548?"
    result: str = parse_name_format(input_parameter)
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
    assert parse_time_period(input_period) == expected


def test_parse_time_period_error():
    empty_input: str = ""
    unknown_values: str = "Alice and Bob"

    with pytest.raises(ValueError):
        parse_time_period(empty_input)
    with pytest.raises(ValueError):
        parse_time_period(unknown_values)


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
def test_default_backup_name(
    tmp_path: Path, source_directory: str, expected_output: str
):
    assert get_default_backup_name(source_directory, tmp_path) == expected_output


@pytest.mark.parametrize(
    "source_directory, config_dir_files, expected_output",
    [
        (
            "~/TestDirectory/our_target_directory",
            [
                "our_target_directory",
                "our_target_directory_1",
                "our_target_directory_2",
                "our_target_directory_3",
            ],
            "our_target_directory_4",
        ),
        ("/test/", ["test", "test_1"], "test_2"),
        ("ABC", ["ABC"], "ABC_1"),
        (
            "/test/directory with spaces/target/",
            ["target", "target_1", "target_2", "target_3"],
            "target_4",
        ),
    ],
)
def test_default_backup_name_not_unique_new(
    tmp_path: Path, source_directory, config_dir_files, expected_output
):
    for file in config_dir_files:
        (tmp_path / f"{file}.json").touch()
    assert get_default_backup_name(source_directory, tmp_path) == expected_output


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

    assert convert_user_args_json(**input_dict) == expected_output


def test_config_path(tmp_path):
    result = get_config_path("myconfig", tmp_path)

    assert result == tmp_path / "myconfig.json"


def test_config_path_raises_when_file_exists(tmp_path):
    existing_file: Path = tmp_path / "test.json"
    existing_file.write_text("this file exists already")

    with pytest.raises(ValueError):
        get_config_path("test", tmp_path)


def test_config_path_dir_missing(tmp_path):
    new_dir: Path = tmp_path / "configs"

    result = get_config_path("test", new_dir)

    assert new_dir.exists()
    assert result == new_dir / "test.json"


def test_write_file_writes_contents(tmp_path):
    file_path = tmp_path / "output.json"

    write_file(file_path, '{"a": 1}')

    assert file_path.exists()
    assert file_path.read_text() == '{"a": 1}'


def test_filter_active(generate_test_configs):
    configs = generate_test_configs
    active = filter_configs_active(configs)
    assert len(active) == 3
    assert all(config["status"] == "active" for config in active)


def test_filter_inactive(generate_test_configs):
    configs = generate_test_configs
    inactive = filter_configs_inactive(configs)
    assert len(inactive) == 2
    assert all(config["status"] == "inactive" for config in inactive)


def test_print_configs(generate_test_configs, capsys):
    configs = generate_test_configs
    print_configs(configs)
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
    config_results = get_all_backups(file_path=write_test_tmp_path)
    for config in configs:
        assert config in config_results
    assert len(config_results) == 5
    assert "broken" not in [config["name"] for config in config_results]


def test_activate_inactive_file(populated_config_directory):
    write_test_tmp_path = populated_config_directory
    change_backup_status("photos", "active", write_test_tmp_path)
    assert (
        loads((write_test_tmp_path / "photos.json").read_text())["status"] == "active"
    )


def test_activate_active_file(populated_config_directory):
    write_test_tmp_path = populated_config_directory
    #  documents should already be active, testing for idempotency
    change_backup_status("documents", "active", write_test_tmp_path)
    assert (
        loads((write_test_tmp_path / "documents.json").read_text())["status"]
        == "active"
    )


def test_deactivate_active_file(populated_config_directory):
    write_test_tmp_path = populated_config_directory
    change_backup_status("documents", "inactive", write_test_tmp_path)
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
    assert change_backup_status("non_existent_config", "active", tmp_path) is None
    #  exited without crashing


def test_change_status_broken_file(populated_config_directory, caplog):
    write_test_tmp_path = populated_config_directory
    change_backup_status("broken", "active", write_test_tmp_path)
    assert 'Config file "broken" is malformed or corrupted.' in caplog.text


def test_change_status_invalid_file(populated_config_directory, caplog):
    write_test_tmp_path = populated_config_directory
    change_backup_status("invalid_structure", "active", write_test_tmp_path)
    assert 'Config file "invalid_structure" is malformed or corrupted.' in caplog.text


def test_change_status_to_invalid_state(tmp_path, caplog):
    change_backup_status("non_existent_config", "wrong_value", tmp_path)
    assert '"wrong_value" is not a valid config status. Exiting' in caplog.text


def test_delete_backup_config(populated_config_directory):
    initial_file_count = len(list(populated_config_directory.iterdir()))
    delete_backup("documents", populated_config_directory)
    assert len(list(populated_config_directory.iterdir())) == initial_file_count - 1
    dir_filenames = {file.name for file in populated_config_directory.iterdir()}
    for file in ("photos.json", "projects.json", "music.json", "notes.json"):
        assert file in dir_filenames
    assert "documents.json" not in dir_filenames


def test_delete_missing_backup_config(populated_config_directory, caplog):
    delete_backup("missing_file", populated_config_directory)
    assert "No such config found" in caplog.text


def test_get_directory_size(tmp_path):
    sentence_one = "abc"
    sentence_two = "defg"
    (tmp_path / "a.txt").write_text(sentence_one)
    (tmp_path / "b.txt").write_text(sentence_two)

    assert get_directory_size(tmp_path) == len(sentence_one) + len(sentence_two)


def test_get_directory_size_with_subdirectories(tmp_path):
    sentence_one = "abc"
    sentence_two = "defg"
    sentence_three = "hijk"
    (tmp_path / "a.txt").write_text(sentence_one)
    (tmp_path / "b.txt").write_text(sentence_two)

    sub_dir = tmp_path / "sub_dir"
    sub_dir.mkdir()
    (sub_dir / "c.txt").write_text(sentence_three)

    assert get_directory_size(tmp_path) == len(sentence_one) + len(sentence_two) + len(
        sentence_three
    )


def test_run_backup_if_needed(single_valid_config_directory, mocker):
    mock_perform_backup = mocker.patch("perform_backup")
    mock_perform_backup.return_value = True

    initial_config_contents = loads(
        (single_valid_config_directory / "documents.json").read_text()
    )
    initial_backup_count = initial_config_contents["total_backup_count"]

    run_backup_if_needed(
        "documents", skip_checks=False, file_path=single_valid_config_directory
    )

    config_contents_after_func = loads(
        (single_valid_config_directory / "documents.json").read_text()
    )

    called_config = mock_perform_backup.call_args.args[0]
    assert called_config["name"] == "documents"
    assert config_contents_after_func["total_backup_count"] == initial_backup_count + 1
    assert (
        datetime.now()
        - datetime.fromisoformat(config_contents_after_func["last_known_backup"])
    ).total_seconds() < 1


def test_run_backup_file_edge_cases(populated_config_directory, mocker, caplog):
    #  documents should be backed up, same with notes
    #  photos, music, projects should not (photos & music inactive, projects active but recently backed up)
    #  Broken/invalid files should be skipped
    mock_perform_backup = mocker.patch("perform_backup")
    mock_perform_backup.return_value = True

    all_filenames = [
        "documents",
        "photos",
        "music",
        "projects",
        "notes",
        "broken",
        "invalid_structure",
    ]

    for name in all_filenames:
        run_backup_if_needed(
            name, skip_checks=False, file_path=populated_config_directory
        )

    called_configs = [call.args[0] for call in mock_perform_backup.call_args_list]
    assert len(called_configs) == 2
    assert called_configs[0]["name"] == "documents"
    assert called_configs[1]["name"] == "notes"
    #  photos, music, projects, broken, and invalid were all skipped
    assert "broken" in caplog.text
    assert "invalid_structure" in caplog.text


def test_run_backup_forced(populated_config_directory, mocker, caplog):
    #  test that all backups are performed, despite elapsed-time or activity status, when forced flag True
    mock_perform_backup = mocker.patch("perform_backup")
    mock_perform_backup.return_value = True

    all_filenames = [
        "documents",
        "photos",
        "music",
        "projects",
        "notes",
        "broken",
        "invalid_structure",
    ]

    for name in all_filenames:
        run_backup_if_needed(
            name, skip_checks=True, file_path=populated_config_directory
        )

    assert mock_perform_backup.call_count == 5
    #  photos, music, projects, broken, and invalid were all skipped
    assert "broken" in caplog.text
    assert "invalid_structure" in caplog.text


def test_run_backup_if_needed_perform_fails(populated_config_directory, mocker):
    mock_perform_backup = mocker.patch("perform_backup")
    mock_perform_backup.return_value = False

    initial_config_contents = loads(
        (populated_config_directory / "documents.json").read_text()
    )

    run_backup_if_needed(
        "documents", skip_checks=False, file_path=populated_config_directory
    )

    config_contents_after_func = loads(
        (populated_config_directory / "documents.json").read_text()
    )
    assert config_contents_after_func == initial_config_contents


def test_find_oldest_backup(tmp_path):
    #  checks that non-CronVault dirs are skipped, and oldest valid dir returned
    for dir_name in ["dir1", "dir2", "dir3", "dirCRONVAULT_older", "dirCRONVAULT"]:
        (tmp_path / dir_name).mkdir()
        if "CRON" in dir_name:
            marker = loads(generate_cronvault_marker(tmp_path, tmp_path))
            marker["backup_datetime"] = (
                "2023-01-01T00:00:00"
                if ("older" in dir_name)
                else "2025-01-01T00:00:00"
            )
            (tmp_path / dir_name / CRONVAULT_MARKER_FILENAME).write_text(dumps(marker))
    assert find_oldest_backup(tmp_path) == (tmp_path / "dirCRONVAULT_older")


def test_find_oldest_backup_no_cronvault_dirs(tmp_path):
    #  checks that non-CronVault dirs are skipped, and oldest valid dir returned
    for dir_name in ["dir1", "dir2", "dir3", "dir4", "dir5"]:
        (tmp_path / dir_name).mkdir()
        if "CRON" in dir_name:
            (tmp_path / dir_name / CRONVAULT_MARKER_FILENAME).write_text(
                generate_cronvault_marker(tmp_path, tmp_path)
            )
    assert find_oldest_backup(tmp_path) is None


def test_generate_cronvault_marker():
    generated_marker = loads(generate_cronvault_marker(Path("pathA"), Path("pathB")))
    assert generated_marker["original_folder"] == "pathA"
    time_difference = datetime.now() - datetime.fromisoformat(
        generated_marker["backup_datetime"]
    )
    assert time_difference.total_seconds() <= 1
    assert generated_marker["backup_folder_path"] == "pathB"


#  no point in testing `get_device_free_space`, it would be testing core Python lib functions, no need


def test_cleanup_failed_backup(tmp_path):
    existing_dir = tmp_path / "existing_dir"
    existing_dir.mkdir()
    (existing_dir / "important_file.txt").write_text("Important!")
    initial_size = get_directory_size(
        tmp_path
    )  #  function has already been tested, and is therefore safe and functional
    sub_dir: Path = tmp_path / "test_subdir"
    sub_dir.mkdir()
    for filename in ["test1.txt", "test2.txt", "test3.txt"]:
        (sub_dir / filename).write_text("This is a large file.\n" * 10)
    cleanup_failed_backup(sub_dir)
    final_size = get_directory_size(tmp_path)
    assert final_size == initial_size
    assert existing_dir.exists()
    assert not sub_dir.exists()


def test_perform_backup_invalid_path(single_valid_config_directory, caplog):
    config = loads((single_valid_config_directory / "documents.json").read_text())
    config["name_format"] = "\0! #$.."
    new_backup_dir = single_valid_config_directory / "temp_backup"
    new_backup_dir.mkdir()
    assert perform_backup(config, path_override=new_backup_dir) is False
    assert "not valid" in caplog.text
    assert len(list(new_backup_dir.iterdir())) == 0


def test_perform_backup_enough_storage_doesnt_call_find_oldest_backup(
    single_valid_config_directory, mocker
):
    mock_find_oldest_backup = mocker.patch("find_oldest_backup")
    mock_get_device_storage = mocker.patch("get_device_free_space")
    mock_get_device_storage.return_value = 10_000_000_000_000_000_000
    mock_get_directory_size = mocker.patch("get_directory_size")
    mock_get_directory_size.side_effect = [1500, 3000]

    config = loads((single_valid_config_directory / "documents.json").read_text())
    new_backup_dir = single_valid_config_directory / "temp_backup"
    new_backup_dir.mkdir()
    perform_backup(config, path_override=new_backup_dir)

    mock_find_oldest_backup.assert_not_called()


def test_perform_backup_lack_storage_exits(single_valid_config_directory, mocker):
    mock_get_device_storage = mocker.patch("get_device_free_space")
    mock_get_device_storage.return_value = 10_000_000_000_000_000_000
    mock_get_directory_size = mocker.patch("get_directory_size")
    mock_get_directory_size.side_effect = [
        35_000_000_000,
        48_000_000_000,
        47_000_000_000,
        46_000_000_000,
        45_000_000_000,
        44_000_000_000,
        43_000_000_000,
        42_000_000_000,
        41_000_000_000,
        40_000_000_000,
        39_000_000_000,
    ]

    config = loads((single_valid_config_directory / "documents.json").read_text())
    new_backup_dir = single_valid_config_directory / "temp_backup"
    new_backup_dir.mkdir()
    marker = generate_cronvault_marker(Path("test1"), Path("test2"))
    for counter in range(9):
        new_dir = new_backup_dir / f"backup_{counter}"
        new_dir.mkdir()
        (new_dir / CRONVAULT_MARKER_FILENAME).write_text(marker)

    non_cronvault_dir = new_backup_dir / "other_dir"
    non_cronvault_dir.mkdir()

    return_value = perform_backup(config, path_override=new_backup_dir)

    assert return_value is False
    for counter in range(9):
        assert not (new_backup_dir / f"backup_{counter}").exists()
    assert non_cronvault_dir.exists()


def test_perform_backup_deletes_old_backups_and_correctly_copies_data(
    single_valid_config_directory, mocker
):
    mock_get_device_storage = mocker.patch("get_device_free_space")
    mock_copy_into = mocker.patch("Path.copy_into")
    mock_get_device_storage.return_value = 10_000_000_000_000_000_000
    mock_get_directory_size = mocker.patch("get_directory_size")
    mock_get_directory_size.side_effect = [
        35_000_000_000,
        48_000_000_000,
        47_000_000_000,
        46_000_000_000,
        45_000_000_000,
        #  mock deleting a heavy backup, and now there's space
        4_000_000_000,
    ]

    config = loads((single_valid_config_directory / "documents.json").read_text())
    new_backup_dir = single_valid_config_directory / "temp_backup"
    new_backup_dir.mkdir()
    marker = generate_cronvault_marker(Path("test1"), Path("test2"))
    for counter in range(9):
        new_dir = new_backup_dir / f"backup_{counter}"
        new_dir.mkdir()
        (new_dir / CRONVAULT_MARKER_FILENAME).write_text(marker)

    non_cronvault_dir = new_backup_dir / "other_dir"
    non_cronvault_dir.mkdir()

    return_value = perform_backup(config, path_override=new_backup_dir)

    assert return_value is True
    mock_copy_into.assert_called_once()
    backup_count: int = 0
    for counter in range(9):
        if (new_backup_dir / f"backup_{counter}").exists():
            backup_count += 1
    assert backup_count == 5
    assert non_cronvault_dir.exists()


def test_perform_backup_nonexistent_destination(single_valid_config_directory, mocker):
    mock_get_device_storage = mocker.patch("get_device_free_space")
    mock_get_device_storage.return_value = 10_000_000_000_000_000_000
    mock_get_directory_size = mocker.patch("get_directory_size")
    mock_get_directory_size.return_value = 4_000_000_000

    config = loads((single_valid_config_directory / "documents.json").read_text())
    new_backup_dir = single_valid_config_directory / "temp_backup"
    return_value = perform_backup(config, path_override=new_backup_dir)

    assert return_value is False


def test_perform_backup_calls_cleanup_when_OSERROR_raised(
    single_valid_config_directory, mocker
):
    mock_get_device_storage = mocker.patch("get_device_free_space")
    mock_cleanup = mocker.patch("cleanup_failed_backup")
    mock_copy_into = mocker.patch("Path.copy_into")
    mock_copy_into.side_effect = OSError("Copy failed")
    mock_get_device_storage.return_value = 10_000_000_000_000_000_000
    mock_get_directory_size = mocker.patch("get_directory_size")
    mock_get_directory_size.return_value = 4_000_000_000

    config = loads((single_valid_config_directory / "documents.json").read_text())
    new_backup_dir = single_valid_config_directory / "temp_backup"
    new_backup_dir.mkdir()
    return_value = perform_backup(config, path_override=new_backup_dir)
    assert return_value is False
    mock_cleanup.assert_called_once()


def test_generate_default_config(tmp_path: Path):
    generate_default_config(tmp_path)

    config_path = tmp_path / CONFIG_FILE_NAME

    assert config_path.exists()
    file_contents = loads(config_path.read_text())
    assert "backup_frequency_minutes" in file_contents
    assert (
        file_contents["backup_frequency_minutes"]
        == DEFAULT_BACKUP_CHECK_INTERVAL_MINUTES
    )


def test_generate_default_config_creates_parent_dir(tmp_path: Path):
    nested_dir = tmp_path / "subdir" / "sub_subdir"
    generate_default_config(nested_dir)
    assert nested_dir.exists()
    assert (nested_dir / CONFIG_FILE_NAME).exists()


def test_get_backup_frequency_from_config(tmp_path: Path):
    generate_default_config(tmp_path)
    assert (
        get_backup_frequency_from_config(tmp_path)
        == DEFAULT_BACKUP_CHECK_INTERVAL_MINUTES
    )


def test_get_backup_frequency_from_config_custom_config(tmp_path: Path):
    config = {"backup_frequency_minutes": 50}
    (tmp_path / CONFIG_FILE_NAME).write_text(dumps(config))
    assert get_backup_frequency_from_config(tmp_path) == 50


def test_get_backup_frequency_from_config_missing_config_creates_it(tmp_path: Path):
    result = get_backup_frequency_from_config(tmp_path)

    config_file_path = tmp_path / CONFIG_FILE_NAME

    assert config_file_path.exists()
    assert result == DEFAULT_BACKUP_CHECK_INTERVAL_MINUTES


@pytest.mark.parametrize("frequency", [0, -1, "10", None, 1.5])
def test_get_backup_frequency_rejects_invalid_frequency(tmp_path, frequency):
    config_path = tmp_path / CONFIG_FILE_NAME
    config_path.write_text(dumps({"backup_frequency_minutes": frequency}))

    with pytest.raises(ValueError):
        get_backup_frequency_from_config(tmp_path)


def test_ensure_single_cron_job_no_existing_jobs():
    result = ensure_single_cron_job([], 10)
    assert result is False


def test_ensure_single_cron_job_correct():
    job = MagicMock()

    job.is_enabled.return_value = True
    job.is_valid.return_value = True
    job.comment = "Automated CronVault check. Minute frequency: 10"

    result = ensure_single_cron_job([job], 10)

    assert result is True
    job.enable.assert_not_called()
    job.delete.assert_not_called()


def test_ensure_single_cron_job_wrong_frequency():
    job = MagicMock()
    job.is_enabled.return_value = True
    job.is_valid.return_value = True
    job.comment = "Automated CronVault check. Minute frequency: 20"

    result = ensure_single_cron_job([job], 10)

    assert result is True
    job.minute.every.assert_called_once_with(10)
    assert job.comment == "Automated CronVault check. Minute frequency: 10"


def test_ensure_single_cron_job_deletes_duplicate():
    job1 = MagicMock()
    job1.is_enabled.return_value = True
    job1.is_valid.return_value = True
    job1.comment = "Automated CronVault check. Minute frequency: 10"

    job2 = MagicMock()
    job2.is_enabled.return_value = True
    job2.is_valid.return_value = True
    job2.comment = "Automated CronVault check. Minute frequency: 10"

    result = ensure_single_cron_job([job1, job2], 10)

    assert result is True
    job1.delete.assert_not_called()
    job2.delete.assert_called_once()


def test_ensure_single_cron_job_malformed_comment():
    job = MagicMock()
    job.is_enabled.return_value = True
    job.is_valid.return_value = True
    job.comment = "Automated CronVault check. Minute frequency: banana"

    result = ensure_single_cron_job([job], 10)

    assert result is False
    job.delete.assert_called_once()


def test_add_cron_job_creates_job(mocker, tmp_path: Path):
    mock_get_frequency = mocker.patch("get_backup_frequency_from_config")
    mock_ensure_job = mocker.patch("ensure_single_cron_job")
    mock_crontab = mocker.patch("CronTab")
    mock_get_frequency.return_value = 10
    mock_ensure_job.return_value = False
    cron = mock_crontab.return_value
    job = MagicMock()
    cron.new.return_value = job

    add_cron_job(tmp_path)

    mock_get_frequency.assert_called_once_with(tmp_path)
    mock_crontab.assert_called_once_with(user=True)
    cron.find_comment.assert_called_once()
    mock_ensure_job.assert_called_once_with([], 10)
    cron.new.assert_called_once()
    job.minute.every.assert_called_once_with(10)
    cron.write.assert_called_once()


def test_add_cron_job_does_not_create_duplicate(mocker, tmp_path: Path):
    mock_get_frequency = mocker.patch("get_backup_frequency_from_config")
    mock_ensure_job = mocker.patch("ensure_single_cron_job")
    mock_crontab = mocker.patch("CronTab")

    mock_get_frequency.return_value = 10
    mock_ensure_job.return_value = True

    cron = mock_crontab.return_value
    cron.find_comment.return_value = [MagicMock()]

    add_cron_job(tmp_path)

    mock_get_frequency.assert_called_once_with(tmp_path)
    mock_ensure_job.assert_called_once_with(
        cron.find_comment.return_value,
        10,
    )

    cron.new.assert_not_called()
    cron.write.assert_called_once()


def test_parse_path_empty_uses_current_directory():
    assert parse_path("") == str(Path.cwd())


def test_fill_missing_create_args_default_values(mocker, tmp_path):
    mock_get_default_backup = mocker.patch("get_default_backup_name")
    mock_get_default_backup.return_value = "expected"

    args = {
        "name": NAME_DEFAULT,
        "naming_format": NAME_DEFAULT,
        "path": Path("."),
    }

    fill_missing_create_args(args, tmp_path)

    mock_get_default_backup.assert_called_once_with(args["path"], tmp_path)
    assert args["naming_format"] == "expected %Y-%m-%d_%H-%M-%S"


def test_fill_missing_create_args_none_values(mocker, tmp_path):
    mock_get_default_backup = mocker.patch("get_default_backup_name")
    mock_get_default_backup.return_value = "expected"

    args = {
        "name": None,
        "naming_format": None,
        "path": Path("."),
    }

    fill_missing_create_args(args, tmp_path)

    mock_get_default_backup.assert_called_once_with(args["path"], tmp_path)
    assert args["naming_format"] == "expected %Y-%m-%d_%H-%M-%S"


def test_interactive_config_creator_all_values_already_present():
    #  parser functions should not be run here, so input doesn't actually need to be valid
    args = {
        "name": "test",
        "max_backup_size": 500,
        "path": "test",
        "naming_format": "test",
        "destination": "test",
        "time_period": 500,
    }

    args_copy = args.copy()

    interactive_config_creator(args_copy)
    assert args == args_copy


def test_interactive_config_creator_no_values_present(mocker, tmp_path):
    mock_input = mocker.patch("input")
    mock_input.side_effect = [tmp_path, tmp_path, "5M", "", "test", "test"]

    args = {}

    interactive_config_creator(args)
    assert mock_input.call_count == 6
    assert args == {
        "name": "test",
        "max_backup_size": FIFTY_GB,
        "path": str(tmp_path),
        "naming_format": "test",
        "destination": str(tmp_path),
        "time_period": 300,
    }


def test_create_backup_from_args_all_params_given(tmp_path: Path, mocker):
    mock_interactive_config_creator = mocker.patch("interactive_config_creator")
    args = {
        "name": "test",
        "max_backup_size": FIFTY_GB,
        "path": str(tmp_path),
        "naming_format": "test",
        "destination": str(tmp_path),
        "time_period": 300,
    }

    create_backup_from_args(args, tmp_path)

    args["name_format"] = args.pop("naming_format")
    args["last_known_backup"] = None
    args["status"] = "active"
    args["total_backup_count"] = 0

    mock_interactive_config_creator.assert_not_called()
    config_location = tmp_path / f"{args['name']}.json"
    assert config_location.exists()
    config_dict = loads(config_location.read_text())
    assert config_dict == args
    assert config_dict["name_format"] == "test"


def test_create_backup_from_args_all_params_given_duplicate_name(
    tmp_path: Path, mocker
):
    mock_interactive_config_creator = mocker.patch("interactive_config_creator")
    mock_input = mocker.patch("input")
    mock_input.return_value = "new_name"

    args = {
        "name": "test",
        "max_backup_size": FIFTY_GB,
        "path": str(tmp_path),
        "naming_format": None,
        "destination": str(tmp_path),
        "time_period": 300,
    }

    (tmp_path / f"{args['name']}.json").touch()

    create_backup_from_args(args, tmp_path)

    args["name"] = "new_name"
    args["name_format"] = args.pop("naming_format")
    args["last_known_backup"] = None
    args["status"] = "active"
    args["total_backup_count"] = 0

    mock_interactive_config_creator.assert_not_called()
    config_location = tmp_path / f"{args['name']}.json"
    assert config_location.exists()
    config_dict = loads(config_location.read_text())
    assert config_dict == args
    assert config_dict["name_format"] == f"{args['name']} %Y-%m-%d_%H-%M-%S"


def test_create_backup_from_args_all_required_params_given_except_name(
    tmp_path: Path, mocker
):
    sub_path = tmp_path / "test"
    sub_path.mkdir()
    mock_interactive_config_creator = mocker.patch("interactive_config_creator")
    mock_input = mocker.patch("input")

    args = {
        "name": None,  #  missing CLI args are automatically set to None
        "max_backup_size": FIFTY_GB,
        "path": str(sub_path),
        "naming_format": None,
        "destination": str(sub_path),
        "time_period": 300,
    }

    (tmp_path / "test.json").touch()

    create_backup_from_args(args, tmp_path)

    args["name"] = "test_1"
    args["name_format"] = args.pop("naming_format")
    args["last_known_backup"] = None
    args["status"] = "active"
    args["total_backup_count"] = 0

    mock_interactive_config_creator.assert_not_called()
    mock_input.assert_not_called()
    config_location = tmp_path / "test_1.json"
    assert config_location.exists()
    config_file_dict = loads(config_location.read_text())
    assert config_file_dict == args
    assert config_file_dict["name_format"] == f"{args['name']} %Y-%m-%d_%H-%M-%S"


def test_create_backup_from_args_no_params(tmp_path: Path, mocker):
    (tmp_path / "exists.json").touch()
    (tmp_path / "exists_too.json").touch()
    mock_input = mocker.patch("input")
    mock_input.side_effect = [
        str(tmp_path),
        str(tmp_path),
        "1500 seconds",
        "",
        "exists",
        "exists",
        "exists_too",
        "expected",
    ]

    args = {
        "name": None,  #  missing CLI args are automatically set to None
        "max_backup_size": FIFTY_GB,  # default value
        "path": None,
        "naming_format": None,
        "destination": None,
        "time_period": None,
    }

    create_backup_from_args(args, tmp_path)

    args["name"] = "expected"
    args.pop("naming_format")
    args["name_format"] = "expected %Y-%m-%d_%H-%M-%S"
    args["last_known_backup"] = None
    args["status"] = "active"
    args["total_backup_count"] = 0
    args = {
        "name": "expected",
        "name_format": "expected %Y-%m-%d_%H-%M-%S",
        "last_known_backup": None,
        "status": "active",
        "total_backup_count": 0,
        "max_backup_size": FIFTY_GB,
        "path": str(tmp_path),
        "destination": str(tmp_path),
        "time_period": 1500,
    }

    assert mock_input.call_count == 8
    config_location = tmp_path / "expected.json"
    assert config_location.exists()
    config_file_dict = loads(config_location.read_text())
    assert config_file_dict == args
    assert config_file_dict["name_format"] == f"{args['name']} %Y-%m-%d_%H-%M-%S"
