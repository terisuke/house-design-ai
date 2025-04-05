output "bucket_name" {
  description = "The name of the storage bucket"
  value       = google_storage_bucket.bucket.name
}

output "bucket_url" {
  description = "The URL of the storage bucket"
  value       = google_storage_bucket.bucket.url
}

output "bucket_id" {
  description = "The ID of the storage bucket"
  value       = google_storage_bucket.bucket.id
} 
