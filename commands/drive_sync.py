from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime
from typing import Optional, List
import shutil

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

try:
    # Optional imports for ADC/google-api fallback
    import google.auth
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
except Exception:
    google = None

from .config import AppConfig

logger = logging.getLogger(__name__)


def _authenticate_drive() -> GoogleDrive:
    gauth = GoogleAuth()
    # Interactive flow: open local webserver and prompt user to authenticate in browser
    gauth.LocalWebserverAuth()
    return GoogleDrive(gauth)


def _get_local_db_path(config: AppConfig, local_db_override: Optional[str]) -> str:
    local_db = local_db_override or config.local_db_path
    if not local_db:
        raise ValueError("local-db path must be provided via --local-db or config.local_db_path")
    if not os.path.exists(local_db):
        raise FileNotFoundError(f"local-db binary not found at: {local_db}")
    return local_db


def _get_or_create_gdrive_folder(drive: GoogleDrive, folder_name: str) -> str:
    file_list = drive.ListFile(
        {
            "q": f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        }
    ).GetList()
    if file_list:
        return file_list[0]["id"]
    folder = drive.CreateFile({"title": folder_name, "mimeType": "application/vnd.google-apps.folder"})
    folder.Upload()
    logger.info(f"Created /{folder_name} folder in Google Drive")
    return folder["id"]


def _get_adc_drive_service():
    """Return a googleapiclient Drive service when ADC is available and has Drive scope, otherwise None.

    We avoid using ADC unless the obtained credentials explicitly include the Drive scope. This
    prevents accidentally selecting ADC in test environments or runtime environments where the
    default credentials don't have Drive permissions (which would cause 403 errors later).
    """
    try:
        if google is None:
            return None
        DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
        # Try to get ADC without forcing scopes first; some environments may provide scoped creds
        creds, _ = google.auth.default()

        scopes = getattr(creds, "scopes", None)
        # If scopes are not present or don't include the Drive scope, try requesting the Drive scope
        if not scopes or DRIVE_SCOPE not in scopes:
            try:
                creds, _ = google.auth.default(scopes=[DRIVE_SCOPE])
                scopes = getattr(creds, "scopes", None)
            except Exception:
                return None

        if not scopes or DRIVE_SCOPE not in scopes:
            return None

        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return service
    except Exception:
        return None


def list_backups(config: AppConfig) -> List[str]:
    drive = _authenticate_drive()
    folder_id = _get_or_create_gdrive_folder(drive, config.gdrive_directory)
    files = drive.ListFile({"q": f"'{folder_id}' in parents and trashed=false"}).GetList()
    return [f["title"] for f in files]


def _run_local_db_command(local_db_script: str, args: list[str]) -> str:
    # Run helper script (if provided) and return stdout. The script is optional; callers may ignore the output.
    if not os.path.exists(local_db_script):
        raise FileNotFoundError(f"local-db script not found at: {local_db_script}")
    if not os.access(local_db_script, os.X_OK):
        raise PermissionError(f"local-db script is not executable: {local_db_script}")

    cmd = [local_db_script] + args
    logger.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {result.stderr}")
    if result.stdout:
        logger.info(result.stdout)
    return result.stdout


