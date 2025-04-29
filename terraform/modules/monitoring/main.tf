# 通知チャネル（メール）
resource "google_monitoring_notification_channel" "email" {
  display_name = "House Design AI Email Alerts"
  type         = "email"
  labels = {
    email_address = var.alert_email
  }
}

# エラーレートアラート（5xxエラーが5%を超えた場合）
resource "google_monitoring_alert_policy" "error_rate" {
  project               = var.project_id
  display_name          = "FreeCAD API Error Rate > 5%"
  combiner              = "OR"
  notification_channels = [google_monitoring_notification_channel.email.id]
  user_labels = {
    severity = "critical"
  }

  conditions {
    display_name = "Error Rate > 5% (MQL)"
    condition_monitoring_query_language {
      query    = <<EOT
fetch cloud_run_revision
| {
    metric 'run.googleapis.com/request_count'
| filter resource.service_name == 'freecad-api' && metric.response_code_class == '5xx'
| align rate(60s)
| group_by [resource.project_id, resource.service_name], [error_count: sum(value.request_count)]
  ;
    metric 'run.googleapis.com/request_count'
| filter resource.service_name == 'freecad-api'
| align rate(60s)
| group_by [resource.project_id, resource.service_name], [total_count: sum(value.request_count)]
  }
| join
| value [error_rate: val(0) / val(1)]
| condition error_rate > 0.05
EOT
      duration = "300s"
      trigger {
        count = 1
      }
    }
  }

  documentation {
    content   = "FreeCAD APIのエラーレートが5%を超えています。"
    mime_type = "text/markdown"
  }
}

# レイテンシーアラート（2秒を超えた場合）
resource "google_monitoring_alert_policy" "latency" {
  display_name = "FreeCAD API Latency > 2s"
  combiner     = "OR"

  conditions {
    display_name = "Latency > 2s"
    condition_threshold {
      filter          = <<-EOT
        metric.type="run.googleapis.com/request_latencies"
        resource.type="cloud_run_revision"
        resource.labels.service_name="freecad-api"
      EOT
      comparison      = "COMPARISON_GT"
      threshold_value = 2000
      duration        = "300s"

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_PERCENTILE_99"
        cross_series_reducer = "REDUCE_MEAN"
        group_by_fields      = ["resource.labels.project_id"]
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [
    google_monitoring_notification_channel.email.id
  ]

  documentation {
    content   = "FreeCAD APIのレイテンシーが2秒を超えています。"
    mime_type = "text/markdown"
  }

  user_labels = {
    severity = "warning"
  }
}

# メモリ使用率アラート（80%を超えた場合）
resource "google_monitoring_alert_policy" "memory_usage" {
  project               = var.project_id
  display_name          = "FreeCAD API Memory Usage > 80%"
  combiner              = "OR"
  notification_channels = [google_monitoring_notification_channel.email.id]
  user_labels = {
    severity = "warning"
  }

  conditions {
    display_name = "Memory Usage > 80%"
    condition_threshold {
      filter          = "metric.type=\"run.googleapis.com/container/memory/utilization\" AND resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"freecad-api\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.8 # 80% utilization

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }

      trigger {
        count = 1
      }
    }
  }

  documentation {
    content   = "FreeCAD APIのメモリ使用率が80%を超えています。"
    mime_type = "text/markdown"
  }
}
