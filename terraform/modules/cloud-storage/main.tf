resource "google_storage_bucket" "bucket" {
  name          = var.bucket_name
  location      = var.location
  force_destroy = var.force_destroy

  uniform_bucket_level_access = true

  versioning {
    enabled = var.versioning_enabled
  }

  lifecycle_rule {
    condition {
      age = var.lifecycle_age
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket_object" "logo" {
  count  = var.upload_logo ? 1 : 0
  name   = "${var.folder_prefix}logo.png"
  bucket = google_storage_bucket.bucket.name
  source = var.logo_file_path
}

resource "google_storage_bucket_iam_member" "public_read" {
  count  = var.public_access ? 1 : 0
  bucket = google_storage_bucket.bucket.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}    
