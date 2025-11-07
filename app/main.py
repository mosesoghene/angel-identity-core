"""
Main FastAPI application file for the Face Recognition Microservice.
- Initializes the FastAPI app.
- Sets up middleware for error handling.
- Defines all API endpoints with dependency injection for security.
- Manages application startup logic (model loading).
"""
import logging, base64
from typing import List

from fastapi import FastAPI, Request, status, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.exceptions import FaceRecognitionError
from app.face_service import FaceService
from app.models import (
    RegisterRequest, RegisterResponse,
    VerifyRequest, VerifyResponse,
    UpdateRequest, UpdateResponse,
    DeleteResponse, ErrorResponse,
    HealthCheckResponse
)
from app.mysql_vector_store import MySQLVectorStore
import app.logging_config

# --- Application Setup ---
logger = logging.getLogger(__name__)

app = FastAPI(
    title="School Angel Face Recognition Microservice",
    description="A stateless microservice for face registration, verification, and management.",
    version="1.0.0",
    docs_url="/docs",  # Enable Swagger UI
    redoc_url='/redoc'
)

# --- Service Initialization ---
# Services are initialized on startup.
try:
    vector_store = MySQLVectorStore()
    face_service = FaceService(vector_store=vector_store)
    logger.info("✓ Services initialized successfully.")
except Exception as e:
    logger.critical(f"✗ CRITICAL: Application startup failed during service initialization: {e}", exc_info=True)
    exit(1)

# --- Security Setup (Dependency Injection) ---
api_key_header_scheme = APIKeyHeader(name="X-API-Key")


def get_api_key(api_key: str = Depends(api_key_header_scheme)):
    """Checks if the provided API key matches a Secret API_KEY string."""

    if api_key and api_key.strip() == settings.API_KEY.strip():
        logger.info("API key authentication successful.")
        return api_key
    else:
        logger.warning("API key authentication failed.")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "UNAUTHORIZED", "message": "Invalid or missing API Key."}
        )

# --- Middleware ---
class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Request received: {request.method} {request.url}")
        try:
            response = await call_next(request)
            logger.info(f"Request to {request.url} completed with status {response.status_code}")
            return response
        except FaceRecognitionError as e:
            logger.error(f"API Error: {e.error_code} - {e.message}", exc_info=False)
            return JSONResponse(status_code=e.status_code, content={"error": e.error_code, "message": e.message})
        except Exception as e:
            logger.critical(f"An unexpected internal server error occurred: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"error": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred."}
            )

app.add_middleware(ErrorHandlingMiddleware)


# --- API Endpoints ---
@app.post("/register", response_model=RegisterResponse, summary="Register a new person", tags=["Face Management"])
async def register(request: RegisterRequest, api_key: str = Depends(get_api_key)):
    if isinstance(api_key, JSONResponse): return api_key # Return the error response if auth failed
    logger.info(f"Registration request received for person_id: {request.person_id}")
    result = face_service.register_face(request.person_id, request.images)
    logger.info(f"Registration successful for person_id: {request.person_id}")
    return RegisterResponse(**result)

@app.post("/verify", response_model=VerifyResponse, summary="Verify a face", tags=["Face Verification"])
async def verify(request: VerifyRequest, api_key: str = Depends(get_api_key)):
    if isinstance(api_key, JSONResponse): return api_key
    logger.info("Verification request received.")
    result = face_service.verify_face(request.image)
    logger.info("Verification process completed.")
    return VerifyResponse(**result)


@app.post("/register-upload", response_model=RegisterResponse, summary="Register a new person via file upload", tags=["Face Management"])
async def register_upload(
    person_id: str = Form(...),
    images: List[UploadFile] = File(...),
    api_key: str = Depends(get_api_key)
):
    """
    Registers a new person by accepting one or more image files.

    - **person_id**: A unique identifier for the person (sent as a form field).
    - **images**: One or more image files to upload.
    """
    if isinstance(api_key, JSONResponse): return api_key
    logger.info(f"Registration upload request received for person_id: {person_id}")

    base64_images = []
    for image_file in images:
        contents = await image_file.read()
        encoded_string = base64.b64encode(contents).decode('utf-8')
        base64_images.append(encoded_string)
        logger.info(f"Image {image_file.filename} encoded to base64.")

    result = face_service.register_face(person_id, base64_images)
    logger.info(f"Registration via upload successful for person_id: {person_id}")
    return RegisterResponse(**result)


@app.post("/verify-upload", response_model=VerifyResponse, summary="Verify a face via file upload", tags=["Face Verification"])
async def verify_upload(
    image: UploadFile = File(...),
    api_key: str = Depends(get_api_key)
):
    """
    Finds the most similar person by accepting a single image file.
    """
    if isinstance(api_key, JSONResponse): return api_key
    logger.info("Verification upload request received.")

    contents = await image.read()
    encoded_string = base64.b64encode(contents).decode('utf-8')
    logger.info(f"Image {image.filename} encoded to base64.")

    # Call the existing service method
    result = face_service.verify_face(encoded_string)
    logger.info("Verification via upload process completed.")
    return VerifyResponse(**result)

@app.put("/faces/{person_id}", response_model=UpdateResponse, summary="Update face embeddings", tags=["Face Management"])
async def update_faces(person_id: str, request: UpdateRequest, api_key: str = Depends(get_api_key)):
    if isinstance(api_key, JSONResponse): return api_key
    logger.info(f"Update request received for person_id: {person_id}")
    result = face_service.update_face(person_id, request.images)
    logger.info(f"Update successful for person_id: {person_id}")
    return UpdateResponse(**result)

@app.delete("/faces/{person_id}", response_model=DeleteResponse, summary="Delete a person", tags=["Face Management"])
async def delete_faces(person_id: str, api_key: str = Depends(get_api_key)):
    if isinstance(api_key, JSONResponse): return api_key
    logger.info(f"Delete request received for person_id: {person_id}")
    face_service.delete_face(person_id)
    logger.info(f"Deletion successful for person_id: {person_id}")
    return DeleteResponse(success=True)

@app.get("/health", response_model=HealthCheckResponse, summary="Perform a health check", tags=["System"])
async def health_check():
    """Checks the status of the service and its dependencies."""
    logger.info("Health check requested.")
    model_loaded = face_service.app is not None
    mysql_ok = vector_store.health_check()

    return HealthCheckResponse(
        model_loaded=model_loaded,
        database="connected" if mysql_ok else "disconnected"
    )