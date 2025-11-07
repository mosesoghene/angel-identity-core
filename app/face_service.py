"""
Core business logic for face recognition operations.

This service class encapsulates the InsightFace model, image processing,
and quality assessment logic.
"""

import base64
import logging
import cv2
import numpy as np
from insightface.app import FaceAnalysis

from app.config import settings
from app.exceptions import (
    FaceNotDetectedError,
    MultipleFacesError,
    PoorImageQualityError,
    ModelError,
    PersonAlreadyExistsError
)
from app.mysql_vector_store import MySQLVectorStore

# Configure logging
logger = logging.getLogger(__name__)

# --- Quality Assessment Constants ---
MIN_FACE_AREA = 150 * 150  # Minimum pixel area for a face to be considered high quality
MAX_POSE_ANGLE = 25.0  # Maximum deviation in yaw/pitch/roll in degrees
BRIGHTNESS_RANGE = (60, 200)  # Acceptable min/max average brightness for the face region


class FaceService:
    """
    Service class for handling all face recognition logic.
    """

    def __init__(self, vector_store: MySQLVectorStore):
        """
        Initializes the FaceService.

        - Loads the InsightFace model.
        - Sets up the connection to the vector store.

        Args:
            vector_store: An instance of the VectorStore class.

        Raises:
            ModelError: If the InsightFace model cannot be loaded.
        """
        self.vector_store = vector_store
        try:
            logger.info("Initializing InsightFace model (buffalo_l)...")
            # Initialize FaceAnalysis with the buffalo_l model
            self.app = FaceAnalysis(
                name='buffalo_l',
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
            )
            # Prepare the model (downloads if not present)
            self.app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("✓ InsightFace model loaded successfully!")
        except Exception as e:
            logger.critical(f"✗ CRITICAL: Failed to load InsightFace model: {e}", exc_info=True)
            raise ModelError(f"Could not load or prepare the face recognition model: {e}")

    def _calculate_quality(self, img: np.ndarray, face) -> float:
        """
        Calculates a quality score (0-1) for a detected face based on size, pose, and brightness.

        Args:
            img: The original image as a NumPy array.
            face: The detected face object from InsightFace.

        Returns:
            A quality score between 0.0 and 1.0.
        """
        scores = []
        logger.debug("Calculating face quality...")

        # 1. Face Size Score
        x1, y1, x2, y2 = face.bbox.astype(int)
        area = (x2 - x1) * (y2 - y1)
        size_score = min(1.0, area / MIN_FACE_AREA)
        scores.append(size_score)
        logger.debug(f"Face area: {area}, Size score: {size_score:.2f}")

        # 2. Pose Angle Score
        pose = face.pose  # (yaw, pitch, roll)
        max_angle = max(abs(p) for p in pose)
        # Score is 1 if angle is 0, decreases to 0 as it approaches MAX_POSE_ANGLE
        pose_score = max(0.0, 1.0 - (max_angle / MAX_POSE_ANGLE))
        scores.append(pose_score)
        logger.debug(f"Max pose angle: {max_angle:.2f}, Pose score: {pose_score:.2f}")

        # 3. Brightness Score
        face_roi = img[y1:y2, x1:x2]
        if face_roi.size > 0:
            gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            avg_brightness = np.mean(gray_face)
            min_b, max_b = BRIGHTNESS_RANGE
            if min_b <= avg_brightness <= max_b:
                brightness_score = 1.0
            else:
                # Penalize images that are too dark or too bright
                diff = min(abs(avg_brightness - min_b), abs(avg_brightness - max_b))
                brightness_score = max(0.0, 1.0 - diff / ((max_b - min_b) / 2))
            scores.append(brightness_score)
            logger.debug(f"Average brightness: {avg_brightness:.2f}, Brightness score: {brightness_score:.2f}")

        # Final score is the average of all individual scores
        final_score = np.mean(scores) if scores else 0.0
        logger.info(f"Final quality score: {final_score:.2f}")

        return final_score

    def extract_embeddings(self, images: list[str], allow_multiple_faces: bool = False) -> list[tuple[list[float], float, bytes]]:
        """
        Decodes, validates, and extracts embeddings from a list of Base64 encoded images.
        Args:
            images: A list of Base64 encoded image strings.
            allow_multiple_faces: If True, allows multiple faces and picks the largest one.
        Returns:
            A list of tuples, where each tuple contains (embedding, quality_score, image_bytes).
        Raises:
            FaceNotDetectedError: If no face is found in an image.
            MultipleFacesError: If more than one face is found and not allowed.
            PoorImageQualityError: If the image quality is below a minimum threshold.
        """
        results = []
        logger.info(f"Starting embedding extraction for {len(images)} image(s).")
        for i, image_b64 in enumerate(images):
            logger.info(f"Image {i + 1} added for processing.")
            logger.debug(f"Processing image {i + 1}...")
            try:
                # Decode Base64 string to an image
                img_bytes = base64.b64decode(image_b64)
                img_np = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(img_np, cv2.IMREAD_COLOR)
                if img is None:
                    raise ValueError("Could not decode image. It might be corrupt or in an unsupported format.")
                logger.debug("Image decoded successfully.")

                # Detect faces
                faces = self.app.get(img)
                if not faces:
                    raise FaceNotDetectedError(f"No face detected in image {i + 1}.")
                logger.debug(f"Detected {len(faces)} face(s).")

                # Handle multiple faces
                if len(faces) > 1:
                    if not allow_multiple_faces:
                        raise MultipleFacesError(f"Multiple faces ({len(faces)}) detected in image {i + 1}.")
                    else:
                        logger.debug(f"Multiple faces ({len(faces)}) detected. Selecting the largest one.")
                        # Sort faces by bounding box area (largest first)
                        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)

                face = faces[0]
                quality_score = self._calculate_quality(img, face)

                if quality_score < 0.4:  # Minimum acceptable quality
                    raise PoorImageQualityError(
                        f"Image {i + 1} has poor quality (score: {quality_score:.2f}). "
                        "Please use a clear, well-lit, frontal face image."
                    )

                embedding = face.embedding.tolist()  # Convert numpy array to list for JSON serialization
                results.append((embedding, quality_score, img_bytes))
                logger.info(f"Image {i + 1} processed successfully with quality score {quality_score:.2f}.")

            except (FaceNotDetectedError, MultipleFacesError, PoorImageQualityError) as e:
                logger.warning(f"Image validation failed for image {i + 1}: {e}")
                raise e  # Re-raise to be caught by the API layer
            except Exception as e:
                logger.error(f"An unexpected error occurred during embedding extraction for image {i + 1}: {e}", exc_info=True)
                # Wrap unexpected errors in a standard exception type
                raise ModelError(f"Failed to process image {i + 1}.")
        logger.info("Embedding extraction completed.")
        return results

        # In app/face_service.py

    def register_face(self, person_id: str, images: list[str]) -> dict:
        """
        Registers a person by extracting embeddings from images and storing them.
        Fails if the person_id already exists.

        Args:
            person_id: The unique ID for the person.
            images: A list of Base64 encoded images.

        Returns:
            A dictionary containing the number of stored embeddings and their average quality.

        Raises:
            PersonAlreadyExistsError: If the person_id is already in the database.
        """
        logger.info(f"Starting registration for person_id: {person_id} with {len(images)} images.")

        if self.vector_store.exists(person_id):
            logger.warning(f"Registration failed: person_id '{person_id}' already exists.")
            raise PersonAlreadyExistsError(person_id)

        embedding_data = self.extract_embeddings(images)

        if not embedding_data:
            logger.error("Registration failed: No valid faces found in any of the provided images.")
            raise FaceNotDetectedError("No valid faces found in any of the provided images.")

        embedding_data.sort(key=lambda x: x[1], reverse=True)
        best_image = embedding_data[0][2]
        embeddings = [item[0] for item in embedding_data]
        avg_quality = np.mean([item[1] for item in embedding_data])

        logger.info(f"Proceeding to save {len(embeddings)} embeddings to the database for person_id: {person_id}.")
        count_stored = self.vector_store.store_embeddings(person_id, embeddings, best_image)

        logger.info(f"Successfully registered {count_stored} embeddings for person_id: {person_id}.")
        return {"embeddings_stored": count_stored, "average_quality": float(avg_quality)}

    def verify_face(self, image: str) -> dict:
        """
        Verifies a face by searching for a match in the vector store.

        Args:
            image: A Base64 encoded image of the face to verify.

        Returns:
            A dictionary with the matched person_id, confidence score, and best_image, or null if no match.
        """
        logger.info("Starting face verification...")
        embedding_data = self.extract_embeddings([image], allow_multiple_faces=True)
        embedding, _, _ = embedding_data[0]
        logger.debug("Embedding extracted for verification.")

        logger.info("Match request: Searching for similar faces in the vector store.")
        search_results = self.vector_store.search(
            embedding=embedding,
            threshold=settings.SIMILARITY_THRESHOLD,
            limit=1
        )

        if not search_results:
            logger.info("Match result: No match found above the similarity threshold.")
            return {"person_id": None, "confidence": 0.0, "best_image": None}

        person_id, confidence, best_image = search_results[0]
        logger.info(f"Match found: person_id '{person_id}' with confidence {confidence:.4f}.")
        return {"person_id": person_id, "confidence": float(confidence), "best_image": base64.b64encode(best_image).decode('utf-8')}

    def update_face(self, person_id: str, images: list[str]) -> dict:
        """
        Updates a person's embeddings by replacing them with new ones.

        Args:
            person_id: The ID of the person to update.
            images: A list of new Base64 encoded images.

        Returns:
            A dictionary containing the number of updated embeddings.
        """
        logger.info(f"Starting update for person_id: {person_id} with {len(images)} images.")
        embedding_data = self.extract_embeddings(images)
        embedding_data.sort(key=lambda x: x[1], reverse=True)
        best_image = embedding_data[0][2]
        embeddings = [item[0] for item in embedding_data]

        logger.info(f"Proceeding to save {len(embeddings)} updated embeddings to the database for person_id: {person_id}.")
        count_updated = self.vector_store.update_embeddings(person_id, embeddings, best_image)

        logger.info(f"Successfully updated {count_updated} embeddings for person_id: {person_id}.")
        return {"embeddings_updated": count_updated}

    def delete_face(self, person_id: str) -> bool:
        """
        Deletes all face embeddings associated with a person.

        Args:
            person_id: The ID of the person to delete.

        Returns:
            True if the deletion was successful.
        """
        logger.info(f"Attempting to delete all embeddings for person_id: {person_id}.")
        success = self.vector_store.delete_embeddings(person_id)
        if success:
            logger.info(f"Successfully deleted embeddings for person_id: {person_id}.")
        else:
            logger.error(f"Deletion failed for person_id: {person_id}.")
        return success