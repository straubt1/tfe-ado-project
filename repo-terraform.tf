# Create the AzDO Git Repo to hold our terraform code
# Import our pipeline code into the repo

resource "azuredevops_git_repository" "terraform" {
  project_id = azuredevops_project.project.id
  name       = "terraform-code"
  initialization {
    init_type = "Clean"
  }
}

# Workaround since import doesnt work currently on new git repo's
# Sync this repo's subfolder to the ADO git repo
resource "null_resource" "terraform-repo-import" {
  # Complexity to checksum all the files in the directory and join them into a string
  # Any change to the directory will cause this to trigger
  triggers = {
    file_contents = join("", [
      for file in fileset("${abspath(path.module)}/repo-terraform-code/", "**") : filemd5(format("%s/repo-terraform-code/%s", abspath(path.module), file))
    ])
    files = join("", fileset("${abspath(path.module)}/repo-terraform-code/", "**"))
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

# Build AzDO Pipelines
resource "azuredevops_build_definition" "pipelines" {
  for_each = {
    "Plan"              = "ci/tfe-run-plan.yml",
    "Plan and Apply"    = "ci/tfe-run-plan-apply.yml",
    "Destroy"           = "ci/tfe-run-destroy.yml",
    "Destroy and Apply" = "ci/tfe-run-destroy-apply.yml",
  }

  project_id = azuredevops_project.project.id
  name       = format("Terraform Pipeline - %s", each.key)

  repository {
    repo_type   = "TfsGit"
    repo_id     = azuredevops_git_repository.terraform.id
    branch_name = azuredevops_git_repository.terraform.default_branch
    yml_path    = each.value
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

# Not implemented yet
# resource "azuredevops_resource_authorization" "pipelines" {
#   for_each = azuredevops_build_definition.pipelines
#
#   repo_id  = azuredevops_project.project.id
#   resource_id = each.value.id
#   authorized  = true
# }

# [Temporary] Call the undocumented pipeline permissions API to allow these pipelines
# to resource the pipeline-code repository
resource "null_resource" "pipelines" {
  for_each = azuredevops_build_definition.pipelines
  triggers = { for r in azuredevops_build_definition.pipelines : r.id => r.id }

  provisioner "local-exec" {
    command = <<EOF
id=${each.value.id}
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

# ADO git repo's do not support `pr` triggers via .yml
# So we must use the branch policy to trigger a speculative plan
# On a PR into the default branch
# resource "azuredevops_branch_policy_build_validation" "terraform-pr" {
#   project_id = azuredevops_project.project.id

#   # Setting this to true will block all master pushes
#   # But we need to be able to push code from this terraform run
#   enabled  = false
#   blocking = false

#   settings {
#     display_name        = "TFE Speculative Plan (pre-merge check)."
#     build_definition_id = azuredevops_build_definition.plan-speculative.id
#     valid_duration      = 720

#     scope {
#       repository_id  = azuredevops_git_repository.terraform.id
#       repository_ref = azuredevops_git_repository.terraform.default_branch
#       match_type     = "Exact"
#     }
#   }
# }
