resource "google_secret_manager_secret" "service_account_secret" {
  secret_id = var.service_account_secret_id
  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "service_account_version" {
  count = var.create_from_file ? 1 : 0

  secret      = google_secret_manager_secret.service_account_secret.id
  secret_data = file(var.service_account_file_path)
}

resource "google_secret_manager_secret_iam_member" "cloud_run_access" {
  secret_id = google_secret_manager_secret.service_account_secret.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.service_account_email}"
}
