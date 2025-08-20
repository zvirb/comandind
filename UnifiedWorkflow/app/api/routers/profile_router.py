"""
Profile router for handling user profile operations.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select
from shared.utils.database_setup import get_async_session, get_db
from shared.database.models import User, UserProfile
from api.dependencies import get_current_user
from pydantic import BaseModel, EmailStr, field_validator
import re
from shared.utils.error_handler import (
    error_handler, create_error_context, internal_server_error, 
    validation_error, not_found_error
)
from api.middleware.error_middleware import monitor_performance

logger = logging.getLogger(__name__)

router = APIRouter()

# TEMPORARY: Debug endpoint to test profile functionality without auth
@router.get("/profile/debug")
async def debug_profile(
    db: AsyncSession = Depends(get_async_session)
):
    """
    TEMPORARY DEBUG: Test profile functionality without authentication.
    This bypasses auth to check if the core profile logic works.
    """
    try:
        # Test with a hardcoded user ID (assuming user 1 exists)
        test_user_id = 1
        
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == test_user_id)
        )
        user_profile = result.scalar_one_or_none()
        
        # Also get user info
        user_result = await db.execute(
            select(User).where(User.id == test_user_id)
        )
        user = user_result.scalar_one_or_none()
        
        return {
            "debug": True,
            "user_exists": user is not None,
            "user_email": user.email if user else None,
            "profile_exists": user_profile is not None,
            "profile_data": {
                "firstName": user_profile.first_name if user_profile else "",
                "lastName": user_profile.last_name if user_profile else "",
                "email": user.email if user else ""
            } if user_profile or user else "No data",
            "database_connection": "OK"
        }
    except Exception as e:
        return {
            "debug": True,
            "error": str(e),
            "database_connection": "FAILED"
        }

class ProfileData(BaseModel):
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    displayName: Optional[str] = None
    dateOfBirth: Optional[str] = None
    phoneNumber: Optional[str] = None
    alternatePhone: Optional[str] = None
    personalAddress: Optional[dict] = None
    jobTitle: Optional[str] = None
    company: Optional[str] = None
    department: Optional[str] = None
    workPhone: Optional[str] = None
    workEmail: Optional[str] = None
    workAddress: Optional[dict] = None
    preferredContactMethod: Optional[str] = None
    emergencyContact: Optional[dict] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    linkedIn: Optional[str] = None
    twitter: Optional[str] = None
    github: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    
    @field_validator('workEmail', 'emergencyContact', mode='before')
    @classmethod
    def validate_email_fields(cls, v, info):
        """Validate email fields and emergency contact structure."""
        if info.field_name == 'workEmail' and v:
            # Basic email validation
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v):
                raise ValueError('Invalid work email format')
        
        if info.field_name == 'emergencyContact' and v:
            if isinstance(v, dict):
                # Validate emergency contact email if provided
                email = v.get('email')
                if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                    raise ValueError('Invalid emergency contact email format')
        
        return v
    
    @field_validator('phoneNumber', 'alternatePhone', 'workPhone', mode='before')
    @classmethod
    def validate_phone_numbers(cls, v):
        """Validate phone number format."""
        if v:
            # Allow various phone formats: +1234567890, (123) 456-7890, 123-456-7890, etc.
            phone_pattern = r'^[+]?[(]?[\d\s\-\(\)]{10,}$'
            if not re.match(phone_pattern, v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')):
                raise ValueError('Invalid phone number format')
        return v
    
    @field_validator('dateOfBirth', mode='before')
    @classmethod
    def validate_date_of_birth(cls, v):
        """Validate date of birth format."""
        if v:
            # Allow YYYY-MM-DD, MM/DD/YYYY, DD/MM/YYYY formats
            date_patterns = [
                r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
                r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
                r'^\d{2}/\d{2}/\d{4}$'   # DD/MM/YYYY
            ]
            if not any(re.match(pattern, v) for pattern in date_patterns):
                raise ValueError('Invalid date format. Use YYYY-MM-DD, MM/DD/YYYY, or DD/MM/YYYY')
        return v
    
    @field_validator('website', 'linkedIn', 'twitter', 'github', mode='before')
    @classmethod
    def validate_urls(cls, v, info):
        """Validate URL fields."""
        if v:
            # Basic URL validation
            url_pattern = r'^https?://[\w\.-]+\.[a-zA-Z]{2,}[\w\.-]*/?.*$'
            if not re.match(url_pattern, v):
                # Allow partial URLs without protocol for social media
                if info.field_name in ['linkedIn', 'twitter', 'github']:
                    if not v.startswith(('http://', 'https://')):
                        # Just validate it looks like a username or profile path
                        return v
                raise ValueError(f'Invalid {info.field_name} URL format')
        return v

# TEMPORARY: Simplified profile endpoint for testing
@router.get("/profile-test")
async def get_profile_test(
    request: Request,
    db: AsyncSession = Depends(get_async_session)
):
    """
    TEMPORARY: Simplified profile endpoint without authentication for testing.
    """
    try:
        # Mock user for testing
        mock_user_id = 1
        
        # Get user profile from database using async syntax
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == mock_user_id)
        )
        user_profile = result.scalar_one_or_none()
        
        return {
            "test_mode": True,
            "mock_user_id": mock_user_id,
            "profile_exists": user_profile is not None,
            "profile_data": {
                "firstName": user_profile.first_name or "" if user_profile else "",
                "lastName": user_profile.last_name or "" if user_profile else "",
                "displayName": user_profile.display_name or "" if user_profile else "",
                "email": "test@example.com"  # Mock email
            } if user_profile else {
                "firstName": "",
                "lastName": "",
                "displayName": "",
                "email": "test@example.com"  # Mock email
            }
        }
    except Exception as e:
        return {
            "test_mode": True,
            "error": str(e)
        }

@router.get("/auth-test")
async def test_authentication(
    current_user: User = Depends(get_current_user)
):
    """Test authentication without complex dependencies."""
    return {
        "success": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "role": str(current_user.role),
        "message": "JWT Authentication working correctly"
    }

@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """
    Get the current user's profile data (simplified for auth testing).
    """
    # Return minimal profile data without database query to isolate auth issues
    return {
        "firstName": "",
        "lastName": "",
        "displayName": current_user.email.split('@')[0],  # Use part of email as display name
        "email": current_user.email,
        "user_id": current_user.id,
        "auth_test": "success",
        "message": "Authentication working correctly"
    }

@router.put("/profile")
@monitor_performance("update_profile")
async def update_profile(
    profile_data: ProfileData,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update the current user's profile data with comprehensive validation.
    """
    try:
        # Validate profile data before database operations
        try:
            profile_dict = profile_data.dict()
        except Exception as validation_err:
            logger.error(f"Profile validation failed for user {current_user.id}: {validation_err}")
            context = create_error_context(request, user_id=current_user.id)
            raise validation_error(
                message="Invalid profile data",
                details={"validation_error": str(validation_err)},
                context=context
            )
        
        # Start database transaction with proper error handling
        async with db.begin():
            # Get existing profile or create new one
            result = await db.execute(
                select(UserProfile).where(UserProfile.user_id == current_user.id)
            )
            user_profile = result.scalar_one_or_none()
            
            if user_profile:
                # Update existing profile with null-safe assignments
                user_profile.first_name = profile_data.firstName
                user_profile.last_name = profile_data.lastName
                user_profile.display_name = profile_data.displayName
                user_profile.date_of_birth = profile_data.dateOfBirth
                user_profile.phone_number = profile_data.phoneNumber
                user_profile.alternate_phone = profile_data.alternatePhone
                user_profile.personal_address = profile_data.personalAddress
                user_profile.job_title = profile_data.jobTitle
                user_profile.company = profile_data.company
                user_profile.department = profile_data.department
                user_profile.work_phone = profile_data.workPhone
                user_profile.work_email = profile_data.workEmail
                user_profile.work_address = profile_data.workAddress
                user_profile.preferred_contact_method = profile_data.preferredContactMethod
                user_profile.emergency_contact = profile_data.emergencyContact
                user_profile.bio = profile_data.bio
                user_profile.website = profile_data.website
                user_profile.linkedin = profile_data.linkedIn
                user_profile.twitter = profile_data.twitter
                user_profile.github = profile_data.github
                user_profile.timezone = profile_data.timezone
                user_profile.language = profile_data.language
                
                # Ensure updated_at is set correctly
                from datetime import datetime, timezone as dt_timezone
                user_profile.updated_at = datetime.now(dt_timezone.utc)
            else:
                # Create new profile with proper constraint handling
                user_profile = UserProfile(
                    user_id=current_user.id,
                    first_name=profile_data.firstName,
                    last_name=profile_data.lastName,
                    display_name=profile_data.displayName,
                    date_of_birth=profile_data.dateOfBirth,
                    phone_number=profile_data.phoneNumber,
                    alternate_phone=profile_data.alternatePhone,
                    personal_address=profile_data.personalAddress,
                    job_title=profile_data.jobTitle,
                    company=profile_data.company,
                    department=profile_data.department,
                    work_phone=profile_data.workPhone,
                    work_email=profile_data.workEmail,
                    work_address=profile_data.workAddress,
                    preferred_contact_method=profile_data.preferredContactMethod,
                    emergency_contact=profile_data.emergencyContact,
                    bio=profile_data.bio,
                    website=profile_data.website,
                    linkedin=profile_data.linkedIn,
                    twitter=profile_data.twitter,
                    github=profile_data.github,
                    timezone=profile_data.timezone,
                    language=profile_data.language
                )
                db.add(user_profile)
            
            # Flush to catch any constraint violations before commit
            await db.flush()
        
        # Refresh the profile to get updated data
        await db.refresh(user_profile)
        
        logger.info(f"Profile updated successfully for user {current_user.id}")
        return {
            "message": "Profile updated successfully",
            "profile_id": user_profile.id,
            "updated_fields": list(profile_dict.keys())
        }
        
    except HTTPException:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Error updating profile for user {current_user.id}: {e}")
        await db.rollback()
        context = create_error_context(request, user_id=current_user.id)
        
        # Check for specific database constraint errors
        error_msg = str(e).lower()
        if 'unique constraint' in error_msg or 'duplicate key' in error_msg:
            raise validation_error(
                message="Profile data conflicts with existing data",
                details={"user_id": current_user.id, "constraint_error": str(e)},
                context=context
            )
        elif 'foreign key' in error_msg:
            raise validation_error(
                message="Invalid user reference in profile data",
                details={"user_id": current_user.id, "foreign_key_error": str(e)},
                context=context
            )
        else:
            raise internal_server_error(
                message="Failed to update profile",
                details={"user_id": current_user.id, "error": str(e)},
                context=context
            )

