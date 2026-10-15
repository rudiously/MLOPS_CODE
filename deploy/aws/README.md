# AWS staging deployment

This stack runs the API, separate model server, PostgreSQL, frontend, Prometheus, and Grafana on one EC2 host. GitHub Actions builds versioned images in ECR, then uses GitHub OIDC and AWS Systems Manager to deploy the exact commit. There are no SSH keys or long-lived AWS credentials in the repository.

## Before creating AWS resources

1. Check your AWS account's Free Tier plan and region. The default `t3.small` is chosen because this five-service stack needs more memory than a `t3.micro`; Free Tier eligibility depends on when the account was created and its current plan. A public IPv4 address and EBS storage can also incur charges. Review the Terraform plan and AWS pricing before applying it.
2. Set `grafana_admin_cidr` to your current public IP in `/32` form. Grafana is not open to the whole internet. The frontend is plain HTTP for a demo; use a domain and TLS termination before treating it as production.
3. Create a local `prod.env` file with strong, random values. Do not commit it:

   ```dotenv
   POSTGRES_PASSWORD=replace-with-a-long-random-alphanumeric-value
   JWT_SECRET=replace-with-a-long-random-value
   WEBHOOK_SECRET=replace-with-a-long-random-value
   GRAFANA_ADMIN_USER=admin
   GRAFANA_ADMIN_PASSWORD=replace-with-a-long-random-value
   GITHUB_CHECKS_ENABLED=false
   REQUIRE_DASHBOARD_AUTH=true
   ```

4. Store it as an AWS Systems Manager SecureString before the EC2 instance starts:

   ```sh
   aws ssm put-parameter \
     --region YOUR_AWS_REGION \
     --name /codesentinel/prod/app-env \
     --type SecureString \
     --overwrite \
     --value file://prod.env
   ```

## Provision the stack

Use an AWS account profile you control. Terraform creates an EC2 instance, private service network, ECR repositories, a GitHub OIDC provider and branch-scoped role, and the IAM permissions needed for image publishing and SSM deployment.

```sh
cd deploy/aws
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: choose your region and put your IP in grafana_admin_cidr.
terraform init
terraform plan
terraform apply
```

If the AWS account already has the GitHub OIDC provider, import it into this Terraform state before applying:

```sh
terraform import aws_iam_openid_connect_provider.github \
  arn:aws:iam::YOUR_AWS_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com
```

The EC2 bootstrap retrieves the SecureString using its instance role, installs Docker Compose, and checks out this public repository. The instance is managed through SSM; no inbound SSH port is opened.

## Enable GitHub Actions deployment

After Terraform finishes, add these **repository variables** in GitHub → Settings → Secrets and variables → Actions → Variables:

- `AWS_REGION`: the same region used for Terraform
- `AWS_ROLE_ARN`: `terraform output -raw github_actions_role_arn`
- `AWS_EC2_INSTANCE_ID`: `terraform output -raw instance_id`

The workflow runs tests and builds images on every push and pull request. On pushes to `main`, it also publishes images and deploys through OIDC once the three repository variables are set. Until then, image publishing and deployment are skipped while CI remains runnable.

After a successful deploy, Terraform outputs the dashboard URL and the Grafana URL. Grafana is reachable only from the CIDR you configured; its admin password is in the SecureString, not in the workflow.

## Remove the stack

Run `terraform destroy` from this directory to remove the EC2 host, ECR repositories, networking, and IAM resources created by this stack. Back up anything you need first; the database volume is deleted with the instance.
