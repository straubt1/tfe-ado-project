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
parser.add_argument('-tfeRunId',
                    default=os.environ.get('TFERUNID'),
                    help="TFE Run Id")

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
tfeRunId = args.tfeRunId

adoBuildLink = f'{os.environ["SYSTEM_TEAMFOUNDATIONSERVERURI"]}/{os.environ["SYSTEM_TEAMPROJECT"]}/_build/results?buildId={os.environ["BUILD_BUILDID"]}'

print(f'tfeToken:{tfeToken}')
print(f'tfeHostname:{tfeHostname}')
print(f'tfeRunId:{tfeRunId}')

tfConfig = {
    "comment": f'Auto Approved from Azure DevOps (Build: {os.environ["BUILD_BUILDID"]})'
}

# TODO: If there is a policy override required, must make a call to override.
# POST f'https://{tfeHostname}/api/v2/policy-checks/{policy_check_id}/actions/override'

resp = requests.post(f'https://{tfeHostname}/api/v2/runs/{tfeRunId}/actions/apply',
                     headers={'Authorization': f'Bearer {tfeToken}',
                              'Content-Type': 'application/vnd.api+json'},
                     data=json.dumps(tfConfig)
                     )

f = open("postApplyRun.json", "w")
f.write(resp.text)
f.close()
print(
    f'##vso[artifact.upload containerfolder=apicalls;artifactname=postApplyRun.json;]{os.getcwd()}/postApplyRun.json')

print(resp.text)

# TODO: wait for apply to complete
# https://www.terraform.io/docs/cloud/api/applies.html