@router.get("/profile/chat-template")
async def get_profile_chat_template(
    current_user: User = Depends(get_current_user)
):
    """
    Get a chat template for collecting profile information.
    """
    template = {
        "session_id": f"profile_collection_{current_user.id}",
        "message": """I'd like to help you fill out your personal profile information through a conversational approach. I'll ask you a series of questions to gather your details, and you can provide as much or as little information as you're comfortable sharing. 

Let's start with some basic information:

1. What's your first name and last name?
2. What would you like to be called (display name)?
3. What's your date of birth? (YYYY-MM-DD format)
4. What's your phone number?

Feel free to answer any or all of these questions, and I'll help organize the information into your profile. You can also tell me about your work, address, emergency contacts, or any other details you'd like to include.

What would you like to share first?""",
        "context": "profile_collection",
        "system_prompt": """You are a helpful assistant collecting profile information from users. Your job is to:

1. **Extract structured data** from user responses, even when they provide multiple pieces of information at once
2. **Ask follow-up questions** for missing information
3. **Update the profile_data** in your graph state as you collect information
4. **Be conversational and natural** while being systematic

**Data Extraction Rules:**
- If user says "My name is John Smith", extract: firstName="John", lastName="Smith"
- If user says "I'm John", ask for last name
- If user provides full name in any format, try to parse it intelligently
- Extract dates, phone numbers, addresses, work info, etc. from natural language
- Always update the profile_data in your graph state with extracted information

**Profile Fields to Collect:**
- firstName, lastName, displayName, dateOfBirth, phoneNumber, alternatePhone
- personalAddress: {street, street2, city, state, zipCode, country}
- jobTitle, company, department, workPhone, workEmail
- workAddress: {street, street2, city, state, zipCode, country}
- preferredContactMethod, timezone, language
- emergencyContact: {name, relationship, phone, email}
- bio, website, linkedIn, twitter, github

**Response Format:**
Always respond in this JSON structure:
{
  "message": "Your conversational response to the user",
  "extracted_data": {
    // Any new profile fields you extracted from their response
  },
  "next_questions": [
    // List of specific follow-up questions if needed
  ],
  "completion_status": "partial|complete"
}

Begin the conversation naturally.""",
        "current_graph_state": {
            "mode": "profile_collection",
            "user_id": current_user.id,
            "profile_data": {},
            "questions_asked": [],
            "completed_sections": [],
            "extraction_context": "personal_info"
        }
    }
    
    return template

