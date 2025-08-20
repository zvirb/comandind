"""
Service for managing system settings.
This centralizes the system settings logic that was previously in admin_router.py.
"""
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from shared.database.models import UserRole, SystemSetting
from shared.utils.database_setup import get_db


class SystemSettings(BaseModel):
    allow_registration: bool = True
    require_approval: bool = False
    default_role: UserRole = UserRole.USER


class SettingsService:
    """
    Service for managing system settings.
    This is backed by a database table for persistence.
    """
    
    def __init__(self):
        self._defaults = SystemSettings()
    
    def _get_db_setting(self, db: Session, key: str, default: Any = None) -> Any:
        """Get a setting from the database."""
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            try:
                # Try to parse as JSON first for complex types
                return json.loads(setting.value)
            except (json.JSONDecodeError, TypeError):
                # If not JSON, return as string and let the caller handle type conversion
                return setting.value
        return default
    
    def _set_db_setting(self, db: Session, key: str, value: Any, description: Optional[str] = None) -> None:
        """Set a setting in the database."""
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        
        # Convert value to string for storage
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
        elif isinstance(value, bool):
            value_str = json.dumps(value)
        else:
            value_str = str(value)
        
        if setting:
            setting.value = value_str
            if description:
                setting.description = description
        else:
            setting = SystemSetting(
                key=key,
                value=value_str,
                description=description
            )
            db.add(setting)
        
        db.commit()
    
    def get_registration_settings(self) -> SystemSettings:
        """Get current registration settings."""
        db = next(get_db())
        try:
            return SystemSettings(
                allow_registration=self._get_db_setting(db, "allow_registration", True),
                require_approval=self._get_db_setting(db, "require_approval", False),
                default_role=UserRole(self._get_db_setting(db, "default_role", UserRole.USER.value))
            )
        finally:
            db.close()
    
    def update_registration_settings(self, settings: SystemSettings) -> SystemSettings:
        """Update registration settings."""
        db = next(get_db())
        try:
            self._set_db_setting(db, "allow_registration", settings.allow_registration, "Whether new user registration is allowed")
            self._set_db_setting(db, "require_approval", settings.require_approval, "Whether new users require admin approval")
            self._set_db_setting(db, "default_role", settings.default_role.value, "Default role for new users")
            return settings
        finally:
            db.close()
    
    def get_setting(self, key: str) -> Any:
        """Get a specific setting value."""
        db = next(get_db())
        try:
            return self._get_db_setting(db, key)
        finally:
            db.close()
    
    def update_setting(self, key: str, value: Any, description: Optional[str] = None) -> None:
        """Update a specific setting."""
        db = next(get_db())
        try:
            self._set_db_setting(db, key, value, description)
        finally:
            db.close()


# Global settings service instance
_settings_service = SettingsService()


def get_settings_service() -> SettingsService:
    """Get the global settings service instance."""
    return _settings_service