resource "azuredevops_git_repository" "terraform" {
  project_id = azuredevops_project.project.id
  name       = "terraform-code"
  initialization {
    init_type = "Clean"
  }
}

# Workaround since import doesnt work currently on new git repo's
# Seed new repo with pipeline files
resource "null_resource" "terraform-repo-import" {
  # Complexity to checksum all the files in the pipeline directory and join them into a string
  # Any change to the directory will cause this to fire
  triggers = {
    check = join("", [
      for file in fileset("${abspath(path.module)}/repo-terraform-code", "*") : filemd5(format("%s/repo-terraform-code/%s", abspath(path.module), file))
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
# rm -rf /tmp/${azuredevops_git_repository.terraform.name}
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

  variable {
    name  = "tfeHostName"
    value = var.tfeHostName
  }
  variable {
    name  = "tfeOrganizationName"
    value = var.tfeOrganizationName
  }
  variable {
    name  = "tfeWorkspaceName"
    value = var.tfeWorkspaceName
  }
  variable {
    name      = "tfeToken"
    value     = var.tfeToken
    is_secret = true
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

  variable {
    name  = "tfeHostName"
    value = var.tfeHostName
  }
  variable {
    name  = "tfeOrganizationName"
    value = var.tfeOrganizationName
  }
  variable {
    name  = "tfeWorkspaceName"
    value = var.tfeWorkspaceName
  }
  variable {
    name      = "tfeToken"
    value     = var.tfeToken
    is_secret = true
  }
}
