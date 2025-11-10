import os
import tempfile
from unittest.mock import Mock, patch
import pytest

from commands.config import AppConfig
from commands.drive_sync import (
    _get_local_db_path,
    _get_or_create_datastore_folder,
    _run_local_db_command,
    push_to_drive,
    pull_from_drive,
)


def test_get_local_db_path_from_override():
    config = AppConfig(local_db_path="/config/path/local-db")
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        result = _get_local_db_path(config, tmp_path)
        assert result == tmp_path
    finally:
        os.unlink(tmp_path)


def test_get_local_db_path_from_config():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        config = AppConfig(local_db_path=tmp_path)
        result = _get_local_db_path(config, None)
        assert result == tmp_path
    finally:
        os.unlink(tmp_path)


def test_get_local_db_path_missing_raises():
    config = AppConfig()
    with pytest.raises(ValueError, match="local-db path must be provided"):
        _get_local_db_path(config, None)


def test_get_local_db_path_not_found_raises():
    config = AppConfig(local_db_path="/nonexistent/local-db")
    with pytest.raises(FileNotFoundError, match="local-db binary not found"):
        _get_local_db_path(config, None)


def test_get_or_create_datastore_folder_existing():
    mock_drive = Mock()
    mock_file_list = Mock()
    mock_file_list.GetList.return_value = [{"id": "folder-123", "title": "datastore"}]
    mock_drive.ListFile.return_value = mock_file_list

    folder_id = _get_or_create_datastore_folder(mock_drive)
    assert folder_id == "folder-123"
    mock_drive.CreateFile.assert_not_called()


def test_get_or_create_datastore_folder_creates_new():
    mock_drive = Mock()
    mock_file_list = Mock()
    mock_file_list.GetList.return_value = []
    mock_drive.ListFile.return_value = mock_file_list

    mock_folder = Mock()
    mock_folder.__getitem__ = Mock(return_value="new-folder-123")
    mock_drive.CreateFile.return_value = mock_folder

    folder_id = _get_or_create_datastore_folder(mock_drive)
    assert folder_id == "new-folder-123"
    mock_drive.CreateFile.assert_called_once()
    mock_folder.Upload.assert_called_once()


def test_run_local_db_command_success():
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".sh") as tmp:
        tmp.write("#!/bin/bash\necho 'Success'\n")
        tmp_path = tmp.name
    os.chmod(tmp_path, 0o755)
    try:
        _run_local_db_command(tmp_path, ["arg1"])
    finally:
        os.unlink(tmp_path)


def test_run_local_db_command_failure():
    with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".sh") as tmp:
        tmp.write("#!/bin/bash\nexit 1\n")
        tmp_path = tmp.name
    os.chmod(tmp_path, 0o755)
    try:
        with pytest.raises(RuntimeError, match="Command failed"):
            _run_local_db_command(tmp_path, ["arg1"])
    finally:
        os.unlink(tmp_path)


@patch("commands.drive_sync._authenticate_drive")
@patch("commands.drive_sync._run_local_db_command")
@patch("commands.drive_sync.os.path.exists")
def test_push_to_drive_with_version(mock_exists, mock_run_cmd, mock_auth):
    mock_exists.return_value = True
    mock_drive = Mock()
    mock_auth.return_value = mock_drive

    mock_folder_list = Mock()
    mock_folder_list.GetList.return_value = [{"id": "folder-123"}]

    mock_file_list = Mock()
    mock_file_list.GetList.return_value = []

    mock_drive.ListFile.side_effect = [mock_folder_list, mock_file_list]

    mock_file = Mock()
    mock_file.__getitem__ = Mock(return_value="folder-123")
    mock_drive.CreateFile.return_value = mock_file

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        config = AppConfig(local_db_path=tmp_path)
        push_to_drive(config, "2024-01-01", False, None)

        mock_run_cmd.assert_called_once_with(tmp_path, ["stash", "2024-01-01"])
        mock_file.SetContentFile.assert_called_once_with("local-db-2024-01-01.bin")
        mock_file.Upload.assert_called_once()
    finally:
        os.unlink(tmp_path)


@patch("commands.drive_sync._authenticate_drive")
@patch("commands.drive_sync._run_local_db_command")
@patch("commands.drive_sync.os.path.exists")
@patch("commands.drive_sync.datetime")
def test_push_to_drive_without_version(mock_datetime, mock_exists, mock_run_cmd, mock_auth):
    mock_now = Mock()
    mock_now.strftime.return_value = "2024-12-25"
    mock_datetime.now.return_value = mock_now
    mock_exists.return_value = True

    mock_drive = Mock()
    mock_auth.return_value = mock_drive

    mock_folder_list = Mock()
    mock_folder_list.GetList.return_value = [{"id": "folder-123"}]

    mock_file_list = Mock()
    mock_file_list.GetList.return_value = []

    mock_drive.ListFile.side_effect = [mock_folder_list, mock_file_list]

    mock_file = Mock()
    mock_file.__getitem__ = Mock(return_value="folder-123")
    mock_drive.CreateFile.return_value = mock_file

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        config = AppConfig(local_db_path=tmp_path)
        push_to_drive(config, None, False, None)

        mock_run_cmd.assert_called_once_with(tmp_path, ["stash", "2024-12-25"])
    finally:
        os.unlink(tmp_path)


