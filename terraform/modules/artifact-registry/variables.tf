variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "location" {
  description = "Location of the Artifact Registry repository"
  type        = string
}

variable "repository_id" {
  description = "ID of the Artifact Registry repository"
  type        = string
}

variable "description" {
  description = "Description of the Artifact Registry repository"
  type        = string
  default     = "Docker repository for House Design AI"
}

variable "public_access" {
  description = "Whether to allow public read access to the repository"
  type        = bool
  default     = false
} 
