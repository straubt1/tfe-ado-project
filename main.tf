# Make sure to set the following environment variables:
#   AZDO_PERSONAL_ACCESS_TOKEN
#   AZDO_ORG_SERVICE_URL
provider "azuredevops" {
  version = ">= 0.0.1"
}

resource "random_pet" "project" {
  length = 3
}

resource "azuredevops_project" "project" {
  project_name = random_pet.project.id
  description  = "Terraform build ADO Project"
}

resource "azuredevops_git_repository" "repo-clean" {
  project_id = azuredevops_project.project.id
  name       = "terraform-demo"
  initialization {
    init_type = "Clean"
  }
}

# Workaround since import doesnt work currently on new git repo's
# Seed new repo with pipeline files
resource "null_resource" "repo-clean-import" {
  # Complexity to checksum all the files in the pipeline directory and join them into a string
  # Any change to the directory will cause this to fire
  triggers = {
    check = join("", [
      for file in fileset("${abspath(path.module)}/pipeline", "*") : filemd5(format("%s/pipeline/%s", abspath(path.module), file))
    ])
  }

  provisioner "local-exec" {
    command = <<EOF
mkdir -p /tmp/testrepoimport
cd /tmp/testrepoimport
git clone ${azuredevops_git_repository.repo-clean.ssh_url} .
cp ${abspath(path.module)}/pipeline/* .
git add .
git commit -m "Terraform updating pipeline file $(date)."
git push origin master
rm -rf /tmp/testrepoimport
EOF
  }
}

# resource "azuredevops_variable_group" "tfe" {
#   project_id   = azuredevops_project.project.id
#   name         = "Terraform Pipeline Variables"
#   description  = "Managed by Terraform"
#   allow_access = true

#   variable {
#     name  = "tfeHostName"
#     value = var.tfeHostName
#   }
#   variable {
#     name  = "tfeOrganizationName"
#     value = var.tfeOrganizationName
#   }
#   variable {
#     name  = "tfeWorkspaceName"
#     value = var.tfeWorkspaceName
#   }
#   variable {
#     name  = "tfeToken"
#     value = var.tfeToken
#   }
# }

resource "azuredevops_build_definition" "build" {
  project_id = azuredevops_project.project.id
  name       = "Sample Build Definition"
  path       = "\\ExampleFolder"

  repository {
    repo_type   = "TfsGit"
    repo_id     = azuredevops_git_repository.repo-clean.id
    branch_name = azuredevops_git_repository.repo-clean.default_branch
    yml_path    = "azure-pipelines.yml"
  }

  # variable_groups = [
  #   azuredevops_variable_group.tfe.id
  # ]

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
    name  = "tfeToken"
    value = var.tfeToken
    # is_secret = true
  }

  variable {
    name  = "PipelineVariable"
    value = "Go Microsoft!"
  }

  variable {
    name      = "PipelineSecret"
    value     = "ZGV2cw"
    is_secret = true
  }
}