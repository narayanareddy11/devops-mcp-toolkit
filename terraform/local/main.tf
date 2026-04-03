terraform {
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# ── Create a local config directory ──────────────────────────────────────────
resource "local_file" "app_config" {
  filename = "${path.module}/output/app.conf"
  content  = templatefile("${path.module}/templates/app.conf.tpl", {
    app_name    = var.app_name
    environment = var.environment
    port        = var.app_port
    log_level   = var.log_level
  })
}

resource "local_file" "env_file" {
  filename = "${path.module}/output/.env"
  content  = <<-EOT
    APP_NAME=${var.app_name}
    ENV=${var.environment}
    PORT=${var.app_port}
    LOG_LEVEL=${var.log_level}
    BUILD_DATE=${timestamp()}
  EOT
}

resource "local_file" "dockerfile" {
  filename = "${path.module}/output/Dockerfile"
  content  = <<-EOT
    FROM node:20-alpine
    WORKDIR /app
    ENV PORT=${var.app_port}
    ENV NODE_ENV=${var.environment}
    COPY package*.json ./
    RUN npm ci --only=production
    COPY . .
    EXPOSE ${var.app_port}
    CMD ["node", "server.js"]
  EOT
}

# ── Simulate a deployment step ────────────────────────────────────────────────
resource "null_resource" "deploy_check" {
  triggers = {
    config_hash = local_file.app_config.content
    env_hash    = local_file.env_file.content
  }

  provisioner "local-exec" {
    command = "echo '[Terraform] Deploying ${var.app_name} to ${var.environment} on port ${var.app_port}'"
  }
}