def push_to_drive(
    config: AppConfig,
    version: Optional[str],
    overwrite: bool,
    local_db_script: Optional[str],
    dry_run: bool = False,
) -> None:
    # local_db_script: optional helper script that produces stashes; local_db_path points to the data binary
    data_path = config.local_db_path
    if local_db_script:
        # If script provided via CLI, use that to produce a stash; capture any output but do not rely on it
        _run_local_db_command(local_db_script, ["stash", version or datetime.now().strftime("%Y-%m-%d")])

    if not data_path or not os.path.exists(data_path):
        raise FileNotFoundError("local_db_path must point to the datastore data binary to upload")

    if not version:
        version = datetime.now().strftime("%Y-%m-%d")

    backup_file = f"local-db-{version}.bin"

    if dry_run:
        logger.info(f"DRY RUN: would upload {data_path} to Google Drive as {backup_file} in /{config.gdrive_directory}")
        return
    # Prefer Application Default Credentials (gcloud auth) when available
    adc_service = _get_adc_drive_service()
    if adc_service:
        # Ensure folder exists or create it
        # Search for folder
        q = f"mimeType='application/vnd.google-apps.folder' and name='{config.gdrive_directory}' and trashed=false"
        res = adc_service.files().list(q=q, fields="files(id,name)").execute()
        files = res.get("files", [])
        if files:
            folder_id = files[0]["id"]
        else:
            file_metadata = {"name": config.gdrive_directory, "mimeType": "application/vnd.google-apps.folder"}
            created = adc_service.files().create(body=file_metadata, fields="id").execute()
            folder_id = created["id"]

        # Check if a backup with the same name exists
        q2 = f"name='{backup_file}' and '{folder_id}' in parents and trashed=false"
        res2 = adc_service.files().list(q=q2, fields="files(id,name)").execute()
        existing_files = res2.get("files", [])
        if existing_files and not overwrite:
            raise FileExistsError(f"File {backup_file} already exists in /{config.gdrive_directory}. Use -o to overwrite.")

        media = MediaFileUpload(data_path, resumable=True)
        if existing_files:
            file_id = existing_files[0]["id"]
            adc_service.files().update(fileId=file_id, media_body=media).execute()
        else:
            file_metadata = {"name": backup_file, "parents": [folder_id]}
            adc_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        logger.info(f"Successfully uploaded {backup_file} to Google Drive /{config.gdrive_directory} (ADC)")
        return

    # Fallback to pydrive2 interactive flow
    drive = _authenticate_drive()
    folder_id = _get_or_create_gdrive_folder(drive, config.gdrive_directory)

    existing = drive.ListFile({"q": f"title='{backup_file}' and '{folder_id}' in parents and trashed=false"}).GetList()
    if existing:
        if overwrite:
            logger.info(f"Overwriting existing file: {backup_file}")
            file_to_upload = existing[0]
        else:
            raise FileExistsError(f"File {backup_file} already exists in /{config.gdrive_directory}. Use -o to overwrite.")
    else:
        file_to_upload = drive.CreateFile({"title": backup_file, "parents": [{"id": folder_id}]})

    file_to_upload.SetContentFile(data_path)
    file_to_upload.Upload()
    logger.info(f"Successfully uploaded {backup_file} to Google Drive /{config.gdrive_directory}")


def pull_from_drive(config: AppConfig, version: Optional[str], local_db_script: Optional[str], overwrite: bool = True) -> None:
    data_path = config.local_db_path
    if not data_path:
        raise ValueError("local_db_path must be configured in order to restore the database file")

    drive = _authenticate_drive()
    folder_id = _get_or_create_gdrive_folder(drive, config.gdrive_directory)

    if version:
        backup_file = f"local-db-{version}.bin"
        files = drive.ListFile({"q": f"title='{backup_file}' and '{folder_id}' in parents and trashed=false"}).GetList()
        if not files:
            raise FileNotFoundError(f"No backup found with version: {version}")
        file_to_download = files[0]
    else:
        files = drive.ListFile({
            "q": f"'{folder_id}' in parents and trashed=false and title contains 'local-db-' and title contains '.bin'",
            "orderBy": "modifiedDate desc",
            "maxResults": 1,
        }).GetList()
        if not files:
            raise FileNotFoundError(f"No backups found in /{config.gdrive_directory} folder")
        file_to_download = files[0]
        backup_file = file_to_download["title"]

    logger.info(f"Downloading {backup_file} from Google Drive")
    # Prefer ADC if available
    adc_service = _get_adc_drive_service()
    tmp_download = f".download_{backup_file}"
    if adc_service:
        # find file id
        q = f"name='{backup_file}' and '{folder_id}' in parents and trashed=false"
        res = adc_service.files().list(q=q, fields="files(id,name)").execute()
        files = res.get("files", [])
        if not files:
            raise FileNotFoundError(f"No backup found with name: {backup_file}")
        file_id = files[0]["id"]
        request = adc_service.files().get_media(fileId=file_id)
        fh = open(tmp_download, "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.close()
    else:
        # Download into a temporary location then move into place
        file_to_download.GetContentFile(tmp_download)

    if os.path.exists(data_path) and not overwrite:
        raise FileExistsError(f"Local DB file exists at {data_path}; use overwrite option to replace")

    # ensure parent dir exists
    parent = os.path.dirname(data_path)
    if parent:
        os.makedirs(parent, exist_ok=True)

    shutil.copy2(tmp_download, data_path)
    os.remove(tmp_download)
    logger.info(f"Restored backup to {data_path}")

    # Optionally run helper restore script if provided
    if local_db_script:
        _run_local_db_command(local_db_script, ["restore", version or "latest"])
