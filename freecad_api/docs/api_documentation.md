# FreeCAD API Documentation

## Overview
The FreeCAD API provides endpoints for generating and manipulating 3D models and drawings using FreeCAD. This API is designed to be used with the House Design AI application.

## Base URL
```
https://freecad-api-513507930971.asia-northeast1.run.app
```

## Default Parameters
The API uses the following default parameters for building models:

- **Wall thickness**: 120mm (0.12m)
- **First floor wall height**: 2900mm (2.9m)
- **Second floor wall height**: 2800mm (2.8m)

## Endpoints

### 1. Health Check
```
GET /health
```
Checks if the API is running.

**Response**:
```json
{
  "status": "ok"
}
```

### 2. Process Grid Data
```
POST /process/grid
```
Processes grid data to generate a FreeCAD model.

**Request Body**:
```json
{
  "rooms": [
    {
      "id": "room1",
      "dimensions": [4.0, 3.0],
      "position": [0.0, 0.0]
    }
  ],
  "walls": [
    {
      "start": [0.0, 0.0],
      "end": [4.0, 0.0],
      "floor": 1
    },
    {
      "start": [0.0, 0.0],
      "end": [0.0, 3.0],
      "floor": 2
    }
  ],
  "wall_thickness": 0.12,
  "include_furniture": false
}
```

**Parameters**:
- `rooms`: List of rooms with dimensions and positions
- `walls`: List of walls with start and end coordinates
  - `floor`: Floor number (1 for first floor, 2 for second floor)
  - First floor walls have a height of 2.9m
  - Second floor walls have a height of 2.8m
- `wall_thickness`: Thickness of walls in meters (default: 0.12m)
- `include_furniture`: Whether to include furniture in the model

**Response**:
```json
{
  "url": "https://storage.googleapis.com/house-design-ai-data/models/12345.fcstd?X-Goog-Algorithm=..."
}
```

### 3. Convert to 3D
```
POST /convert/3d
```
Converts a FreeCAD file to STL format.

**Request**:
- Form data with a file field containing the FreeCAD file

**Response**:
```json
{
  "url": "https://storage.googleapis.com/house-design-ai-data/models/12345.stl?X-Goog-Algorithm=..."
}
```

### 4. Convert STL to glTF
```
POST /convert/stl-to-gltf
```
Converts an STL file to glTF format for web viewing.

**Request**:
- Form data with a file field containing the STL file

**Response**:
```json
{
  "url": "https://storage.googleapis.com/house-design-ai-data/models/12345.gltf?X-Goog-Algorithm=..."
}
```

### 5. Process Drawing
```
POST /process/drawing
```
Generates a 2D drawing from a FreeCAD model.

**Request**:
- Form data with a file field containing the FreeCAD file
- Optional parameters:
  - `view_type`: Type of view (top, front, side)
  - `scale`: Scale of the drawing

**Response**:
```json
{
  "url": "https://storage.googleapis.com/house-design-ai-data/drawings/12345.svg?X-Goog-Algorithm=..."
}
```

### 6. Generate Model
```
POST /generate/model
```
Generates a 3D model based on parameters.

**Request Body**:
```json
{
  "width": 10.0,
  "length": 8.0,
  "height": 2.9,
  "wall_thickness": 0.12,
  "include_roof": true
}
```

**Response**:
```json
{
  "url": "https://storage.googleapis.com/house-design-ai-data/models/12345.fcstd?X-Goog-Algorithm=..."
}
```

## Error Handling
All endpoints return appropriate HTTP status codes:
- 200: Success
- 400: Bad request (invalid parameters)
- 500: Server error

Error responses include a JSON body with error details:
```json
{
  "error": "Error message",
  "trace": "Error trace (only in debug mode)"
}
```

## Python Client Example
```python
import requests
import json

# Base URL
base_url = "https://freecad-api-513507930971.asia-northeast1.run.app"

# Example: Process grid data
grid_data = {
  "rooms": [
    {
      "id": "room1",
      "dimensions": [4.0, 3.0],
      "position": [0.0, 0.0]
    }
  ],
  "walls": [
    {
      "start": [0.0, 0.0],
      "end": [4.0, 0.0],
      "floor": 1
    }
  ],
  "wall_thickness": 0.12,
  "include_furniture": False
}

response = requests.post(f"{base_url}/process/grid", json=grid_data)
print(response.json())
```

## Notes on Cloud Run Deployment
- The API is deployed on Google Cloud Run with 2GB memory allocation
- Maximum request timeout is set to 300 seconds
- Authentication is handled through service accounts
