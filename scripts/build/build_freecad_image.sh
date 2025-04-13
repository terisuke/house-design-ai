set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="asia-northeast1"
REPOSITORY="house-design-ai"
IMAGE_NAME="freecad"
TAG="latest"

IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"

CURRENT_DIR=$(pwd)

cd "$(dirname "$0")/../../freecad_api"

echo "Building FreeCAD image: ${IMAGE_PATH}"
gcloud builds submit --tag "${IMAGE_PATH}" --file=Dockerfile.freecad .

cd "${CURRENT_DIR}"

echo "FreeCAD image built and pushed successfully: ${IMAGE_PATH}"
