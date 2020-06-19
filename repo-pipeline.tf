resource "azuredevops_git_repository" "pipeline" {
  project_id = azuredevops_project.project.id
  name       = "terraform-pipeline"
  initialization {
    init_type = "Clean"
  }
}

# Workaround since import doesnt work currently on new git repo's
# Seed new repo with pipeline files
resource "null_resource" "pipeline-repo-import" {
  # Complexity to checksum all the files in the pipeline directory and join them into a string
  # Any change to the directory will cause this to fire
  triggers = {
    check = join("", [
      for file in fileset("${abspath(path.module)}/pipeline", "*") : filemd5(format("%s/pipeline/%s", abspath(path.module), file))
    ])
  }

  provisioner "local-exec" {
    command = <<EOF
mkdir -p /tmp/${azuredevops_git_repository.pipeline.name}
cd /tmp/${azuredevops_git_repository.pipeline.name}
git clone ${azuredevops_git_repository.pipeline.ssh_url} .
mkdir pipeline
cp ${abspath(path.module)}/pipeline/* ./pipeline
git add .
git commit -m "Updating erraform pipeline files $(date)."
git push origin master
rm -rf /tmp/${azuredevops_git_repository.pipeline.name}
EOF
  }
}