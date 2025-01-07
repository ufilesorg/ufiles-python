import os
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import json_advanced as json
import singleton
from usso.session import AsyncUssoSession

from .schemas import UFileItem


class AsyncUFiles(AsyncUssoSession):

    def __init__(
        self,
        *,
        ufiles_base_url: str = os.getenv("UFILES_URL", "https://media.pixy.ir/v1/f"),
        usso_base_url: str | None = os.getenv("USSO_URL"),
        api_key: str | None = os.getenv("UFILES_API_KEY"),
        usso_refresh_url: str | None = os.getenv("USSO_REFRESH_URL"),
        refresh_token: str | None = os.getenv("USSO_REFRESH_TOKEN"),
        client: AsyncUssoSession | None = None,
    ):
        if client and hasattr(client, "ufiles_base_url"):
            ufiles_base_url = client.ufiles_base_url
        if usso_base_url is None:
            # calculate sso_url using ufiles_url
            # for example: media.pixiee.io/v1/f -> sso.pixiee.io
            # for example: media.ufaas.io/v1/f -> sso.ufaas.io
            # for example: media.pixy.ir/api/v1/f -> sso.pixy.ir
            # for example: storage.pixy.ir/api/v1/f -> sso.pixy.ir
            parsed_url = urlparse(ufiles_base_url)
            netloc = parsed_url.netloc
            netloc_parts = netloc.split(".")
            if len(netloc_parts) > 2:
                netloc_parts[0] = "sso"
            else:
                netloc_parts = ["sso", netloc]
            netloc = ".".join(netloc_parts)
            usso_base_url = f"https://{netloc}"

        super().__init__(
            usso_base_url=usso_base_url,
            api_key=api_key,
            usso_refresh_url=usso_refresh_url,
            refresh_token=refresh_token,
            client=client,
        )

        ufiles_base_url = ufiles_base_url.rstrip("/")
        ufiles_base_url = ufiles_base_url.rstrip("/v1/f")
        self.ufiles_base_url = ufiles_base_url
        self.base_url = f"{self.ufiles_base_url}/v1/f"
        self.upload_file_url = f"{self.base_url}/upload"

    async def upload_file(self, filepath: Path, **kwargs) -> UFileItem:
        if isinstance(filepath, str):
            filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File {filepath} not found")

        with open(filepath, "rb") as f:
            file_content = BytesIO(f.read())
            return await self.upload_bytes(file_content, **kwargs)

    async def upload_url(self, url: str, **kwargs) -> UFileItem:
        if not url.startswith("http"):
            raise ValueError("URL must start with http or https")

        data = {"url": url} | {k: v for k, v in kwargs.items() if v is not None}

        response = await self.post(
            f"{self.ufiles_base_url}/v1/f/url", json=data
        )
        response.raise_for_status()
        return UFileItem(**response.json())

    async def upload_bytes(self, file_bytes: BytesIO, **kwargs) -> UFileItem:
        file_bytes.seek(0)
        files = {"file": (kwargs.get("filename", "file"), file_bytes)}

        data = {}
        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, dict) or isinstance(value, list):
                    value = json.dumps(value)
                data[key] = value

        response = await self.post(
            self.upload_file_url, headers=self.headers, files=files, data=data
        )
        response.raise_for_status()
        return UFileItem(**response.json())

    async def list_files(
        self, parent_id: str = None, all_pages: bool = True, **kwargs
    ) -> list[UFileItem]:
        async def get_page(offset, limit=20):
            params = {"parent_id": parent_id, "offset": offset, "limit": limit}
            response = await self.get(self.ufiles_base_url, params=params)
            response.raise_for_status()
            return [UFileItem(**item) for item in response.json().get("items")]

        items = []
        offset = 0
        while True:
            page = await get_page(offset)
            items.extend(page)
            if not all_pages or not page:
                break
            offset += len(page)

        return items

    async def delete_file(self, uid: str) -> UFileItem:
        response = await self.delete(f"{self.ufiles_base_url}/{uid}")
        response.raise_for_status()
        return response.json()

    async def change_file(
        self, uid: str, filepath: Path, *, overwrite: bool = False, **kwargs
    ) -> UFileItem:
        if isinstance(filepath, str):
            filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File {filepath} not found")

        with open(filepath, "rb") as f:
            file_content = BytesIO(f.read())
            return await self.change_bytes(uid, file_content, overwrite=overwrite, **kwargs)

    async def change_bytes(
        self, uid: str, file_bytes: BytesIO, *, overwrite: bool = False, **kwargs
    ) -> UFileItem:
        file_bytes.seek(0)
        files = {"file": (kwargs.get("filename", "file"), file_bytes)}

        data = {}
        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, dict) or isinstance(value, list):
                    value = json.dumps(value)
                data[key] = value

        response = await self.put(
            f"{self.base_url}/{uid}",
            files=files,
            data=data,
            params={"overwrite": overwrite},
        )
        response.raise_for_status()
        return response.json()
