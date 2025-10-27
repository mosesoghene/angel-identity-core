"""
Custom exception classes for the Face Recognition Microservice.
"""

from fastapi import status

class FaceRecognitionError(Exception):
    """Base class for face recognition errors."""
    def __init__(self, message: str, error_code: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

class FaceNotDetectedError(FaceRecognitionError):
    """Raised when no face is detected in an image."""
    def __init__(self, message: str = "No face detected in the provided image."):
        super().__init__(message, "FACE_NOT_DETECTED", status.HTTP_400_BAD_REQUEST)

class MultipleFacesError(FaceRecognitionError):
    """Raised when multiple faces are detected in an image intended for single-face processing."""
    def __init__(self, message: str = "Multiple faces detected. Please provide an image with a single face."):
        super().__init__(message, "MULTIPLE_FACES_DETECTED", status.HTTP_400_BAD_REQUEST)

class PoorImageQualityError(FaceRecognitionError):
    """Raised when an image has poor quality for face recognition."""
    def __init__(self, message: str = "Image quality is too poor for reliable recognition."):
        super().__init__(message, "POOR_IMAGE_QUALITY", status.HTTP_400_BAD_REQUEST)

class PersonNotFoundError(FaceRecognitionError):
    """Raised when a person_id is not found in the vector store."""
    def __init__(self, person_id: str):
        message = f"Person with ID '{person_id}' not found."
        super().__init__(message, "PERSON_NOT_FOUND", status.HTTP_404_NOT_FOUND)

class NoMatchFoundError(FaceRecognitionError):
    """Raised when no matching face is found during verification."""
    def __init__(self, message: str = "No matching face found in the database."):
        super().__init__(message, "NO_MATCH_FOUND", status.HTTP_404_NOT_FOUND)

class StorageError(FaceRecognitionError):
    """Raised for errors related to the vector store or Redis."""
    def __init__(self, message: str = "A storage error occurred."):
        super().__init__(message, "STORAGE_ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR)

class ModelError(FaceRecognitionError):
    """Raised for errors related to the face recognition model."""
    def __init__(self, message: str = "An error occurred with the face recognition model."):
        super().__init__(message, "MODEL_ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR)


# In app/exceptions.py

class PersonAlreadyExistsError(FaceRecognitionError):
    """Raised when attempting to register a person_id that already exists."""
    def __init__(self, person_id: str):
        message = f"Person with ID '{person_id}' already exists. Use the PUT /faces/{person_id} endpoint to update."
        super().__init__(message, "PERSON_ALREADY_EXISTS", status.HTTP_409_CONFLICT)