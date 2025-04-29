variable "service_account_secret_id" {
  description = "Secret Managerに保存するサービスアカウントのシークレットID"
  type        = string
  default     = "house-design-ai-service-account"
}

variable "service_account_file_path" {
  description = "サービスアカウントJSONファイルのパス"
  type        = string
  default     = "config/service_account.json"
}

variable "create_from_file" {
  description = "ファイルからシークレットを作成するかどうか"
  type        = bool
  default     = false
}

variable "service_account_email" {
  description = "Cloud Runサービスアカウントのメールアドレス"
  type        = string
}
