output "vpc_id" {
  description = "ID of the VPC."
  value       = aws_vpc.main.id
}

output "public_subnet_id" {
  description = "ID of the public subnet."
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "ID of the application security group."
  value       = aws_security_group.app.id
}

output "instance_id" {
  description = "ID of the application VM."
  value       = aws_instance.app.id
}

output "instance_public_ip" {
  description = "Public IP address of the application VM."
  value       = aws_instance.app.public_ip
}

output "app_url" {
  description = "URL the application would be served on."
  value       = "http://${aws_instance.app.public_ip}:${var.app_port}"
}

output "backup_bucket" {
  description = "Name of the versioned S3 bucket for backups."
  value       = aws_s3_bucket.backups.bucket
}
