#!/usr/bin/env python3
"""
Script to populate factory default system prompts in the database.
Run this after the migration to initialize the system prompts.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from shared.utils.database_setup import get_db, initialize_database
from shared.utils.config import Settings
from shared.services.system_prompt_service import system_prompt_service


async def populate_system_prompts():
    """Populate factory default system prompts in the database."""
    print("Starting system prompts initialization...")
    db = None
    try:
        # Initialize database first
        settings = Settings()
        initialize_database(settings)
        
        # Get database session
        db = next(get_db())
        
        # Initialize factory defaults with force update to refresh descriptions  
        success = await system_prompt_service.initialize_factory_defaults(db, force_update=True)
        
        if success:
            print("✅ Successfully populated factory default system prompts")
            
            # Print summary
            prompts = await system_prompt_service.get_factory_defaults(db)
            print(f"\nInitialized {len(prompts)} factory default prompts:")
            for prompt in prompts:
                print(f"  - {prompt['prompt_key']}: {prompt['prompt_name']}")
        else:
            print("❌ Failed to populate factory default system prompts")
            return False
            
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        return False
    finally:
        if db:
            db.close()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(populate_system_prompts())
    if not success:
        sys.exit(1)
    
    print("\n🎉 System prompts initialization completed successfully!")
