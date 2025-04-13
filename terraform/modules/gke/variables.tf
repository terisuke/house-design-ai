variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud Region"
  type        = string
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "freecad-cluster"
}

variable "network" {
  description = "VPC network"
  type        = string
  default     = "default"
}

variable "enable_autopilot" {
  description = "Enable Autopilot mode for GKE cluster"
  type        = bool
  default     = true
}
