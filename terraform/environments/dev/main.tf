terraform {
  required_version = ">= 1.0.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Cloud Run サービス
module "streamlit_service" {
  source = "../../modules/cloud-run"

  project_id            = var.project_id
  region                = var.region
  service_name          = "streamlit-web"
  image                 = var.streamlit_image
  memory                = "1Gi"
  cpu                   = "1"
  allow_unauthenticated = true
}

# FreeCAD API サービス
module "freecad_api_service" {
  source = "../../modules/cloud-run"

  project_id            = var.project_id
  region                = var.region
  service_name          = "freecad-api"
  image                 = var.freecad_api_image
  memory                = "2Gi"
  cpu                   = "2"
  allow_unauthenticated = false
  environment_variables = {
    BUCKET_NAME = module.storage.bucket_name
  }
}

# Cloud Storage バケット
module "storage" {
  source = "../../modules/cloud-storage"

  project_id  = var.project_id
  bucket_name = "house-design-ai-data"
  location    = var.region
}

# Artifact Registry リポジトリ
module "artifact_registry" {
  source = "../../modules/artifact-registry"

  project_id    = var.project_id
  location      = var.region
  repository_id = "house-design-ai"
}
