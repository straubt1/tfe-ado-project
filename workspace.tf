# Create the TFE workspace to integrate with

resource "tfe_workspace" "terraform" {
  organization      = var.tfeOrganizationName
  name              = var.tfeWorkspaceName
  terraform_version = "0.12.26"
}
