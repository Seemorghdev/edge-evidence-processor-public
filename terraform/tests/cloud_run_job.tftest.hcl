mock_provider "google" {}

run "plans_real_processor_job" {
  command = plan

  variables {
    project_id            = "example-project"
    region                = "us-central1"
    image                 = "us-docker.pkg.dev/example-project/edge-evidence/processor@sha256:0000000000000000000000000000000000000000000000000000000000000000"
    service_account_email = "processor@example-project.iam.gserviceaccount.com"
    database_path         = "/opt/edge-evidence-processor/fixture/authority.sqlite3"
    spool_root            = "/opt/edge-evidence-processor/fixture/spool"
  }
}

run "rejects_mutable_image_tag" {
  command = plan

  variables {
    project_id            = "example-project"
    region                = "us-central1"
    image                 = "us-docker.pkg.dev/example-project/edge-evidence/processor:latest"
    service_account_email = "processor@example-project.iam.gserviceaccount.com"
    database_path         = "/data/authority.sqlite3"
    spool_root            = "/data/spool"
  }

  expect_failures = [var.image]
}
