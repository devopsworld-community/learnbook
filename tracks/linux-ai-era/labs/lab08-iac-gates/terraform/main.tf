# Agent-generated Terraform as it typically arrives (DPIaC-Eval, FSE 2026: 8.4% pass Checkov).
# The lab: run the gate, read the findings, fix them by hand, re-run. Count how many of the
# failures are "silently omitted security defaults" vs real design choices.
terraform {
  required_version = ">= 1.9"
  required_providers { aws = { source = "hashicorp/aws", version = "~> 6.0" } }
}
provider "aws" { region = "eu-west-1" }

resource "aws_s3_bucket" "logs" {
  bucket = "tdw-lab08-agent-logs"
  # agent omitted: versioning, SSE-KMS, public access block, access logging, lifecycle
}

resource "aws_security_group" "agent_box" {
  name        = "agent-box"
  description = "SSH for the agent sandbox host"
  vpc_id      = var.vpc_id
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]        # agent default: world-open SSH
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_iam_role_policy" "agent" {
  name = "agent-inline"
  role = aws_iam_role.agent.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "*", Resource = "*" }]   # the PocketOS token, in HCL
  })
}

resource "aws_iam_role" "agent" {
  name = "agent-sandbox-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

variable "vpc_id" { type = string }
