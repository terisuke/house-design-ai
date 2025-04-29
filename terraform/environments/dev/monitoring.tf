module "monitoring" {
  source = "../../modules/monitoring"

  project_id   = var.project_id
  alert_email  = "company@cor-jp.com"
  service_name = "freecad-api"
}
