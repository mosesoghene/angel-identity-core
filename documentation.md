# API Documentation

This document provides detailed documentation for the Face Recognition Microservice API.

## Authentication

All endpoints (except for `/health`) require an API key for authentication. The API key must be included in the `X-API-Key` header of your request.

---

## Endpoints

### Face Registration

The system provides two endpoints for face registration: one for `base64 image string` and another for `multipart/form-data`.

#### 1. Register via Base64 Image String

*   **Endpoint:** `POST /register`
*   **Description:** Registers a new person by sending one or more `base64 image string`.
*   **Request Type:** `POST`
*   **Headers:**
    *   `Content-Type: application/json`
    *   `X-API-Key: <YOUR_API_KEY>`
*   **Request Body:**
    ```json
    {
      "person_id": "UNIQUE_PERSON_ID",
      "images": [
        "BASE64_ENCODED_IMAGE_STRING_1",
        "BASE64_ENCODED_IMAGE_STRING_2"
      ]
    }
    ```
*   **Response:**
    *   **200 OK:**
        ```json
        {
          "success": true,
          "person_id": "UNIQUE_PERSON_ID",
          "faces_detected": 2,
          "faces_registered": 2
        }
        ```
*   **Example Usage (curl):**
    ```bash
    curl -X POST "http://http://192.168.0.82:8800/register" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: <YOUR_API_KEY>" \
    -d '{
      "person_id": "user123",
      "images": ["/9j/4AAQSkZJRgABAQE..."]
    }'
    ```

#### 2. Register via Multipart/Form-Data

*   **Endpoint:** `POST /register-upload`
*   **Description:** Registers a new person by uploading image files using `multipart/form-data`.
*   **Request Type:** `POST`
*   **Headers:**
    *   `X-API-Key: <YOUR_API_KEY>`
*   **Request Body:** `multipart/form-data`
    *   `person_id`: (string) A unique identifier for the person.
    *   `images`: (file) One or more image files.
*   **Response:**
    *   **200 OK:**
        ```json
        {
          "success": true,
          "person_id": "UNIQUE_PERSON_ID",
          "faces_detected": 1,
          "faces_registered": 1
        }
        ```
*   **Example Usage (curl):**
    ```bash
    curl -X POST "http://http://192.168.0.82:8800/register-upload" \
    -H "X-API-Key: <YOUR_API_KEY>" \
    -F "person_id=user123" \
    -F "images=@/path/to/image1.jpg" \
    -F "images=@/path/to/image2.png"
    ```

### Face Management

#### 1. Update Face Embeddings

*   **Endpoint:** `PUT /faces/{person_id}`
*   **Description:** Updates the face embeddings for an existing person.
*   **Request Type:** `PUT`
*   **Headers:**
    *   `Content-Type: application/json`
    *   `X-API-Key: <YOUR_API_KEY>`
*   **Path Parameter:**
    *   `person_id`: The ID of the person to update.
*   **Request Body:**
    ```json
    {
      "images": [
        "NEW_BASE64_ENCODED_IMAGE_STRING_1",
        "NEW_BASE64_ENCODED_IMAGE_STRING_2"
      ]
    }
    ```
*   **Response:**
    *   **200 OK:**
        ```json
        {
          "success": true,
          "person_id": "UNIQUE_PERSON_ID",
          "faces_detected": 2,
          "faces_updated": 2
        }
        ```
*   **Example Usage (curl):**
    ```bash
    curl -X PUT "http://http://192.168.0.82:8800/faces/user123" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: <YOUR_API_KEY>" \
    -d '{
      "images": ["/9j/4AAQSkZJRgABAQE..."]
    }'
    ```

#### 2. Delete a Person

*   **Endpoint:** `DELETE /faces/{person_id}`
*   **Description:** Deletes a person and their associated face embeddings.
*   **Request Type:** `DELETE`
*   **Headers:**
    *   `X-API-Key: <YOUR_API_KEY>`
*   **Path Parameter:**
    *   `person_id`: The ID of the person to delete.
*   **Response:**
    *   **200 OK:**
        ```json
        {
          "success": true
        }
        ```
*   **Example Usage (curl):**
    ```bash
    curl -X DELETE "http://http://192.168.0.82:8800/faces/user123" \
    -H "X-API-Key: <YOUR_API_KEY>"
    ```

---

### Face Verification

The system provides two endpoints for face verification: one for `base64 image string` and another for `multipart/form-data`.

#### 1. Verify via Base64 Image String

*   **Endpoint:** `POST /verify`
*   **Description:** Verifies a face by sending a `base64 image string`.
*   **Request Type:** `POST`
*   **Headers:**
    *   `Content-Type: application/json`
    *   `X-API-Key: <YOUR_API_KEY>`
*   **Request Body:**
    ```json
    {
      "image": "BASE64_ENCODED_IMAGE_STRING"
    }
    ```
*   **Response:**
    *   **200 OK:**
        ```json
        {
          "found": true,
          "person_id": "MATCHING_PERSON_ID",
          "confidence": 0.95
        }
        ```
*   **Example Usage (curl):**
    ```bash
    curl -X POST "http://http://192.168.0.82:8800/verify" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: <YOUR_API_KEY>" \
    -d '{
      "image": "/9j/4AAQSkZJRgABAQE..."]
    }'
    ```

#### 2. Verify via Multipart/Form-Data

*   **Endpoint:** `POST /verify-upload`
*   **Description:** Verifies a face by uploading an image file using `multipart/form-data`.
*   **Request Type:** `POST`
*   **Headers:**
    *   `X-API-Key: <YOUR_API_KEY>`
*   **Request Body:** `multipart/form-data`
    *   `image`: (file) A single image file.
*   **Response:**
    *   **200 OK:**
        ```json
        {
          "found": true,
          "person_id": "MATCHING_PERSON_ID",
          "confidence": 0.95
        }
        ```
*   **Example Usage (curl):**
    ```bash
    curl -X POST "http://http://192.168.0.82:8800/verify-upload" \
    -H "X-API-Key: <YOUR_API_KEY>" \
    -F "image=@/path/to/verify_image.jpg"
    ```

---

### System

#### 1. Health Check

*   **Endpoint:** `GET /health`
*   **Description:** Checks the health of the service and its dependencies.
*   **Request Type:** `GET`
*   **Response:**
    *   **200 OK:**
        ```json
        {
          "model_loaded": true,
          "database": "connected"
        }
        ```
*   **Example Usage (curl):**
    ```bash
    curl -X GET "http://http://192.168.0.82:8800/health"
    ```
