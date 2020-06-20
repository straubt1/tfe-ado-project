# Terraform Code

This code represents a the Terraform code that would be ran as the 'root' module in a TFE Workspace.

The code lives at the root, however the pipeline can be configured to use a nested working directory.

## Resources

There are only a few resources created to help demonstrate flow through the environments.

## Pipelines

There are two pipelines:

- `tfe-run-speculative` will trigger a [Speculative Plan](https://www.terraform.io/docs/cloud/run/index.html#speculative-plans) that can not be applied.
- `tfe-run-apply` will trigger a run that will be auto applied if there are no planning/policy check errors.
 