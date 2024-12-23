import os
from io import BytesIO
from pathlib import Path

import json_advanced as json
import singleton
from usso.session import UssoSession

from .schemas import UFileItem


class UFiles(UssoSession, metaclass=singleton.Singleton):

    def __init__(
        self,
        *,
        ufiles_base_url: str = os.getenv("UFILES_URL", "https://media.pixiee.io/v1/f"),
        usso_base_url: str | None = os.getenv("USSO_URL"),
        api_key: str | None = os.getenv("UFILES_API_KEY"),
        usso_refresh_url: str | None = os.getenv("USSO_REFRESH_URL"),
        refresh_token: str | None = os.getenv("USSO_REFRESH_TOKEN"),
        client: UssoSession | None = None,
    ):
        UssoSession.__init__(
            self,
            usso_base_url=usso_base_url,
            api_key=api_key,
            usso_refresh_url=usso_refresh_url,
            refresh_token=refresh_token,
            client=client,
        )
        if ufiles_base_url.endswith("/"):
            ufiles_base_url = ufiles_base_url[:-1]
        self.ufiles_base_url = ufiles_base_url
        self.upload_url = f"{self.ufiles_base_url}/upload"

    def upload_file(self, filepath: Path, **kwargs) -> UFileItem:
        if not filepath.exists():
            raise FileNotFoundError(f"File {filepath} not found")

        with open(filepath, "rb") as f:
            file_content = BytesIO(f.read())
            return self.upload_bytes(file_content, **kwargs)

    def upload_bytes(self, file_bytes: BytesIO, **kwargs) -> UFileItem:
        file_bytes.seek(0)
        files = {"file": (kwargs.get("filename", "file"), file_bytes)}

        data = {}
        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, dict) or isinstance(value, list):
                    value = json.dumps(value)
                data[key] = value

        response = self.post(
            self.upload_url, headers=self.headers, files=files, data=data
        )
        response.raise_for_status()
        return UFileItem(**response.json())

    def list_files(
        self, parent_id: str = None, all_pages: bool = True, **kwargs
    ) -> list[UFileItem]:
        def get_page(offset, limit=20):
            params = {"parent_id": parent_id, "offset": offset, "limit": limit}
            response = self.get(self.ufiles_base_url, params=params)
            response.raise_for_status()
            return [UFileItem(**item) for item in response.json().get("items")]

        items = []
        offset = 0
        while True:
            page = get_page(offset)
            items.extend(page)
            if not all_pages or not page:
                break
            offset += len(page)

        return items

    def delete_file(self, uid: str) -> UFileItem:
        response = self.delete(f"{self.ufiles_base_url}/{uid}")
        response.raise_for_status()
        return response.json()
