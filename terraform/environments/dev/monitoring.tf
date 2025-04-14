module "monitoring" {
  source = "../../modules/monitoring"

  project_id   = "yolov8environment"
  alert_email  = "company@cor-jp.com"
  service_name = "freecad-api"
} 
