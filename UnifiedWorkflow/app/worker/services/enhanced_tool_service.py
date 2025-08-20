"""
Enhanced Tool Service with Schema Validation (LangChain 0.3+ features).
Provides structured tool calling with Pydantic schema validation.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union, get_type_hints
from uuid import uuid4

from langchain_core.tools import BaseTool, StructuredTool
from langchain_core.pydantic_v1 import BaseModel, Field, create_model
from langchain_ollama import ChatOllama
from pydantic import ValidationError

from worker.graph_types import GraphState
from worker.tool_handlers import get_tool_handler
from shared.schemas.enhanced_chat_schemas import ToolExecutionResult, ToolExecutionStatus
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Enhanced tool schemas for validation
class ToolInputSchema(BaseModel):
    """Base schema for tool inputs with validation."""
    user_input: str = Field(..., description="User input for the tool")
    additional_context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    
class CalendarToolInput(ToolInputSchema):
    """Schema for calendar management tool."""
    action: str = Field(..., description="Calendar action: create, view, edit, delete")
    event_title: Optional[str] = Field(None, description="Event title for creation/editing")
    event_date: Optional[str] = Field(None, description="Event date in ISO format")
    event_time: Optional[str] = Field(None, description="Event time")
    duration: Optional[int] = Field(None, description="Duration in minutes")

class DocumentQAToolInput(ToolInputSchema):
    """Schema for document Q&A tool."""
    query: str = Field(..., description="Question about the document")
    document_id: Optional[str] = Field(None, description="Specific document ID")
    search_type: str = Field("semantic", description="Search type: semantic, keyword, hybrid")

class EmailToolInput(ToolInputSchema):
    """Schema for email management tool."""
    action: str = Field(..., description="Email action: compose, search, reply, organize")
    recipient: Optional[str] = Field(None, description="Email recipient")
    subject: Optional[str] = Field(None, description="Email subject")
    body: Optional[str] = Field(None, description="Email body")
    search_query: Optional[str] = Field(None, description="Search query for finding emails")

class WebSearchToolInput(ToolInputSchema):
    """Schema for web search tool."""
    query: str = Field(..., description="Search query")
    max_results: int = Field(5, description="Maximum number of results")
    search_type: str = Field("general", description="Search type: general, news, images")

class FileSystemToolInput(ToolInputSchema):
    """Schema for file system operations."""
    action: str = Field(..., description="File action: read, write, list, search")
    file_path: Optional[str] = Field(None, description="File path")
    content: Optional[str] = Field(None, description="Content for write operations")
    search_pattern: Optional[str] = Field(None, description="Search pattern")

class TaskManagementToolInput(ToolInputSchema):
    """Schema for task management tool."""
    action: str = Field(..., description="Task action: create, list, update, complete")
    task_title: Optional[str] = Field(None, description="Task title")
    task_description: Optional[str] = Field(None, description="Task description")
    task_id: Optional[str] = Field(None, description="Task ID for updates")
    priority: Optional[str] = Field("medium", description="Task priority: low, medium, high")

class HomeAssistantToolInput(ToolInputSchema):
    """Schema for home automation tool."""
    action: str = Field(..., description="Home action: control, status, scene")
    device_name: Optional[str] = Field(None, description="Device name")
    device_type: Optional[str] = Field(None, description="Device type: light, switch, sensor")
    value: Optional[Union[str, int, float]] = Field(None, description="Value to set")

class SocraticGuidanceToolInput(ToolInputSchema):
    """Schema for Socratic guidance tool."""
    reflection_type: str = Field("general", description="Type of reflection: general, career, learning")
    current_situation: Optional[str] = Field(None, description="Current situation description")
    goals: Optional[List[str]] = Field(None, description="User goals")

class ToolValidationResult(BaseModel):
    """Result of tool input validation."""
    is_valid: bool = Field(..., description="Whether input is valid")
    validated_input: Optional[Dict[str, Any]] = Field(None, description="Validated input data")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    schema_used: Optional[str] = Field(None, description="Schema class name used")

class EnhancedToolService:
    """Enhanced tool service with schema validation and structured calling."""
    
    def __init__(self):
        self.ollama_base_url = settings.OLLAMA_API_BASE_URL
        self.tool_schemas = self._initialize_tool_schemas()
        
    def _initialize_tool_schemas(self) -> Dict[str, Type[ToolInputSchema]]:
        """Initialize tool input schemas mapping."""
        return {
            "calendar_management": CalendarToolInput,
            "document_qa": DocumentQAToolInput,
            "email_management": EmailToolInput,
            "web_search": WebSearchToolInput,
            "file_system": FileSystemToolInput,
            "task_management": TaskManagementToolInput,
            "home_assistant": HomeAssistantToolInput,
            "socratic_guidance": SocraticGuidanceToolInput,
            "unstructured_interaction": ToolInputSchema  # Base schema for fallback
        }
    
    async def validate_tool_input(
        self, 
        tool_name: str, 
        raw_input: Dict[str, Any]
    ) -> ToolValidationResult:
        """Validate tool input against its schema."""
        try:
            # Get appropriate schema
            schema_class = self.tool_schemas.get(tool_name, ToolInputSchema)
            
            # Validate input
            validated_input = schema_class(**raw_input)
            
            return ToolValidationResult(
                is_valid=True,
                validated_input=validated_input.dict(),
                schema_used=schema_class.__name__
            )
            
        except ValidationError as e:
            logger.warning(f"Tool input validation failed for {tool_name}: {e}")
            return ToolValidationResult(
                is_valid=False,
                errors=[str(error) for error in e.errors()],
                schema_used=self.tool_schemas.get(tool_name, ToolInputSchema).__name__
            )
        except Exception as e:
            logger.error(f"Unexpected error in tool validation: {e}")
            return ToolValidationResult(
                is_valid=False,
                errors=[f"Unexpected validation error: {str(e)}"]
            )
    
    async def extract_tool_parameters_with_llm(
        self, 
        tool_name: str, 
        user_input: str, 
        model: str = "llama3.2:3b"
    ) -> Dict[str, Any]:
        """Use LLM to extract structured parameters for tool calling."""
        try:
            # Get schema for the tool
            schema_class = self.tool_schemas.get(tool_name, ToolInputSchema)
            
            # Create LLM with structured output
            llm = ChatOllama(
                model=model,
                base_url=self.ollama_base_url,
                temperature=0.1
            )
            
            # Create prompt for parameter extraction
            schema_description = self._get_schema_description(schema_class)
            
            from langchain_core.prompts import ChatPromptTemplate
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", f"""You are a parameter extraction expert. Extract structured parameters for the {tool_name} tool.

