output "app_config_path" {
  description = "Path to generated app config"
  value       = local_file.app_config.filename
}

output "env_file_path" {
  description = "Path to generated .env file"
  value       = local_file.env_file.filename
}

output "dockerfile_path" {
  description = "Path to generated Dockerfile"
  value       = local_file.dockerfile.filename
}

output "deployment_summary" {
  description = "Deployment summary"
  value = {
    app_name    = var.app_name
    environment = var.environment
    port        = var.app_port
    log_level   = var.log_level
  }
}
