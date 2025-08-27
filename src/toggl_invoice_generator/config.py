# from loguru import logger
from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)
from typing import Optional
import os

class Project(BaseModel):
    # project_id: Optional[int] = None
    project_id: int
    name: Optional[str] = "<unknown>"
    hourly_rate: float

    # @model_validator(mode="after")
    # def verify_identifier(self) -> "Project":
    #     if (self.project_id and self.name):
    #         logger.warning("Both project_id and name are set for project %s. Using project_id and setting name to None.", self.name)
    #         self.name = None
        
    #     if not self.project_id and not self.name:
    #         raise ValueError("Either project_id or name must be set for project")
        
    #     return self


class Settings(BaseSettings):
    toggl_api_key: str
    projects: list[Project]
    # Invoice configuration
    billed_to: str
    pay_to: str
    payment_terms: str = "Payment details on file"
    workspace_id: int

    @staticmethod
    def _get_config_path() -> str:
        """Get config file path, prompting user if default doesn't exist."""
        default_path = "./config.toml"
        
        # Check if default config exists
        if os.path.exists(default_path):
            return default_path
        
        # Prompt user for config file path
        config_path = default_path
        while not os.path.exists(config_path):
            config_path = input(f"Config file not found at {config_path}. Enter the path to your config.toml file (it should follow the format of example.config.toml): ").strip()
        return config_path
    model_config = SettingsConfigDict(toml_file=_get_config_path())

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls),)