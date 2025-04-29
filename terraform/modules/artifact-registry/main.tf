resource "google_artifact_registry_repository" "repository" {
  location      = var.location
  repository_id = var.repository_id
  description   = var.description
  format        = "DOCKER"

  docker_config {
    immutable_tags = true
  }
}

resource "google_artifact_registry_repository_iam_member" "public_read" {
  count      = var.public_access ? 1 : 0
  location   = google_artifact_registry_repository.repository.location
  repository = google_artifact_registry_repository.repository.name
  role       = "roles/artifactregistry.reader"
  member     = "allUsers"
} 
