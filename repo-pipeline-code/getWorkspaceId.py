#!/usr/bin/python

import sys
import os
import requests
import argparse

# Parse arguments, these can be set via parameters or environment variables
parser = argparse.ArgumentParser(
    description='Get the TFE Workspace Id when given the Workspace Name.')
parser.add_argument('-tfeToken',
                    default=os.environ.get('TFETOKEN'),
                    help='API Token used to authenticate to TFE.')
parser.add_argument('-tfeHostName',
                    default=os.environ.get('TFEHOSTNAME'),
                    help="TFE Hostname (i.e. terraform.company.com")
parser.add_argument('-tfeOrganizationName',
                    default=os.environ.get('TFEORGANIZATIONNAME'),
                    help="TFE Organization Name (i.e. hashicorp-dev")
parser.add_argument('-tfeWorkspaceName',
                    default=os.environ.get('TFEWORKSPACENAME'),
                    help="TFE Workspace Name (i.e. app1-eastus-dev")

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
tfeHostName = args.tfeHostName
tfeOrganizationName = args.tfeOrganizationName
tfeWorkspaceName = args.tfeWorkspaceName

print(f'tfeToken:{tfeToken}')
print(f'tfeHostName:{tfeHostName}')
print(f'tfeOrganizationName:{tfeOrganizationName}')
print(f'tfeWorkspaceName:{tfeWorkspaceName}')

resp = requests.get(f'https://{tfeHostName}/api/v2/organizations/{tfeOrganizationName}/workspaces/{tfeWorkspaceName}',
                    headers={'Authorization': f'Bearer {tfeToken}',
                             'Content-Type': 'application/vnd.api+json'},
                    )

f = open("getWorkspaceId.json", "w")
f.write(resp.text)
f.close()
print(
    f'##vso[artifact.upload containerfolder=apicalls;artifactname=getWorkspaceId.json;]{os.getcwd()}/getWorkspaceId.json')

tfeWorkspaceId = resp.json()['data']['id']
print(f'##vso[task.setvariable variable=tfeWorkspaceId;]{tfeWorkspaceId}')
