variable "aws_region" {
  description = "AWS region used by the provider."
  type        = string
  default     = "us-east-1"
}

variable "aws_endpoint" {
  description = "URL of the local AWS emulator (Moto server or LocalStack)."
  type        = string
  default     = "http://localhost:4566"
}

variable "project_name" {
  description = "Short name used as a prefix for every resource."
  type        = string
  default     = "task-tracker"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "The environment must be one of: dev, staging, prod."
  }
}

variable "vpc_cidr" {
  description = "CIDR block of the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block of the public subnet (must sit inside vpc_cidr)."
  type        = string
  default     = "10.20.1.0/24"
}

variable "availability_zone" {
  description = "Availability zone for the subnet and the VM."
  type        = string
  default     = "us-east-1a"
}

variable "instance_type" {
  description = "EC2 instance type of the application VM."
  type        = string
  default     = "t3.micro"
}

variable "ami_id" {
  description = "Machine image for the VM. Any ID is accepted by the local emulator."
  type        = string
  default     = "ami-0abcdef1234567890"
}

variable "allowed_ssh_cidr" {
  description = "Only this CIDR may reach port 22. Use your own IP with /32."
  type        = string
  default     = "203.0.113.10/32"
}

variable "app_port" {
  description = "Port the Task Tracker container listens on."
  type        = number
  default     = 8000
}

variable "container_image" {
  description = "Container image the VM runs on boot."
  type        = string
  default     = "ghcr.io/example/devops-task-tracker:latest"
}
