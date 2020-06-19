resource "azuredevops_git_repository" "pipeline" {
  project_id = azuredevops_project.project.id
  name       = "terraform-pipeline"
  initialization {
    init_type = "Clean"
  }
}

# Workaround since import doesnt work currently on new git repo's
# Sync this repo's subfolder to the ADO git repo
resource "null_resource" "pipeline-repo-import" {
  # Complexity to checksum all the files in the directory and join them into a string
  # Any change to the directory will cause this to fire
  triggers = {
    check = join("", [
      for file in fileset("${abspath(path.module)}/repo-pipeline-code", "*") : filemd5(format("%s/repo-pipeline-code/%s", abspath(path.module), file))
    ])
    # force = timestamp()
  }

  provisioner "local-exec" {
    command = <<EOF
mkdir -p /tmp/${azuredevops_git_repository.pipeline.name}
cd /tmp/${azuredevops_git_repository.pipeline.name}
git clone ${azuredevops_git_repository.pipeline.ssh_url} .
mkdir pipeline
cp ${abspath(path.module)}/repo-pipeline-code/* ./pipeline
git add .
git commit -m "Updating repo files $(date)."
git push origin master
rm -rf /tmp/${azuredevops_git_repository.pipeline.name}
EOF
  }
}