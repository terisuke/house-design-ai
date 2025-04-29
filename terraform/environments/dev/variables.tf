variable "project_id" {
  description = "GCPプロジェクトID"
  type        = string
}

variable "region" {
  description = "GCPリージョン"
  type        = string
}

# Streamlit関連の変数
variable "streamlit_image" {
  description = "Streamlitイメージのフルパス"
  type        = string
}

variable "freecad_api_image" {
  description = "FreeCAD APIイメージのフルパス"
  type        = string
}

variable "streamlit_image_platform" {
  description = "Streamlitイメージのプラットフォーム (例: linux/amd64)"
  type        = string
  default     = "linux/amd64"
}

variable "service_account_secret_id" {
  description = "サービスアカウントのシークレットID"
  type        = string
  default     = "house-design-ai-service-account"
}

variable "service_account_file_path" {
  description = "サービスアカウントJSONファイルのパス"
  type        = string
  default     = "config/service_account.json"
}

variable "logo_file_path" {
  description = "ロゴファイルのパス"
  type        = string
  default     = "public/img/logo.png"
}

variable "cloud_run_service_account" {
  description = "Cloud Runのサービスアカウント"
  type        = string
  default     = "yolo-v8-enviroment@yolov8environment.iam.gserviceaccount.com"
}
