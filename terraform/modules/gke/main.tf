resource "google_container_cluster" "cluster" {
  name            = var.cluster_name
  location        = var.region
  enable_autopilot = var.enable_autopilot
  network         = var.network

}
