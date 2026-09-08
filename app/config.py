import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    postgres_host: str
    postgres_port: str
    postgres_user: str
    postgres_password: str
    postgres_db: str

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings(
        postgres_host=os.environ.get("POSTGRES_HOST", "localhost"),
        postgres_port=os.environ.get("POSTGRES_PORT", "5432"),
        postgres_user=os.environ.get("POSTGRES_USER", "taskflow"),
        postgres_password=os.environ.get("POSTGRES_PASSWORD", "taskflow_dev_only"),
        postgres_db=os.environ.get("POSTGRES_DB", "taskflow"),
    )