Tool Schema:
{schema_description}

Extract the relevant parameters from the user input. If a parameter is not mentioned, use null or appropriate default values.
Return valid JSON that matches the schema."""),
                ("human", "User input: {user_input}")
            ])
            
            # Use structured output if available (LangChain 0.3+ feature)
            try:
                structured_llm = llm.with_structured_output(schema_class)
                chain = prompt | structured_llm
                result = await chain.ainvoke({"user_input": user_input})
                return result.dict()
                
            except AttributeError:
                # Fallback to text parsing
                chain = prompt | llm
                response = await chain.ainvoke({"user_input": user_input})
                
                # Try to parse JSON from response
                try:
                    return json.loads(response.content)
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse LLM response as JSON for {tool_name}")
                    return {"user_input": user_input}
                    
        except Exception as e:
            logger.error(f"Error extracting tool parameters with LLM: {e}")
            return {"user_input": user_input}
    
    def _get_schema_description(self, schema_class: Type[ToolInputSchema]) -> str:
        """Get human-readable description of a schema."""
        try:
            fields = []
            for field_name, field_info in schema_class.__fields__.items():
                field_type = field_info.type_
                description = field_info.field_info.description or "No description"
                required = field_info.required
                
                fields.append(f"- {field_name} ({field_type.__name__}): {description} {'(required)' if required else '(optional)'}")
            
            return f"{schema_class.__name__} fields:\n" + "\n".join(fields)
            
        except Exception as e:
            logger.error(f"Error getting schema description: {e}")
            return "Schema description unavailable"
    
    async def execute_tool_with_validation(
        self, 
        tool_name: str, 
        raw_input: Dict[str, Any], 
        state: GraphState,
        use_llm_extraction: bool = True
    ) -> ToolExecutionResult:
        """Execute tool with input validation and structured error handling."""
        start_time = datetime.now()
        
        try:
            # Step 1: Try direct validation first
            validation_result = await self.validate_tool_input(tool_name, raw_input)
            
            if not validation_result.is_valid and use_llm_extraction:
                # Step 2: Use LLM to extract parameters if direct validation fails
                logger.info(f"Direct validation failed for {tool_name}, using LLM extraction")
                extracted_params = await self.extract_tool_parameters_with_llm(
                    tool_name, 
                    raw_input.get("user_input", str(raw_input)),
                    state.chat_model or "llama3.2:3b"
                )
                
                # Re-validate with extracted parameters
                validation_result = await self.validate_tool_input(tool_name, extracted_params)
            
            if not validation_result.is_valid:
                # Return validation error
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                return ToolExecutionResult(
                    tool_name=tool_name,
                    status=ToolExecutionStatus.ERROR,
                    error=f"Input validation failed: {'; '.join(validation_result.errors)}",
                    execution_time_ms=execution_time,
                    metadata={
                        "validation_errors": validation_result.errors,
                        "schema_used": validation_result.schema_used
                    }
                )
            
            # Step 3: Execute tool with validated input
            logger.info(f"Executing {tool_name} with validated input")
            
            # Update state with validated input
            if validation_result.validated_input:
                # Merge validated input into state
                for key, value in validation_result.validated_input.items():
                    if hasattr(state, key):
                        setattr(state, key, value)
                
                # Store original user input
                state.user_input = validation_result.validated_input.get("user_input", state.user_input)
            
            # Get and execute tool handler
            handler = get_tool_handler(tool_name)
            if not handler:
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                return ToolExecutionResult(
                    tool_name=tool_name,
                    status=ToolExecutionStatus.ERROR,
                    error=f"Tool handler not found: {tool_name}",
                    execution_time_ms=execution_time
                )
            
            # Execute tool
            result = await handler(state)
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            return ToolExecutionResult(
                tool_name=tool_name,
                status=ToolExecutionStatus.SUCCESS,
                result=result,
                execution_time_ms=execution_time,
                metadata={
                    "schema_used": validation_result.schema_used,
                    "input_validated": True,
                    "llm_extraction_used": use_llm_extraction and not validation_result.is_valid
                }
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Error executing tool {tool_name}: {e}")
            
            return ToolExecutionResult(
                tool_name=tool_name,
                status=ToolExecutionStatus.ERROR,
                error=str(e),
                execution_time_ms=execution_time,
                metadata={"validation_attempted": True}
            )
    
    async def get_available_tools_with_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Get all available tools with their input schemas."""
        tools_info = {}
        
        for tool_name, schema_class in self.tool_schemas.items():
            try:
                # Get schema info
                schema_info = {
                    "name": tool_name,
                    "schema_class": schema_class.__name__,
                    "description": schema_class.__doc__ or f"Schema for {tool_name}",
                    "fields": {},
                    "required_fields": [],
                    "optional_fields": []
                }
                
                # Extract field information
                for field_name, field_info in schema_class.__fields__.items():
                    field_data = {
                        "type": field_info.type_.__name__,
                        "description": field_info.field_info.description,
                        "required": field_info.required,
                        "default": field_info.default if hasattr(field_info, 'default') else None
                    }
                    
                    schema_info["fields"][field_name] = field_data
                    
                    if field_info.required:
                        schema_info["required_fields"].append(field_name)
                    else:
                        schema_info["optional_fields"].append(field_name)
                
                tools_info[tool_name] = schema_info
                
            except Exception as e:
                logger.error(f"Error getting schema info for {tool_name}: {e}")
                tools_info[tool_name] = {
                    "name": tool_name,
                    "error": f"Could not load schema: {str(e)}"
                }
        
        return tools_info

# Global instance
enhanced_tool_service = EnhancedToolService()