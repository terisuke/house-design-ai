#!/bin/bash
set -e

echo "Testing FreeCAD Docker build..."
cd "$(dirname "$0")/../freecad_api"

echo "Building Docker image locally..."
docker build -t freecad-test:latest -f Dockerfile.freecad .

echo "Docker build successful!"
echo "You can now push to Artifact Registry with:"
echo "docker tag freecad-test:latest asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:latest"
echo "docker push asia-northeast1-docker.pkg.dev/yolov8environment/freecad-api/freecad-api:latest"