@patch("commands.drive_sync._authenticate_drive")
@patch("commands.drive_sync._run_local_db_command")
@patch("commands.drive_sync.os.path.exists")
def test_push_to_drive_overwrite(mock_exists, mock_run_cmd, mock_auth):
    mock_exists.return_value = True
    mock_drive = Mock()
    mock_auth.return_value = mock_drive

    existing_file = Mock()
    existing_file.__getitem__ = Mock(return_value="existing-file-123")
    mock_file_list = Mock()
    mock_file_list.GetList.return_value = [existing_file]

    mock_folder_list = Mock()
    mock_folder_list.GetList.return_value = [{"id": "folder-123"}]

    mock_drive.ListFile.side_effect = [mock_folder_list, mock_file_list]

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        config = AppConfig(local_db_path=tmp_path)
        push_to_drive(config, "2024-01-01", True, None)

        existing_file.SetContentFile.assert_called_once()
        existing_file.Upload.assert_called_once()
    finally:
        os.unlink(tmp_path)


@patch("commands.drive_sync._authenticate_drive")
@patch("commands.drive_sync._run_local_db_command")
@patch("commands.drive_sync.os.path.exists")
def test_push_to_drive_no_overwrite_raises(mock_exists, mock_run_cmd, mock_auth):
    mock_exists.return_value = True
    mock_drive = Mock()
    mock_auth.return_value = mock_drive

    existing_file = Mock()
    mock_file_list = Mock()
    mock_file_list.GetList.return_value = [existing_file]

    mock_folder_list = Mock()
    mock_folder_list.GetList.return_value = [{"id": "folder-123"}]

    mock_drive.ListFile.side_effect = [mock_folder_list, mock_file_list]

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        config = AppConfig(local_db_path=tmp_path)
        with pytest.raises(FileExistsError, match="already exists"):
            push_to_drive(config, "2024-01-01", False, None)
    finally:
        os.unlink(tmp_path)


@patch("commands.drive_sync._authenticate_drive")
@patch("commands.drive_sync._run_local_db_command")
def test_pull_from_drive_with_version(mock_run_cmd, mock_auth):
    mock_drive = Mock()
    mock_auth.return_value = mock_drive

    mock_file = Mock()
    mock_file.__getitem__ = Mock(return_value="local-db-2024-01-01.bin")
    mock_file_list = Mock()
    mock_file_list.GetList.return_value = [mock_file]

    mock_folder_list = Mock()
    mock_folder_list.GetList.return_value = [{"id": "folder-123"}]

    mock_drive.ListFile.side_effect = [mock_folder_list, mock_file_list]

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        config = AppConfig(local_db_path=tmp_path)
        pull_from_drive(config, "2024-01-01", None)

        mock_file.GetContentFile.assert_called_once_with("local-db-2024-01-01.bin")
        mock_run_cmd.assert_called_once_with(tmp_path, ["restore", "2024-01-01"])
    finally:
        os.unlink(tmp_path)


@patch("commands.drive_sync._authenticate_drive")
@patch("commands.drive_sync._run_local_db_command")
def test_pull_from_drive_without_version(mock_run_cmd, mock_auth):
    mock_drive = Mock()
    mock_auth.return_value = mock_drive

    mock_file = Mock()
    mock_file.__getitem__ = Mock(return_value="local-db-latest.bin")
    mock_file_list = Mock()
    mock_file_list.GetList.return_value = [mock_file]

    mock_folder_list = Mock()
    mock_folder_list.GetList.return_value = [{"id": "folder-123"}]

    mock_drive.ListFile.side_effect = [mock_folder_list, mock_file_list]

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        config = AppConfig(local_db_path=tmp_path)
        pull_from_drive(config, None, None)

        mock_file.GetContentFile.assert_called_once()
        mock_run_cmd.assert_called_once_with(tmp_path, ["restore", "latest"])
    finally:
        os.unlink(tmp_path)


@patch("commands.drive_sync._authenticate_drive")
def test_pull_from_drive_version_not_found(mock_auth):
    mock_drive = Mock()
    mock_auth.return_value = mock_drive

    mock_file_list = Mock()
    mock_file_list.GetList.return_value = []

    mock_folder_list = Mock()
    mock_folder_list.GetList.return_value = [{"id": "folder-123"}]

    mock_drive.ListFile.side_effect = [mock_folder_list, mock_file_list]

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        config = AppConfig(local_db_path=tmp_path)
        with pytest.raises(FileNotFoundError, match="No backup found"):
            pull_from_drive(config, "nonexistent", None)
    finally:
        os.unlink(tmp_path)
