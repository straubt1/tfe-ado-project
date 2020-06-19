#!/usr/bin/python

import sys
import os
import requests
import json
import argparse
import tarfile

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

adoBuildLink = f'{os.environ["SYSTEM_TEAMFOUNDATIONSERVERURI"]}/{os.environ["SYSTEM_TEAMPROJECT"]}/_build/results?buildId={os.environ["BUILD_BUILDID"]}'

print(f'tfeToken:{tfeToken}')
print(f'tfeHostname:{tfeHostname}')
print(f'tfeOrganizationName:{tfeOrganizationName}')
print(f'tfeWorkspaceId:{tfeWorkspaceId}')

tfConfig = {
    "data": {
        "type": "runs",
        "attributes": {
                "is-destroy": True,
                "message": "ADO Triggered Destroy"
        },
        "relationships": {
            "workspace": {
                "data": {
                    "type": "workspaces",
                    "id": tfeWorkspaceId
                }
            }
        }
    }
}

resp = requests.post(f'https://{tfeHostname}/api/v2/runs',
                     headers={'Authorization': f'Bearer {tfeToken}',
                              'Content-Type': 'application/vnd.api+json'},
                     data=json.dumps(tfConfig)
                     )

f = open("postCreateDestroy.json", "w")
f.write(resp.text)
f.close()
print(
    f'##vso[artifact.upload containerfolder=apicalls;artifactname=postCreateDestroy.json;]{os.getcwd()}/postCreateDestroy.json')

tfeRunId = resp.json()['data']['id']
tfePlanId = resp.json()['data']['relationships']['plan']['data']['id']

print(f'##vso[task.setvariable variable=tfeRunId;]{tfeRunId}')
print(f'##vso[task.setvariable variable=tfePlanId;]{tfePlanId}')

print(f'tfeRunId:{tfeRunId}')
print(f'tfePlanId:{tfePlanId}')

tfConfig = {
    "data": {
        "attributes": {
            "body": f'ADO Build Link:<br />  {adoBuildLink}'
        },
        "relationships": {
            "run": {
                "data": {
                    "type": "runs",
                    "id": tfeRunId
                }
            }
        },
        "type": "comments"
    }
}

# Post comment
resp = requests.post(f'https://{tfeHostname}/api/v2/runs/{tfeRunId}/comments',
                     headers={'Authorization': f'Bearer {tfeToken}',
                              'Content-Type': 'application/vnd.api+json'},
                     data=json.dumps(tfConfig)
                     )
