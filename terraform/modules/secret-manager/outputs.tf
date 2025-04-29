output "service_account_secret_id" {
  description = "サービスアカウントのシークレットID"
  value       = google_secret_manager_secret.service_account_secret.secret_id
}

output "service_account_secret_name" {
  description = "サービスアカウントのシークレット名（プロジェクトIDを含む）"
  value       = google_secret_manager_secret.service_account_secret.name
}
