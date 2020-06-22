#!/usr/bin/python

import argparse
import json
import os
import re
import time

import requests

# Required, these can be set via arguments or environment variables
parser = argparse.ArgumentParser(description='Perform a TFE Run Plan.')
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
parser.add_argument('-tfeRunId',
                    default=os.environ.get('TFERUNID'),
                    help="TFE Run Id (i.e. run-xxxxxxxxx)")


def parse_args(parser):
    """
    Get all required arguments and valid them.
    Throw exception if any arguments were not set
    :param parser: ArgumentParser
    :return: Settings as NameSpace
    """
    print(f'##[group]Parse Arguments')
    print(f'##[command]Parsing arguments')
    try:
        args = parser.parse_args()
        args_as_dict = vars(args)
        for k in args_as_dict:
            if args_as_dict[k] is None:
                print(f'##[error]Missing argument: {k}')
        if None in args_as_dict.values():
            raise Exception('Missing required arguments')
    except Exception:
        parser.print_help()
        raise

    args.tfeRunId = 'run-BZCGfcuMi5u3rBDy'
    # Print arguments for debugging
    print(f'##[debug]tfeToken:{args.tfeToken}')
    print(f'##[debug]tfeHostName:{args.tfeHostName}')
    print(f'##[debug]tfeOrganizationName:{args.tfeOrganizationName}')
    print(f'##[debug]tfeWorkspaceName:{args.tfeWorkspaceName}')
    print(f'##[debug]tfeRunId:{args.tfeRunId}')

    # Build specific values
    args.sleepInSeconds = 5
    args.adoBuildId = os.environ["BUILD_BUILDID"]

    print(f'##[endgroup]')
    print()
    return args


def validate_run_id(settings):
    """
    Check if the given run id represents a run that can be applied
    Exception if not.
    :param settings:
    :return:
    """
    print(f'##[group]Validate Run Id')

    print(f'##[command]Validating Run Id: {settings.tfeRunId}')
    resp = requests.get(f'https://{settings.tfeHostName}/api/v2/runs/{settings.tfeRunId}',
                        headers={'Authorization': f'Bearer {settings.tfeToken}',
                                 'Content-Type': 'application/vnd.api+json'},
                        )
    print(f'##[debug]getRunInfoResponse: {resp.text}')

    if not resp.ok:
        exceptionMessage = f'TFE Run Id "{settings.tfeRunId}" is not able to be applied, message: {resp.text}'
        print(f'##[error]Invalid Run Id {exceptionMessage}')
        raise Exception(exceptionMessage)
    currentRunStatus = resp.json()['data']['attributes']['status']
    print(f'##[debug]Run status: {currentRunStatus}')

    if currentRunStatus not in ['planned', 'cost_estimated', 'policy_checked']:
        # Run can not be applied, error
        exceptionMessage = f'TFE Run Id "{settings.tfeRunId}" is not able to be applied, status: {currentRunStatus}'
        print(f'##[error]Invalid Run Id: {exceptionMessage}')
        raise Exception(exceptionMessage)

    # print(resp.text)
    print(f'##[endgroup]')
    print()


def create_run_apply(settings):
    print(f'##[group]Create Run Apply')

    tfConfig = {
        "comment": f'Auto Approved from Azure DevOps (Build: {settings.adoBuildId})'
    }

    # TODO: If there is a policy override required, must make a call to override.
    # POST f'https://{tfeHostName}/api/v2/policy-checks/{policy_check_id}/actions/override'

    print(f'##[command]Create Apply')
    resp = requests.post(f'https://{settings.tfeHostName}/api/v2/runs/{settings.tfeRunId}/actions/apply',
                         headers={'Authorization': f'Bearer {settings.tfeToken}',
                                  'Content-Type': 'application/vnd.api+json'},
                         data=json.dumps(tfConfig)
                         )
    print(f'##[debug]postCreateApplyRequest: {resp.request.body}')
    print(f'##[debug]postCreateApplyResponse: {resp.text}')

    if not resp.ok:
        exceptionMessage = f'Create Apply failed, message: {resp.text}'
        print(f'##[error]Create Apply {exceptionMessage}')
        raise Exception(exceptionMessage)

    print(f'##[command]Apply Created')
    print(f'##[endgroup]')
    print()


