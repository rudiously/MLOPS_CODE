variable "aws_region" {
  description = "AWS region for the CodeSentinel staging stack."
  type        = string
}

variable "instance_type" {
  description = "EC2 type; t3.small is a practical minimum for this stack. Free Tier eligibility depends on account age and plan."
  type        = string
  default     = "t3.small"
}

variable "web_cidr" {
  description = "CIDR allowed to open the HTTP dashboard. Use 0.0.0.0/0 only for a public demo."
  type        = string
  default     = "0.0.0.0/0"
}

variable "grafana_admin_cidr" {
  description = "Operator public IP range in CIDR notation, for example 203.0.113.10/32."
  type        = string
  nullable    = false
}

variable "app_env_parameter_name" {
  description = "Pre-created SSM SecureString containing the production .env variables."
  type        = string
  default     = "/codesentinel/prod/app-env"
}
