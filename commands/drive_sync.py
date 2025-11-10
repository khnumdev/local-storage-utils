from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime
from typing import Optional

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

from .config import AppConfig

logger = logging.getLogger(__name__)


def _authenticate_drive() -> GoogleDrive:
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    return GoogleDrive(gauth)


def _get_local_db_path(config: AppConfig, local_db_override: Optional[str]) -> str:
    local_db = local_db_override or config.local_db_path
    if not local_db:
        raise ValueError("local-db path must be provided via --local-db or config.local_db_path")
    if not os.path.exists(local_db):
        raise FileNotFoundError(f"local-db binary not found at: {local_db}")
    return local_db


def _get_or_create_datastore_folder(drive: GoogleDrive) -> str:
    file_list = drive.ListFile(
        {
            "q": "title='datastore' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        }
    ).GetList()
    if file_list:
        return file_list[0]["id"]
    folder = drive.CreateFile(
        {"title": "datastore", "mimeType": "application/vnd.google-apps.folder"}
    )
    folder.Upload()
    logger.info("Created /datastore folder in Google Drive")
    return folder["id"]


def _run_local_db_command(local_db_path: str, args: list[str]) -> None:
    cmd = [local_db_path] + args
    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {result.stderr}")
    if result.stdout:
        logger.info(result.stdout)


def push_to_drive(
    config: AppConfig, version: Optional[str], overwrite: bool, local_db: Optional[str]
) -> None:
    local_db_path = _get_local_db_path(config, local_db)

    if not version:
        version = datetime.now().strftime("%Y-%m-%d")

    backup_file = f"local-db-{version}.bin"

    _run_local_db_command(local_db_path, ["stash", version])

    if not os.path.exists(backup_file):
        raise FileNotFoundError(f"Stash did not produce expected file: {backup_file}")

    drive = _authenticate_drive()
    folder_id = _get_or_create_datastore_folder(drive)

    existing = drive.ListFile(
        {"q": f"title='{backup_file}' and '{folder_id}' in parents and trashed=false"}
    ).GetList()
    if existing:
        if overwrite:
            logger.info(f"Overwriting existing file: {backup_file}")
            file_to_upload = existing[0]
        else:
            raise FileExistsError(
                f"File {backup_file} already exists in /datastore. Use -o to overwrite."
            )
    else:
        file_to_upload = drive.CreateFile({"title": backup_file, "parents": [{"id": folder_id}]})

    file_to_upload.SetContentFile(backup_file)
    file_to_upload.Upload()
    logger.info(f"Successfully uploaded {backup_file} to Google Drive /datastore")


def pull_from_drive(config: AppConfig, version: Optional[str], local_db: Optional[str]) -> None:
    local_db_path = _get_local_db_path(config, local_db)

    drive = _authenticate_drive()
    folder_id = _get_or_create_datastore_folder(drive)

    if version:
        backup_file = f"local-db-{version}.bin"
        files = drive.ListFile(
            {"q": f"title='{backup_file}' and '{folder_id}' in parents and trashed=false"}
        ).GetList()
        if not files:
            raise FileNotFoundError(f"No backup found with version: {version}")
        file_to_download = files[0]
    else:
        files = drive.ListFile(
            {
                "q": f"'{folder_id}' in parents and trashed=false and title contains 'local-db-' and title contains '.bin'",
                "orderBy": "modifiedDate desc",
                "maxResults": 1,
            }
        ).GetList()
        if not files:
            raise FileNotFoundError("No backups found in /datastore folder")
        file_to_download = files[0]
        backup_file = file_to_download["title"]

    logger.info(f"Downloading {backup_file} from Google Drive")
    file_to_download.GetContentFile(backup_file)

    version_to_restore = backup_file.replace("local-db-", "").replace(".bin", "")
    _run_local_db_command(local_db_path, ["restore", version_to_restore])
    logger.info(f"Successfully restored backup: {version_to_restore}")
