output "notification_channel_id" {
  description = "作成された通知チャネルのID"
  value       = google_monitoring_notification_channel.email.id
}

output "error_rate_alert_id" {
  description = "エラーレートアラートポリシーのID"
  value       = google_monitoring_alert_policy.error_rate.id
}

output "latency_alert_id" {
  description = "レイテンシーアラートポリシーのID"
  value       = google_monitoring_alert_policy.latency.id
}

output "memory_usage_alert_id" {
  description = "メモリ使用率アラートポリシーのID"
  value       = google_monitoring_alert_policy.memory_usage.id
}
