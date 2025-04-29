variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "bucket_name" {
  description = "Name of the storage bucket"
  type        = string
}

variable "location" {
  description = "Location of the storage bucket"
  type        = string
}

variable "force_destroy" {
  description = "Whether to force destroy the bucket even if it contains objects"
  type        = bool
  default     = false
}

variable "versioning_enabled" {
  description = "Whether to enable versioning on the bucket"
  type        = bool
  default     = true
}

variable "lifecycle_age" {
  description = "Age in days after which objects should be deleted"
  type        = number
  default     = 30
}

variable "public_access" {
  description = "Whether to allow public read access to the bucket"
  type        = bool
  default     = false
}

variable "upload_logo" {
  description = "ロゴファイルをアップロードするかどうか"
  type        = bool
  default     = false
}

variable "logo_file_path" {
  description = "アップロードするロゴファイルのパス"
  type        = string
  default     = "public/img/logo.png"
}  
