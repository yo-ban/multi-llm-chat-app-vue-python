from sqlalchemy.orm import Session
import json
from typing import Optional # Import Optional

# Fix imports to directly import User and UserSettings from models.models
from app.models.models import User, UserSettings
from app import schemas
from app.encryption import encrypt_data, decrypt_data

# --- Temporary User Handling --- 
# In a real app, use proper authentication to get the user ID
TEMP_USER_ID = 1 

def get_or_create_temp_user(db: Session) -> User:
    """Gets the temporary user or creates them if they don't exist."""
    db_user = db.query(User).filter(User.id == TEMP_USER_ID).first()
    if not db_user:
        db_user = User(id=TEMP_USER_ID)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    return db_user
# --- End Temporary User Handling ---

def get_settings(db: Session, user_id: int) -> Optional[UserSettings]:
    """Retrieve user settings from the database."""
    return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

def update_settings(db: Session, user_id: int, settings_data: schemas.SettingsCreate) -> UserSettings:
    """Update or create user settings in the database."""
    db_settings = get_settings(db, user_id)

    # Encrypt API keys
    encrypted_api_keys = encrypt_data(json.dumps(settings_data.api_keys))

    if db_settings:
        # Update existing settings
        # Get all fields from input data except api_keys
        # update_data = settings_data.model_dump(exclude_unset=True, exclude={'api_keys'}) # Pydantic v1
        update_data = settings_data.model_dump(exclude_unset=True, exclude={'api_keys'}, by_alias=False) # Pydantic v2
        
        # Update all fields present in update_data
        for key, value in update_data.items():
            if hasattr(db_settings, key):
                setattr(db_settings, key, value)

        # Set the encrypted API keys separately
        db_settings.api_keys_encrypted = encrypted_api_keys
    else:
        # Create new settings entry
        db_user = get_or_create_temp_user(db) # Ensure user exists
        # Get all fields from input data except api_keys
        # create_data = settings_data.model_dump(exclude={'api_keys'}) # Pydantic v1
        create_data = settings_data.model_dump(exclude={'api_keys'}, by_alias=False) # Pydantic v2
        
        # Create the UserSettings object, including openrouter_models directly
        db_settings = UserSettings(
            user_id=user_id,
            **create_data, 
            api_keys_encrypted=encrypted_api_keys,
        )
        db.add(db_settings)
    
    db.commit()
    db.refresh(db_settings)
    return db_settings

def decrypt_settings(db_settings: UserSettings) -> schemas.SettingsResponse:
    """Converts DB model to response schema, decrypting API keys."""
    # Start with all data from the DB model
    # This automatically includes openrouter_models and other non-encrypted fields
    # response_data = schemas.SettingsResponse.from_orm(db_settings).dict() # Pydantic v1
    response_data = schemas.SettingsResponse.model_validate(db_settings).model_dump(by_alias=True) # Pydantic v2
    
    # Decrypt API keys
    api_keys = {}
    if db_settings.api_keys_encrypted:
        try:
            api_keys = json.loads(decrypt_data(db_settings.api_keys_encrypted))
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error decrypting or parsing API keys: {e}") # Log properly
            # Optionally return an error or empty dict

    # Override the api_keys field in the response data with the decrypted version
    response_data['apiKeys'] = api_keys
    
    # Ensure openrouter_models is a list (it might be None from DB)
    if response_data.get('openrouterModels') is None:
        response_data['openrouterModels'] = []
        
    return schemas.SettingsResponse.model_validate(response_data) 