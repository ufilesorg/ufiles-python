import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

try:
    from fastapi_mongo_base.schemas import CoreEntitySchema
except ImportError:

    class CoreEntitySchema(BaseModel):
        created_at: datetime = Field(
            default_factory=datetime.now, json_schema_extra={"index": True}
        )
        updated_at: datetime = Field(default_factory=datetime.now)
        is_deleted: bool = False
        meta_data: dict | None = None


class PermissionEnum(int, Enum):
    NONE = 0
    READ = 10
    WRITE = 20
    MANAGE = 30
    DELETE = 40
    OWNER = 100


class PermissionSchema(CoreEntitySchema):
    permission: PermissionEnum = PermissionEnum.NONE

    @property
    def read(self):
        return self.permission >= PermissionEnum.READ

    @property
    def write(self):
        return self.permission >= PermissionEnum.WRITE

    @property
    def manage(self):
        return self.permission >= PermissionEnum.MANAGE

    @property
    def delete(self):
        return self.permission >= PermissionEnum.DELETE

    @property
    def owner(self):
        return self.permission >= PermissionEnum.OWNER


class Permission(PermissionSchema):
    user_id: uuid.UUID


class UFileItem(BaseModel):
    uid: uuid.UUID
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    meta_data: dict | None = None
    user_id: uuid.UUID
    business_name: str

    s3_key: str | None = None

    parent_id: uuid.UUID | None = None
    is_directory: bool = False

    root_url: str | None = None
    url: str | None = None

    filehash: str | None = None
    filename: str

    content_type: str = "image/webp"
    size: int = 4096
    deleted_at: datetime | None = None

    permissions: list[Permission] = []
    public_permission: PermissionSchema = PermissionSchema()
