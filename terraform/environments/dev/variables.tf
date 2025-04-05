variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud Region"
  type        = string
  default     = "asia-northeast1"
}

variable "streamlit_image" {
  description = "Streamlit container image"
  type        = string
  default     = "asia-northeast1-docker.pkg.dev/house-design-ai/house-design-ai/streamlit:latest"
}

variable "freecad_api_image" {
  description = "FreeCAD API container image"
  type        = string
  default     = "asia-northeast1-docker.pkg.dev/house-design-ai/house-design-ai/freecad-api:latest"
}
