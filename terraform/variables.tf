variable "project_id" {
  description = "Google Cloud project containing the pre-authorized Cloud Run Job."
  type        = string
}

variable "region" {
  description = "Google Cloud region for the job."
  type        = string
}

variable "image" {
  description = "Immutable processor container image reference by sha256 digest."
  type        = string

  validation {
    condition     = can(regex("@sha256:[0-9a-f]{64}$", var.image))
    error_message = "image must be an immutable container reference ending in @sha256:<64 lowercase hex characters>."
  }
}

variable "service_account_email" {
  description = "Existing service-account identity assigned to the job. IAM is managed elsewhere."
  type        = string
}

variable "database_path" {
  description = "Absolute in-container path to the existing migrated SQLite authority file."
  type        = string

  validation {
    condition     = startswith(var.database_path, "/") && var.database_path != "/"
    error_message = "database_path must be an absolute in-container file path."
  }
}

variable "spool_root" {
  description = "Absolute in-container path to the existing writable processor spool directory."
  type        = string

  validation {
    condition     = startswith(var.spool_root, "/") && var.spool_root != "/"
    error_message = "spool_root must be an absolute in-container directory path."
  }
}

variable "job_name" {
  description = "Cloud Run Job name."
  type        = string
  default     = "edge-evidence-processor"
}

variable "timeout_seconds" {
  description = "Maximum task runtime in seconds."
  type        = number
  default     = 3600
}

variable "max_retries" {
  description = "Cloud Run task retries. Processor idempotency makes retries safe."
  type        = number
  default     = 1
}

variable "cpu" {
  description = "Container CPU limit."
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Container memory limit."
  type        = string
  default     = "512Mi"
}
