variable "alert_email" {
  description = "アラート通知を受け取るメールアドレス"
  type        = string
}

variable "project_id" {
  description = "GCPプロジェクトID"
  type        = string
}

variable "service_name" {
  description = "Cloud Runサービス名"
  type        = string
  default     = "freecad-api"
} 
