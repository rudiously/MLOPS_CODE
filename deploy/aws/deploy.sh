#!/usr/bin/env bash
set -euo pipefail

image_tag="${1:?usage: deploy.sh IMAGE_TAG}"
cd /opt/codesentinel
set -a
source ./.aws-runtime
set +a
export AWS_DEFAULT_REGION="${AWS_REGION}"
export IMAGE_TAG="${image_tag}"

aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ECR_REGISTRY}"
git fetch origin main
git checkout -f main
git reset --hard origin/main
docker compose -f deploy/aws/docker-compose.yml pull
docker compose -f deploy/aws/docker-compose.yml up -d --remove-orphans
