output "bucket_name" {
  description = "The name of the storage bucket"
  value       = google_storage_bucket.bucket.name
}

output "bucket_url" {
  description = "Cloud Storageバケットのurl"
  value       = "gs://${google_storage_bucket.bucket.name}"
}

output "logo_url" {
  description = "ロゴファイルのURL"
  value       = var.upload_logo ? "gs://${google_storage_bucket.bucket.name}/${google_storage_bucket_object.logo[0].name}" : ""
}

output "bucket_id" {
  description = "The ID of the storage bucket"
  value       = google_storage_bucket.bucket.id
}  