@router.post("/profile/update-from-chat")
@monitor_performance("update_profile_from_chat")
async def update_profile_from_chat(
    extracted_data: dict,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Update profile data with information extracted from chat conversation.
    This endpoint receives structured data extracted by AI from natural language.
    """
    try:
        # Validate the extracted data structure
        valid_fields = {
            'firstName', 'lastName', 'displayName', 'dateOfBirth', 'phoneNumber', 
            'alternatePhone', 'personalAddress', 'jobTitle', 'company', 'department',
            'workPhone', 'workEmail', 'workAddress', 'preferredContactMethod',
            'emergencyContact', 'bio', 'website', 'linkedIn', 'twitter', 'github',
            'timezone', 'language'
        }
        
        # Filter to only valid fields
        validated_data = {k: v for k, v in extracted_data.items() if k in valid_fields}
        
        logger.info(f"Profile data extracted from chat for user {current_user.id}: {validated_data}")
        
        # Get existing profile or create new one
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user.id)
        )
        user_profile = result.scalar_one_or_none()
        
        if user_profile:
            # Update existing profile with validated data
            for field, value in validated_data.items():
                if field == 'firstName':
                    user_profile.first_name = value
                elif field == 'lastName':
                    user_profile.last_name = value
                elif field == 'displayName':
                    user_profile.display_name = value
                elif field == 'dateOfBirth':
                    user_profile.date_of_birth = value
                elif field == 'phoneNumber':
                    user_profile.phone_number = value
                elif field == 'alternatePhone':
                    user_profile.alternate_phone = value
                elif field == 'personalAddress':
                    user_profile.personal_address = value
                elif field == 'jobTitle':
                    user_profile.job_title = value
                elif field == 'company':
                    user_profile.company = value
                elif field == 'department':
                    user_profile.department = value
                elif field == 'workPhone':
                    user_profile.work_phone = value
                elif field == 'workEmail':
                    user_profile.work_email = value
                elif field == 'workAddress':
                    user_profile.work_address = value
                elif field == 'preferredContactMethod':
                    user_profile.preferred_contact_method = value
                elif field == 'emergencyContact':
                    user_profile.emergency_contact = value
                elif field == 'bio':
                    user_profile.bio = value
                elif field == 'website':
                    user_profile.website = value
                elif field == 'linkedIn':
                    user_profile.linkedin = value
                elif field == 'twitter':
                    user_profile.twitter = value
                elif field == 'github':
                    user_profile.github = value
                elif field == 'timezone':
                    user_profile.timezone = value
                elif field == 'language':
                    user_profile.language = value
        else:
            # Create new profile with validated data
            user_profile = UserProfile(
                user_id=current_user.id,
                first_name=validated_data.get('firstName'),
                last_name=validated_data.get('lastName'),
                display_name=validated_data.get('displayName'),
                date_of_birth=validated_data.get('dateOfBirth'),
                phone_number=validated_data.get('phoneNumber'),
                alternate_phone=validated_data.get('alternatePhone'),
                personal_address=validated_data.get('personalAddress'),
                job_title=validated_data.get('jobTitle'),
                company=validated_data.get('company'),
                department=validated_data.get('department'),
                work_phone=validated_data.get('workPhone'),
                work_email=validated_data.get('workEmail'),
                work_address=validated_data.get('workAddress'),
                preferred_contact_method=validated_data.get('preferredContactMethod'),
                emergency_contact=validated_data.get('emergencyContact'),
                bio=validated_data.get('bio'),
                website=validated_data.get('website'),
                linkedin=validated_data.get('linkedIn'),
                twitter=validated_data.get('twitter'),
                github=validated_data.get('github'),
                timezone=validated_data.get('timezone'),
                language=validated_data.get('language')
            )
            db.add(user_profile)
        
        await db.commit()
        logger.info(f"Profile updated successfully from chat for user {current_user.id}")
        
        return {
            "message": "Profile data updated successfully from chat",
            "updated_fields": list(validated_data.keys()),
            "data": validated_data
        }
        
    except Exception as e:
        logger.error(f"Error updating profile from chat for user {current_user.id}: {e}")
        await db.rollback()
        context = create_error_context(request, user_id=current_user.id)
        raise internal_server_error(
            message="Failed to update profile from chat data",
            details={"user_id": current_user.id, "error": str(e)},
            context=context
        )