def wait_for_apply_complete(settings):
    """
    Poll the TFE Run until it's done
    :param settings:
    :return:
    """
    print(f'##[group]Monitoring Run Plan for completion')

    # Get initial information about the Run and its starting status
    resp = requests.get(f'https://{settings.tfeHostName}/api/v2/runs/{settings.tfeRunId}',
                        headers={'Authorization': f'Bearer {settings.tfeToken}',
                                 'Content-Type': 'application/vnd.api+json'},
                        )
    currentRunStatus = resp.json()['data']['attributes']['status']

    # Loop until plan, cost estimate, and policy checks are all done (if applicable)
    planDone = checkStatus(currentRunStatus)
    while planDone is False:
        time.sleep(settings.sleepInSeconds)
        resp = requests.get(f'https://{settings.tfeHostName}/api/v2/runs/{settings.tfeRunId}',
                            headers={'Authorization': f'Bearer {settings.tfeToken}',
                                     'Content-Type': 'application/vnd.api+json'},
                            )

        currentRunStatus = resp.json()['data']['attributes']['status']
        print(f'##[debug]Current Run Status: {currentRunStatus}')
        planDone = checkStatus(currentRunStatus)

    print(f'##[command]Plan has completed, status: {currentRunStatus}')
    print(f'##[endgroup]')
    print()


def get_run_apply_logs(settings):
    print(f'##[group]Get Run Apply Logs')

    print(f'##[command]Getting Run Apply Logs Url')
    resp = requests.get(f'https://{settings.tfeHostName}/api/v2/runs/{settings.tfeRunId}/apply',
                        headers={'Authorization': f'Bearer {settings.tfeToken}',
                                 'Content-Type': 'application/vnd.api+json'},
                        )
    print(f'##[debug]getApplyLogsUrlResponse: {resp.text}')

    vars(settings)['applyLogsUrl'] = resp.json()['data']['attributes']['log-read-url']

    print(f'##[command]Getting Run Apply Logs')
    resp = requests.get(settings.applyLogsUrl,
                        headers={'Authorization': f'Bearer {settings.tfeToken}',
                                 'Content-Type': 'application/vnd.api+json'},
                        )

    vars(settings)['applyLogs'] = resp.text

    print(f'##[command]Getting Run Apply Logs')
    printLogs(settings.applyLogs)
    print(f'##[endgroup]')
    print()


def create_summary(settings):
    print(f'##[group]Creating Summary Markdown')

    summary = []
    # print(f'##[command]Generating Details')
    # summary.append('## Details\n\n')
    # summary.append(f'Terraform Enterprise Run: <{settings.tfeRunUrl}>\n')
    # summary.append(f'Azure DevOps Build: <{settings.adoBuildLink}>\n')
    # summary.append('\n')

    print(f'##[command]Generating Plan logs')
    # remove color encodings, could pass -no-color flag but that will make the TFE output ugly...
    tfeApplyClean = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub('', settings.applyLogs)
    summary.append('## Apply\n\n')
    summary.append('```\n')
    summary.append(tfeApplyClean)
    summary.append('\n```\n')

    f = open("applysummary.md", "w")
    f.writelines(summary)
    f.close()
    print(f'##vso[task.uploadsummary]{os.getcwd()}/applysummary.md')
    print(f'##[endgroup]')
    print()


# Utility functions
def checkStatus(status):
    """
    Check the current status to determine if 1. the run is still running, 2. the run has stopped, 3. there is a final state.
    :param status:
    :param tfeIsPolicyCheck:
    :param tfeIsCostEstimate:
    :return:
    """
    # Return True if done
    if status in ['apply_queued', 'applying', 'confirmed']:
        return False
    if status in ['discarded', 'errored', 'canceled', 'force_canceled']:
        # Error or final states
        exceptionMessage = f'TFE Run Apply has stopped unexpectedly, status: {status}'
        print(f'##[error]Invalid Run Apply: {exceptionMessage}')
        raise Exception(exceptionMessage)
    if status in ['applied']:
        # Apply is done
        return True

    exceptionMessage = f'TFE Run Apply is in an unknown status: {status}'
    print(f'##[error]Unknown Run Apply: {exceptionMessage}')
    raise Exception(exceptionMessage)


def printLogs(logs):
    print()
    print('#' * 80)
    print(logs)
    print('#' * 80)


settings = parse_args(parser)

validate_run_id(settings)

create_run_apply(settings)

wait_for_apply_complete(settings)

get_run_apply_logs(settings)

create_summary(settings)
