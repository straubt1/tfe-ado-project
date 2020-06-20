#!/usr/bin/python

import sys
import os
import requests
import json
import time
import re
import argparse

sleepInSeconds = 5


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
parser.add_argument('-tfeWorkspaceId',
                    default=os.environ.get('TFEWORKSPACEID'),
                    help="TFE Workspace Id (i.e. ws-zzzzzzzzzz")
parser.add_argument('-tfeRunId',
                    default=os.environ.get('TFERUNID'),
                    help="TFE Run Id.")
parser.add_argument('-tfePlanId',
                    default=os.environ.get('TFEPLANID'),
                    help="TFE Plan Id.")

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
tfeWorkspaceId = args.tfeWorkspaceId
tfeRunId = args.tfeRunId
tfePlanId = args.tfePlanId

print(f'tfeToken:{tfeToken}')
print(f'tfeHostName:{tfeHostName}')
print(f'tfeOrganizationName:{tfeOrganizationName}')
print(f'tfeRunId:{tfeRunId}')
print(f'tfePlanId:{tfePlanId}')

# Get initial information about the Run and its starting status
resp = requests.get(f'https://{tfeHostName}/api/v2/runs/{tfeRunId}',
                    headers={'Authorization': f'Bearer {tfeToken}',
                             'Content-Type': 'application/vnd.api+json'},
                    )
# if relationships.cost-estimate is not present, no cost estimation
tfeIsCostEstimate = 'cost-estimate' in resp.json()['data']['relationships']
if tfeIsCostEstimate:
    tfeCostEstimateId = resp.json(
    )['data']['relationships']['cost-estimate']['data']['id']
# if relationships.policy-checks.data[] is empty, no policy checks
tfeIsPolicyCheck = len(
    resp.json()['data']['relationships']['policy-checks']['data'])
if tfeIsPolicyCheck:
    # TODO: Ensure there is only 1 sub 'data' policy check?
    tfePolicyCheckId = resp.json(
    )['data']['relationships']['policy-checks']['data'][0]['id']


def checkStatus(status):
    # Return True if done
    if status in ['queued', 'pending', 'plan_queued', 'planning']:
        # Plan is not complete
        return False
    if status is 'planned':
        if not tfeIsPolicyCheck and not tfeIsCostEstimate:
            # If there are not policy checks or cost estimate, we are done
            return True
        else:
            return False
    if status is 'cost_estimating':
        # Coste estimate is not complete
        return False
    if status is 'cost_estimated':
        if not tfeIsPolicyCheck:
            # If there are no policy checks, we are done
            return True
        else:
            return False
    if status is 'policy_checking':
        return False
    if status is 'policy_override':
        # A sentinel policy has soft failed, and can be overridden, will it stay here or then move to checked?
        return False
    if status is 'policy_soft_failed':
        return True
    if status is 'policy_checked':
        # Regardless of how we get here, we are done
        return True

    if status in ['apply_queued', 'applying', 'confirmed']:
        return False
    if status in ['applied', 'planned_and_finished', 'discarded', 'errored', 'canceled', 'force_canceled']:
        # Final states, we are done
        return True


def printLogs(message, logs):
    print()
    print(f'{message}:')
    print(logs)
    print('#'*80)


# Loop until plan, cost estimate, and policy checks are all done (if applicable)
planDone = False
while planDone is False:
    resp = requests.get(f'https://{tfeHostName}/api/v2/runs/{tfeRunId}',
                        headers={'Authorization': f'Bearer {tfeToken}',
                                 'Content-Type': 'application/vnd.api+json'},
                        )
    currentRunStatus = resp.json()['data']['attributes']['status']
    print(f'Current Run Status: {currentRunStatus}')
    planDone = checkStatus(currentRunStatus)
    time.sleep(sleepInSeconds)
print('Plan is done')

# Get Plan output
resp = requests.get(f'https://{tfeHostName}/api/v2/plans/{tfePlanId}',
                    headers={'Authorization': f'Bearer {tfeToken}',
                             'Content-Type': 'application/vnd.api+json'},
                    )
currentPlanStatus = resp.json()['data']['attributes']['status']
planLogsUrl = resp.json()['data']['attributes']['log-read-url']
print(f'Current Plan Status: {currentPlanStatus}')
print(f'Current planLogsUrl: {planLogsUrl}')

resp = requests.get(planLogsUrl,
                    headers={'Authorization': f'Bearer {tfeToken}',
                             'Content-Type': 'application/vnd.api+json'},
                    )
tfePlan = resp.text

# Print plan to output
printLogs('Plan Logs', tfePlan)

# # Get Cost Estimate output
if tfeIsCostEstimate:
    # Get Cost Estimate logs url
    resp = requests.get(f'https://{tfeHostName}/api/v2/cost-estimates/{tfeCostEstimateId}',
                        headers={'Authorization': f'Bearer {tfeToken}',
                                 'Content-Type': 'application/vnd.api+json'},
                        )
    tfeCostEstimate = f"""
resources-count:            {resp.json()['data']['attributes']['resources-count']}
matched-resources-count:    {resp.json()['data']['attributes']['matched-resources-count']}
unmatched-resources-count:  {resp.json()['data']['attributes']['unmatched-resources-count']}
prior-monthly-cost:         ${resp.json()['data']['attributes']['prior-monthly-cost']}/month
proposed-monthly-cost:      ${resp.json()['data']['attributes']['proposed-monthly-cost']}/month
delta-monthly-cost:         ${resp.json()['data']['attributes']['delta-monthly-cost']}/month
"""

    # Print policy checks to output
    printLogs('Cost Estimate Logs', tfeCostEstimate)


# Get Policy Check output
if tfeIsPolicyCheck:
    # Get Policy Check logs url
    resp = requests.get(f'https://{tfeHostName}/api/v2/runs/{tfeRunId}/policy-checks',
                        headers={'Authorization': f'Bearer {tfeToken}',
                                 'Content-Type': 'application/vnd.api+json'},
                        )
    policyChecksLogsUrl = resp.json()['data'][0]['links']['output']

    resp = requests.get(f'https://{tfeHostName}{policyChecksLogsUrl}',
                        headers={'Authorization': f'Bearer {tfeToken}',
                                 'Content-Type': 'application/vnd.api+json'},
                        )
    tfePolicyChecks = resp.text
    # Print policy checks to output
    printLogs('Policy Check Logs', tfePolicyChecks)


# Create a markdown file to save to as a run summary for easy visibility
f = open("runsummary.md", "w")
f.write('## Details\n')
f.write(
    f'Terraform Enterprise Run: <https://{tfeHostName}/app/{tfeOrganizationName}/workspaces/{tfeWorkspaceName}/runs/{tfeRunId}>\n')

if tfeIsCostEstimate:
    f.write('## Cost Estimate\n')
    f.write(tfeCostEstimate)
    # f.write('\n')

# remove color encodings, could pass -no-color flag but that will make the TFE output ugly...
tfePlanClean = re.compile(
    r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub('', tfePlan)
f.write('## Plan\n')
f.write('```\n')
f.write(tfePlanClean)
f.write('\n```\n')

if tfeIsPolicyCheck:
    f.write('## Policy Checks\n')
    f.write('```\n')
    f.write(tfePolicyChecks)
    f.write('\n```\n')

f.close()
print(f'##vso[task.uploadsummary]{os.getcwd()}/runsummary.md')
