from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_name: str = Field(default="noaa_dw")
    db_user: str = Field(default="postgres")
    db_password: str = Field(default="postgres")

    # NOAA
    noaa_base_url: str = Field(default="https://storms.ngs.noaa.gov/storms")
    noaa_request_timeout: int = Field(default=30)
    noaa_max_retries: int = Field(default=3)

    # Storage
    staging_dir: Path = Field(default=Path("data/staging"))
    archive_dir: Path = Field(default=Path("data/archive"))

    # Pipeline
    batch_size: int = Field(default=100)
    log_level: str = Field(default="INFO")

    @property
    def db_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
