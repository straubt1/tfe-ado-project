#!/usr/bin/python

import argparse
import json
import os
import tarfile

import requests

# Required, these can be set via arguments or environment variables
parser = argparse.ArgumentParser(
    description='Perform a TFE Run Plan.')
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
parser.add_argument('-terraformWorkingDirectory',
                    default=os.environ.get('TERRAFORMWORKINGDIRECTORY'),
                    help='The path of the Terraform code based on current working directory.')
# Optional
parser.add_argument('-tfeArchiveFileName',
                    default='terraform.tar.gz',
                    help='The file name to create as the archive file.')
parser.add_argument('-tfeSpeculativePlan',
                    default='False',
                    help="When True, trigger a speculative plan that can not be applied.")

# Parse Args
try:
    settings = parser.parse_args()
    settings_as_dict = vars(settings)
    for k in settings_as_dict:
        if settings_as_dict[k] is None:
            print(f'##[error]Missing argument: {k}')
    if None in settings_as_dict.values():
        raise Exception('Missing required arguments')
except Exception:
    parser.print_help()
    raise

# Create archive
currentDirectory = os.getcwd()
archiveFullPath = os.path.join(currentDirectory, settings.tfeArchiveFileName)

# Change working directory to make the tarfile logic easier
os.chdir(settings.terraformWorkingDirectory)

print(f'Generating the tar.gz file')
tar = tarfile.open(archiveFullPath, "w:gz")
for root, dirs, files in os.walk('./', topdown=True):
    # skip any potential temp directories
    dirs[:] = [d for d in dirs if d not in ['.git', '.terraform']]

    for file in files:
        # print(f'##[debug]Archiving File: {os.path.join(root, file)}')
        tar.add(os.path.join(root, file))
tar.close()

# Revert working directory back
os.chdir(currentDirectory)

# Get Workspace ID
resp = requests.get(
    f'https://{settings.tfeHostName}/api/v2/organizations/{settings.tfeOrganizationName}/workspaces/{settings.tfeWorkspaceName}',
    headers={'Authorization': f'Bearer {settings.tfeToken}',
             'Content-Type': 'application/vnd.api+json'},
)
vars(settings)['tfeWorkspaceId'] = resp.json()['data']['id']
print(f'TFE Workspace Id: {settings.tfeWorkspaceId}')

# Create Config Version
tfConfig = {
    "data":
        {
            "type": "configuration-versions",
            "attributes": {
                "auto-queue-runs": False,
                "speculative": settings.tfeSpeculativePlan
            }
        }
}
resp = requests.post(
    f'https://{settings.tfeHostName}/api/v2/workspaces/{settings.tfeWorkspaceId}/configuration-versions',
    headers={'Authorization': f'Bearer {settings.tfeToken}',
             'Content-Type': 'application/vnd.api+json'},
    data=json.dumps(tfConfig)
)

vars(settings)['tfeConfigurationVersionId'] = resp.json()['data']['id']
vars(settings)['tfeConfigurationVersionUploadUrl'] = resp.json()['data']['attributes']['upload-url']

# Upload tar to configuration version
resp = requests.put(settings.tfeConfigurationVersionUploadUrl,
                    headers={'Authorization': f'Bearer {settings.tfeToken}',
                             'Content-Type': 'application/octet-stream'},
                    data=open(settings.tfeArchiveFileName, 'rb').read()
                    )

# Create Destroy Plan
tfConfig = {
    "data": {
        "type": "runs",
        "attributes": {
            "is-destroy": True,
            "message": "Triggered Destroy"
        },
        "relationships": {
            "workspace": {
                "data": {
                    "type": "workspaces",
                    "id": settings.tfeWorkspaceId
                }
            },
            "configuration-version": {
                "data": {
                    "type": "configuration-versions",
                    "id": settings.tfeConfigurationVersionId
                }
            }
        }
    }
}

resp = requests.post(f'https://{settings.tfeHostName}/api/v2/runs',
                     headers={'Authorization': f'Bearer {settings.tfeToken}',
                              'Content-Type': 'application/vnd.api+json'},
                     data=json.dumps(tfConfig)
                     )
vars(settings)['tfeRunId'] = resp.json()['data']['id']

print(f'Newly Created Configuration Version Id: {settings.tfeConfigurationVersionId}')
print(f'Newly Created Run Id: {settings.tfeRunId}')
print(
    f'Configuration Version Id sent to trigger the Run: {tfConfig["data"]["relationships"]["configuration-version"]["data"]["id"]}')

print(
    f'Configuration Version Id from the create Run Response: {resp.json()["data"]["relationships"]["configuration-version"]["data"]["id"]}')

# Read Run info from TFE
resp = requests.get(f'https://{settings.tfeHostName}/api/v2/runs/{settings.tfeRunId}',
                    headers={'Authorization': f'Bearer {settings.tfeToken}',
                             'Content-Type': 'application/vnd.api+json'},
                    )

print(
    f'Configuration Version Id from the show Run API Response: {resp.json()["data"]["relationships"]["configuration-version"]["data"]["id"]}')
