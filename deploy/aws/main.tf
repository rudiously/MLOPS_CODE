terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.80, < 7.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
data "aws_kms_alias" "ssm" {
  name = "alias/aws/ssm"
}
data "aws_availability_zones" "available" {
  state = "available"
}
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

locals {
  ecr_repositories = toset(["codesentinel-api", "codesentinel-model", "codesentinel-frontend"])
  oidc_subject     = "repo:rudiously@194351773/MLOPS_CODE@1421233873:ref:refs/heads/main"
}

resource "aws_vpc" "codesentinel" {
  cidr_block           = "10.73.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = { Name = "codesentinel" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.codesentinel.id
  cidr_block              = "10.73.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
  tags                    = { Name = "codesentinel-public" }
}

resource "aws_internet_gateway" "codesentinel" {
  vpc_id = aws_vpc.codesentinel.id
  tags   = { Name = "codesentinel" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.codesentinel.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.codesentinel.id
  }
  tags = { Name = "codesentinel-public" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "codesentinel" {
  name        = "codesentinel"
  description = "Public app; Grafana is limited to the administrator CIDR."
  vpc_id      = aws_vpc.codesentinel.id

  ingress {
    description = "Demo frontend over HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = [var.web_cidr]
  }

  ingress {
    description = "Grafana restricted to the administrator CIDR"
    from_port   = 3001
    to_port     = 3001
    protocol    = "tcp"
    cidr_blocks = [var.grafana_admin_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "codesentinel" }
}

resource "aws_ecr_repository" "images" {
  for_each             = local.ecr_repositories
  name                 = each.value
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  encryption_configuration { encryption_type = "AES256" }
}

resource "aws_iam_role" "ec2" {
  name = "codesentinel-ec2"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_instance" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "ecr_pull" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy" "read_app_config" {
  name = "codesentinel-read-app-config"
  role = aws_iam_role.ec2.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["ssm:GetParameter"]
      Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter${var.app_env_parameter_name}"
    }, {
      Effect   = "Allow"
      Action   = ["kms:Decrypt"]
      Resource = data.aws_kms_alias.ssm.target_key_arn
    }]
  })
}

resource "aws_iam_instance_profile" "codesentinel" {
  name = "codesentinel-ec2"
  role = aws_iam_role.ec2.name
}

resource "aws_instance" "codesentinel" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.codesentinel.id]
  iam_instance_profile        = aws_iam_instance_profile.codesentinel.name
  associate_public_ip_address = true
  user_data_replace_on_change = true

  root_block_device {
    volume_size           = 24
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  user_data = templatefile("${path.module}/user-data.sh.tftpl", {
    repo_url               = "https://github.com/rudiously/MLOPS_CODE.git"
    aws_region             = var.aws_region
    app_env_parameter_name = var.app_env_parameter_name
    ecr_registry           = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
  })

  depends_on = [aws_route_table_association.public]
  tags       = { Name = "codesentinel", Project = "MLOPS_CODE" }
}

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

resource "aws_iam_role" "github_actions" {
  name = "codesentinel-github-actions"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          "token.actions.githubusercontent.com:sub" = local.oidc_subject
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_deploy" {
  name = "codesentinel-publish-and-deploy"
  role = aws_iam_role.github_actions.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:DescribeRepositories",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
        ]
        Resource = [for repo in aws_ecr_repository.images : repo.arn]
      },
      {
        Effect = "Allow"
        Action = ["ssm:SendCommand"]
        Resource = [
          "arn:aws:ssm:${var.aws_region}::document/AWS-RunShellScript",
          aws_instance.codesentinel.arn,
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["ssm:GetCommandInvocation"]
        Resource = "*"
      },
    ]
  })
}
