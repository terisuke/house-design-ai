variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud Region"
  type        = string
}

variable "job_name" {
  description = "Cloud Run job name"
  type        = string
}

variable "image" {
  description = "Container image to deploy"
  type        = string
}

variable "memory" {
  description = "Memory allocation"
  type        = string
  default     = "2Gi"
}

variable "cpu" {
  description = "CPU allocation"
  type        = string
  default     = "2"
}

variable "timeout_seconds" {
  description = "Timeout for job execution in seconds"
  type        = number
  default     = 900  # 15分
}

variable "environment_variables" {
  description = "Environment variables"
  type        = map(string)
  default     = {}
}

variable "max_retries" {
  description = "Maximum number of retries for a failed job"
  type        = number
  default     = 0
}
