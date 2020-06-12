#!/bin/bash

echo "test"

tfe_response=$(curl -s \
  --header "Authorization: Bearer ${TFETOKEN}" \
  --header "Content-Type: application/vnd.api+json" \
  https://${TFEHOSTNAME}/api/v2/organizations/${TFEORGANIZATIONNAME}/workspaces/${TFEWORKSPACENAME})

echo "Response: ${tfe_response}"

workspace_id=$(echo ${tfe_response} | jq -r '.data.id')
echo ${workspace_id}
 
echo "##vso[task.setvariable variable=WorkspaceId;]${workspace_id}"