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
      for file in fileset("${abspath(path.module)}/repo-terraform-code", "*") : filemd5(format("%s/repo-terraform-code/%s", abspath(path.module), file))
    ])
    # force = timestamp()
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

  variable_groups = [
    azuredevops_variable_group.tfe.id
  ]

  variable {
    name  = "tfeWorkspaceName"
    value = tfe_workspace.terraform.name
  }
}