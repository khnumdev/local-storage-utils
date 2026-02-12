# Interactive Google Drive (pydrive2) setup and usage

This document explains how to run the interactive OAuth flow (pydrive2 LocalWebserverAuth) so you can upload and download your local DB binary to *your* Google Drive using the project's CLI.

Summary
- The CLI uses pydrive2 for the interactive browser OAuth flow. When you run `cli.py db push` without ADC, pydrive2 will open a browser so you can sign in with your Google account and grant Drive permissions. The files uploaded will belong to the account you authorize.

Steps

1) Create an OAuth 2.0 client ID in Google Cloud Console (recommended)

  - Open https://console.cloud.google.com/apis/credentials
  - Click "Create credentials" → "OAuth client ID".
  - Application type: "Desktop app" (or "Other") is fine for local use.
  - Name it (e.g. `local-storage-utils CLI`) and create.
  - Download the JSON file and save it as `client_secrets.json` in the project root (the same directory where `cli.py` lives).

2) Install and activate the Python environment

  ```bash
  python -m venv .venv     # if you don't already have the project venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```

3) Run the interactive push

  - Dry-run first to confirm the path and filename (no changes to Drive):

    ```bash
    .venv/bin/python cli.py db push --dry-run
    ```

  - When ready to upload, run:

    ```bash
    .venv/bin/python cli.py db push
    ```

  - pydrive2 will open a browser window to let you authorize. If the browser doesn't open automatically, the command will print a URL you can paste into any browser. Complete the consent flow and return to the terminal.

4) Verify the upload

  - List backups in the configured Drive folder:

    ```bash
    .venv/bin/python cli.py db list
    ```

  - Alternatively, visit https://drive.google.com and inspect the folder named in your `config.yaml` (`gdrive_directory`, default is `datastore`).

Notes and troubleshooting

- pydrive2 will save the OAuth token locally after you complete the flow so subsequent runs should not require re-authenticating unless the token expires or is revoked. Watch the CLI output to see which file was created.
- If you get errors about missing `client_secrets.json`, ensure the file you downloaded is named exactly `client_secrets.json` and is in the same working directory where you run the CLI.
- If you prefer not to create a client ID, you can still use ADC (gcloud) or a service account — see other options in the project README.
- If you want the program to request a narrower permission (`drive.file`) instead of full Drive access, say so and I can update the code; you must then re-run the interactive flow or adjust ADC accordingly.

Security
- Keep `client_secrets.json` and any token files out of source control (add them to `.gitignore`).
- For automated usage (CI), prefer a service account key and `GOOGLE_APPLICATION_CREDENTIALS` environment variable instead of interactive OAuth.

If you want me to start the interactive push now, say: "run interactive now" and I'll invoke the CLI (it will open the browser / print the auth URL). If you'd rather perform the browser auth yourself first, follow the steps above and then tell me when to proceed.
