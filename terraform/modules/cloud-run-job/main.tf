resource "google_cloud_run_v2_job" "job" {
  name     = var.job_name
  location = var.region

  template {
    template {
      containers {
        image = var.image
        
        resources {
          limits = {
            memory = var.memory
            cpu    = var.cpu
          }
        }

        dynamic "env" {
          for_each = var.environment_variables
          content {
            name  = env.key
            value = env.value
          }
        }
      }
      
      timeout = "${var.timeout_seconds}s"
      max_retries = var.max_retries
    }
  }
}
