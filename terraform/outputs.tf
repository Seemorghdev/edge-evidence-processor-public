output "job_id" {
  description = "Fully qualified Cloud Run Job identifier."
  value       = google_cloud_run_v2_job.processor.id
}

output "job_name" {
  description = "Cloud Run Job name."
  value       = google_cloud_run_v2_job.processor.name
}

output "location" {
  description = "Cloud Run Job region."
  value       = google_cloud_run_v2_job.processor.location
}
