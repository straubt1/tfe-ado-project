resource "azuredevops_git_repository" "terraform" {
  project_id = azuredevops_project.project.id
  name       = "terraform-code"
  initialization {
    init_type = "Clean"
  }
}

resource "tfe_workspace" "terraform" {
  organization      = var.tfeOrganizationName
  name              = var.tfeWorkspaceName
  terraform_version = "0.12.26"
}

# Workaround since import doesnt work currently on new git repo's
# Sync this repo's subfolder to the ADO git repo
resource "null_resource" "terraform-repo-import" {
  # Complexity to checksum all the files in the directory and join them into a string
  # Any change to the directory will cause this to fire
  triggers = {
    check = join("", [
      for file in fileset("${abspath(path.module)}/repo-terraform-code/", "**") : filemd5(format("%s/repo-terraform-code/%s", abspath(path.module), file))
    ])
    force = timestamp()
  }

  provisioner "local-exec" {
    command = <<EOF
mkdir -p /tmp/${azuredevops_git_repository.terraform.name}
cd /tmp/${azuredevops_git_repository.terraform.name}
git clone ${azuredevops_git_repository.terraform.ssh_url} .
cp -rf ${abspath(path.module)}/repo-terraform-code/* ./
git add .
git commit -m "Syncing repo files $(date)."
git push origin master
rm -rf /tmp/${azuredevops_git_repository.terraform.name}
EOF
  }
}

# Build Pipelines
resource "azuredevops_build_definition" "plan-apply" {
  project_id = azuredevops_project.project.id
  name       = "Terraform Pipeline - Run Apply"

  repository {
    repo_type   = "TfsGit"
    repo_id     = azuredevops_git_repository.terraform.id
    branch_name = azuredevops_git_repository.terraform.default_branch
    yml_path    = "ci/tfe-run-apply.yml"
  }

  ci_trigger {
    use_yaml = true
  }

  variable_groups = [
    azuredevops_variable_group.tfe.id
  ]

  variable {
    name  = "tfeWorkspaceName"
    value = tfe_workspace.terraform.name
  }
}

resource "azuredevops_build_definition" "plan-speculative" {
  project_id = azuredevops_project.project.id
  name       = "Terraform Pipeline - Run Speculative"

  repository {
    repo_type   = "TfsGit"
    repo_id     = azuredevops_git_repository.terraform.id
    branch_name = azuredevops_git_repository.terraform.default_branch
    yml_path    = "ci/tfe-run-speculative.yml"
  }

  ci_trigger {
    use_yaml = true
  }

  variable_groups = [
    azuredevops_variable_group.tfe.id
  ]

  variable {
    name  = "tfeWorkspaceName"
    value = tfe_workspace.terraform.name
  }
}

resource "azuredevops_build_definition" "destroy" {
  project_id = azuredevops_project.project.id
  name       = "Terraform Pipeline - Destroy"

  repository {
    repo_type   = "TfsGit"
    repo_id     = azuredevops_git_repository.terraform.id
    branch_name = azuredevops_git_repository.terraform.default_branch
    yml_path    = "ci/tfe-destroy.yml"
  }

  ci_trigger {
    use_yaml = true
  }

  variable_groups = [
    azuredevops_variable_group.tfe.id
  ]

  variable {
    name  = "tfeWorkspaceName"
    value = tfe_workspace.terraform.name
  }
}

resource "azuredevops_build_definition" "destroy-speculative" {
  project_id = azuredevops_project.project.id
  name       = "Terraform Pipeline - Destroy Speculative"

  repository {
    repo_type   = "TfsGit"
    repo_id     = azuredevops_git_repository.terraform.id
    branch_name = azuredevops_git_repository.terraform.default_branch
    yml_path    = "ci/tfe-destroy-speculative.yml"
  }

  ci_trigger {
    use_yaml = true
  }

  variable_groups = [
    azuredevops_variable_group.tfe.id
  ]

  variable {
    name  = "tfeWorkspaceName"
    value = tfe_workspace.terraform.name
  }
}

# ADO git repo's do not support `pr` triggers via .yml
# So we must use the branch policy to trigger a speculative plan
# On a PR into the default branch
resource "azuredevops_branch_policy_build_validation" "terraform-pr" {
  project_id = azuredevops_project.project.id

  # Setting this to true will block all master pushes
  # But we need to be able to push code from this terraform run
  enabled  = true
  blocking = false

  settings {
    display_name        = "TFE Speculative Plan (pre-merge check)."
    build_definition_id = azuredevops_build_definition.plan-speculative.id
    valid_duration      = 720

    scope {
      repository_id  = azuredevops_git_repository.terraform.id
      repository_ref = azuredevops_git_repository.terraform.default_branch
      match_type     = "Exact"
    }
  }
}

# Not implemented yet
# resource "azuredevops_resource_authorization" "plan-speculative" {
#   project_id  = azuredevops_project.project.id
#   resource_id = azuredevops_build_definition.plan-speculative.id
#   authorized  = true
# }

resource "null_resource" "pipeline-perm-plan-apply" {
  triggers = {
    id = azuredevops_build_definition.plan-apply.id
  }

  provisioner "local-exec" {
    command = <<EOF
id=${azuredevops_build_definition.plan-apply.id}
payload="{ \"pipelines\": [{ \"id\": $id, \"authorized\": true }]}"
echo $id
echo $payload
curl \
  -u tstraub:$AZDO_PERSONAL_ACCESS_TOKEN \
  -H "Content-Type: application/json" \
  --request PATCH \
  --data "$payload" \
  $AZDO_ORG_SERVICE_URL/${azuredevops_project.project.project_name}/_apis/pipelines/pipelinePermissions/repository/${azuredevops_git_repository.pipeline.project_id}.${azuredevops_git_repository.pipeline.id}?api-version=5.1-preview.1 | jq .
EOF
  }
}

resource "null_resource" "pipeline-perm-plan-speculative" {
  triggers = {
    id = azuredevops_build_definition.plan-speculative.id
  }

  provisioner "local-exec" {
    command = <<EOF
id=${azuredevops_build_definition.plan-speculative.id}
payload="{ \"pipelines\": [{ \"id\": $id, \"authorized\": true }]}"
echo $id
echo $payload
curl \
  -u tstraub:$AZDO_PERSONAL_ACCESS_TOKEN \
  -H "Content-Type: application/json" \
  --request PATCH \
  --data "$payload" \
  $AZDO_ORG_SERVICE_URL/${azuredevops_project.project.project_name}/_apis/pipelines/pipelinePermissions/repository/${azuredevops_git_repository.pipeline.project_id}.${azuredevops_git_repository.pipeline.id}?api-version=5.1-preview.1 | jq .
EOF
  }
}

resource "null_resource" "pipeline-perm-destroy" {
  triggers = {
    id = azuredevops_build_definition.destroy.id
  }

  provisioner "local-exec" {
    command = <<EOF
id=${azuredevops_build_definition.destroy.id}
payload="{ \"pipelines\": [{ \"id\": $id, \"authorized\": true }]}"
echo $id
echo $payload
curl \
  -u tstraub:$AZDO_PERSONAL_ACCESS_TOKEN \
  -H "Content-Type: application/json" \
  --request PATCH \
  --data "$payload" \
  $AZDO_ORG_SERVICE_URL/${azuredevops_project.project.project_name}/_apis/pipelines/pipelinePermissions/repository/${azuredevops_git_repository.pipeline.project_id}.${azuredevops_git_repository.pipeline.id}?api-version=5.1-preview.1 | jq .
EOF
  }
}

resource "null_resource" "pipeline-perm-destroy-speculative" {
  triggers = {
    id = azuredevops_build_definition.destroy-speculative.id
  }

  provisioner "local-exec" {
    command = <<EOF
id=${azuredevops_build_definition.destroy-speculative.id}
payload="{ \"pipelines\": [{ \"id\": $id, \"authorized\": true }]}"
echo $id
echo $payload
curl \
  -u tstraub:$AZDO_PERSONAL_ACCESS_TOKEN \
  -H "Content-Type: application/json" \
  --request PATCH \
  --data "$payload" \
  $AZDO_ORG_SERVICE_URL/${azuredevops_project.project.project_name}/_apis/pipelines/pipelinePermissions/repository/${azuredevops_git_repository.pipeline.project_id}.${azuredevops_git_repository.pipeline.id}?api-version=5.1-preview.1 | jq .
EOF
  }
}

