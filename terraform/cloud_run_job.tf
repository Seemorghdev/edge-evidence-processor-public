resource "google_cloud_run_v2_job" "processor" {
  name                = var.job_name
  project             = var.project_id
  location            = var.region
  deletion_protection = false

  template {
    task_count  = 1
    parallelism = 1

    template {
      service_account = var.service_account_email
      timeout         = "${var.timeout_seconds}s"
      max_retries     = var.max_retries

      containers {
        image = var.image
        args = [
          "run",
          "--database",
          var.database_path,
          "--spool-root",
          var.spool_root,
        ]

        resources {
          limits = {
            cpu    = var.cpu
            memory = var.memory
          }
        }
      }
    }
  }
}
