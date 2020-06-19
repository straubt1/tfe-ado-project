# Make sure to set the following environment variables:
#   AZDO_PERSONAL_ACCESS_TOKEN
#   AZDO_ORG_SERVICE_URL
provider "azuredevops" {
  version = ">= 0.0.1"
}

# Make sure to set the following environment variables:
#   TFE_HOSTNAME
#   TFE_TOKEN
provider "tfe" {
  version = "~> 0.15.0"
}