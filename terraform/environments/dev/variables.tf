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
