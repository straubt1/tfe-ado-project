#!/usr/bin/python

import sys
import os
import requests
import json
import argparse

# Parse arguments, these can be set via parameters or environment variables
parser = argparse.ArgumentParser(
    description='Get the TFE Workspace Id when given the Workspace Name.')
parser.add_argument('-tfeToken',
                    default=os.environ.get('TFETOKEN'),
                    help='API Token used to authenticate to TFE.')
parser.add_argument('-tfeHostname',
                    default=os.environ.get('TFEHOSTNAME'),
                    help="TFE Hostname (i.e. terraform.company.com")
parser.add_argument('-tfeOrganizationName',
                    default=os.environ.get('TFEORGANIZATIONNAME'),
                    help="TFE Organization Name (i.e. hashicorp-dev")
parser.add_argument('-tfeWorkspaceId',
                    default=os.environ.get('TFEWORKSPACEID'),
                    help="TFE Workspace Id (i.e. ws-zzzzzzzzzz")
parser.add_argument('-tfeArchiveFileName',
                    default=os.environ.get('TFEARCHIVEFILENAME'),
                    help="The name of the archive file containing the terraform code.")
parser.add_argument('-tfeSpeculativePlan',
                    default=False,
                    help="When True, trigger a speculative plan that can not be applied.")

# Throw exception if any arguments were not set
try:
    args = parser.parse_args()
    if None in vars(args).values():
        raise Exception('Missing required arguments')
except Exception:
    parser.print_help()
    raise

# Assign local variables
tfeToken = args.tfeToken
tfeHostname = args.tfeHostname
tfeOrganizationName = args.tfeOrganizationName
tfeWorkspaceId = args.tfeWorkspaceId
tfeArchiveFileName = args.tfeArchiveFileName
# Convert string to boolean using json
tfeSpeculativePlan = json.loads(args.tfeSpeculativePlan.lower())

print(f'tfeToken:{tfeToken}')
print(f'tfeHostname:{tfeHostname}')
print(f'tfeOrganizationName:{tfeOrganizationName}')
print(f'tfeWorkspaceId:{tfeWorkspaceId}')
print(f'tfeArchiveFileName:{tfeArchiveFileName}')
print(f'tfeSpeculativePlan:{tfeSpeculativePlan}')

tfConfig = {
    "data":
    {
        "type": "configuration-versions",
        "attributes": {
            "auto-queue-runs": False,
            "speculative": tfeSpeculativePlan
        }
    }
}

resp = requests.post(f'https://{tfeHostname}/api/v2/workspaces/{tfeWorkspaceId}/configuration-versions',
                     headers={'Authorization': f'Bearer {tfeToken}',
                              'Content-Type': 'application/vnd.api+json'},
                     data=json.dumps(tfConfig)
                     )
f = open("postConfigurationVersion.json", "w")
f.write(resp.text)
f.close()
print(
    f'##vso[artifact.upload containerfolder=apicalls;artifactname=postConfigurationVersion.json;]{os.getcwd()}/postConfigurationVersion.json')

tfeConfigurationVersionId = resp.json()['data']['id']
tfeConfigurationVersionUploadUrl = resp.json(
)['data']['attributes']['upload-url']
print(
    f'##vso[task.setvariable variable=tfeConfigurationVersionId;]{tfeConfigurationVersionId}')
print(
    f'##vso[task.setvariable variable=tfeConfigurationVersionUploadUrl;]{tfeConfigurationVersionUploadUrl}')

print(f'tfeConfigurationVersionId:{tfeConfigurationVersionId}')
print(f'tfeConfigurationVersionUploadUrl:{tfeConfigurationVersionUploadUrl}')

resp = requests.put(tfeConfigurationVersionUploadUrl,
                    headers={'Authorization': f'Bearer {tfeToken}',
                             'Content-Type': 'application/octet-stream'},
                    data=open(tfeArchiveFileName, 'rb').read()
                    )

# a
