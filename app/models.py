"""
Pydantic models for API requests and responses.
"""
import base64
import binascii
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.config import settings


def is_base64(s: str) -> bool:
    """Check if a string is a valid Base64 encoding."""
    try:
        # Attempt to decode the string
        base64.b64decode(s, validate=True)
        return True
    except (binascii.Error, TypeError):
        return False


class RegisterRequest(BaseModel):
    """Request model for registering a new person."""
    person_id: str = Field(..., description="Unique identifier for the person.")
    images: List[str] = Field(..., description="List of Base64 encoded images for registration.")

    @field_validator('images')
    def validate_images(cls, v):
        if not v:
            raise ValueError("At least one image is required for registration.")
        if len(v) > settings.MAX_IMAGES_PER_REGISTRATION:
            raise ValueError(f"Cannot register more than {settings.MAX_IMAGES_PER_REGISTRATION} images at once.")
        for i, image_str in enumerate(v):
            if not is_base64(image_str):
                raise ValueError(f"Image at index {i} is not a valid Base64 string.")
        return v


class VerifyRequest(BaseModel):
    """Request model for verifying a face."""
    image: str = Field(..., description="Base64 encoded image to verify.")

    @field_validator('image')
    def validate_image(cls, v):
        if not is_base64(v):
            raise ValueError("Image is not a valid Base64 string.")
        return v


class UpdateRequest(BaseModel):
    """Request model for updating a person's face embeddings."""
    images: List[str] = Field(..., description="List of new Base64 encoded images.")

    @field_validator('images')
    def validate_images(cls, v):
        if not v:
            raise ValueError("At least one image is required for updating.")
        if len(v) > settings.MAX_IMAGES_PER_REGISTRATION:
            raise ValueError(f"Cannot update with more than {settings.MAX_IMAGES_PER_REGISTRATION} images at once.")
        for i, image_str in enumerate(v):
            if not is_base64(image_str):
                raise ValueError(f"Image at index {i} is not a valid Base64 string.")
        return v


class RegisterResponse(BaseModel):
    """Response model for a successful registration."""
    success: bool = True
    embeddings_stored: int = Field(..., description="Number of new embeddings successfully stored.")
    average_quality: float = Field(..., description="Average quality score of the processed images (0-1).")


class VerifyResponse(BaseModel):
    """Response model for a verification request."""
    person_id: Optional[str] = Field(None, description="The matched person's ID, or null if no match found.")
    confidence: float = Field(..., description="The confidence score of the match (0-1).")


class UpdateResponse(BaseModel):
    """Response model for a successful update."""
    success: bool = True
    embeddings_updated: int = Field(..., description="Number of embeddings successfully updated.")


class DeleteResponse(BaseModel):
    """Response model for a successful deletion."""
    success: bool = True


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="A unique error code.")
    message: str = Field(..., description="A human-readable error message.")


class HealthCheckResponse(BaseModel):
    """Response model for the health check endpoint."""
    status: str = "ok"
    model_loaded: bool
    qdrant: str
    redis: str