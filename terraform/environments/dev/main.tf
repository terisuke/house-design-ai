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
# Streamlitサービスのデプロイ
module "streamlit_service" {
  source = "../../modules/cloud-run"

  project_id            = var.project_id
  region                = var.region
  service_name          = "streamlit-web"
  image                 = var.streamlit_image
  memory                = "1Gi"
  cpu                   = "1"
  allow_unauthenticated = true
  environment_variables = {
    BUCKET_NAME     = module.storage.bucket_name
    FREECAD_API_URL = "https://freecad-api-service-xxxxx-xx.a.run.app" # デプロイ後に実際のURLに置き換える
  }
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
  allow_unauthenticated = true
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

module "gke_cluster" {
  source = "../../modules/gke"

  project_id       = var.project_id
  region           = var.region
  cluster_name     = "freecad-gke-cluster"
  enable_autopilot = true
  network          = "default"
}

module "freecad_job" {
  source = "../../modules/cloud-run-job"

  project_id      = var.project_id
  region          = var.region
  job_name        = "freecad-job"
  image           = var.freecad_api_image
  memory          = "2Gi"
  cpu             = "2"
  timeout_seconds = 900 # 15分
  max_retries     = 0
  environment_variables = {
    BUCKET_NAME = module.storage.bucket_name
  }
}
