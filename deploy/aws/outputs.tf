output "instance_id" {
  value = aws_instance.codesentinel.id
}

output "public_ip" {
  value = aws_instance.codesentinel.public_ip
}

output "dashboard_url" {
  value = "http://${aws_instance.codesentinel.public_ip}"
}

output "grafana_url" {
  value = "http://${aws_instance.codesentinel.public_ip}:3001"
}

output "github_actions_role_arn" {
  value = aws_iam_role.github_actions.arn
}

output "ecr_registry" {
  value = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
}
