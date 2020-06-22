#!/usr/bin/python

import argparse
import json
import os
import re
import tarfile
import time

import requests

# Required, these can be set via arguments or environment variables
parser = argparse.ArgumentParser(description='Perform a TFE Run Plan.')
parser.add_argument('-tfeToken',
                    default=os.environ.get('TFETOKEN'),
                    help='API Token used to authenticate to TFE.')
parser.add_argument('-tfeHostName',
                    default=os.environ.get('TFEHOSTNAME'),
                    help="TFE Hostname (i.e. terraform.company.com)")
parser.add_argument('-tfeOrganizationName',
                    default=os.environ.get('TFEORGANIZATIONNAME'),
                    help="TFE Organization Name (i.e. hashicorp-dev)")
parser.add_argument('-tfeWorkspaceName',
                    default=os.environ.get('TFEWORKSPACENAME'),
                    help="TFE Workspace Name (i.e. app1-eastus-dev)")
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
parser.add_argument('-tfeDestroyPlan',
                    default='False',
                    help="When True, trigger a destroy plan.")


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
    # Print arguments for debugging
    print(f'##[debug]tfeArchiveFileName:{args.tfeArchiveFileName}')
    print(f'##[debug]terraformWorkingDirectory:{args.terraformWorkingDirectory}')
    print(f'##[debug]tfeToken:{args.tfeToken}')
    print(f'##[debug]tfeHostName:{args.tfeHostName}')
    print(f'##[debug]tfeOrganizationName:{args.tfeOrganizationName}')
    print(f'##[debug]tfeWorkspaceName:{args.tfeWorkspaceName}')

    # Update in case ADO boolean matching causes issues
    args.tfeSpeculativePlan = json.loads(args.tfeSpeculativePlan.lower())
    print(f'##[debug]tfeSpeculativePlan:{args.tfeSpeculativePlan}')
    print(f'##[debug]tfeDestroyPlan:{args.tfeDestroyPlan}')

    # Build specific values
    args.adoBuildLink = f'{os.environ["SYSTEM_TEAMFOUNDATIONSERVERURI"]}{os.environ["SYSTEM_TEAMPROJECT"]}/_build/results?buildId={os.environ["BUILD_BUILDID"]}'
    args.sleepInSeconds = 5

    print(f'##[endgroup]')
    print()
    return args


def archive_files(settings):
    """
    Based on the code directory, archive all the files into a tar.gz
    :param archiveFileName: Name of the tar.gz to create
    :param codeDirectory: Directory where the code lives
    :return: None
    """
    print(f'##[group]Archive Files')
    print(f'##[debug]archiveFileName: {settings.tfeArchiveFileName}')
    print(f'##[debug]codeDirectory: {settings.terraformWorkingDirectory}')
    currentDirectory = os.getcwd()
    archiveFullPath = os.path.join(
        currentDirectory, settings.tfeArchiveFileName)

    # Change working directory to make the tarfile logic easier
    os.chdir(settings.terraformWorkingDirectory)

    print(f'##[command]Generating the tar.gz file')
    tar = tarfile.open(archiveFullPath, "w:gz")
    for root, dirs, files in os.walk('./', topdown=True):
        # skip any potential temp directories
        dirs[:] = [d for d in dirs if d not in ['.git', '.terraform']]

        for file in files:
            print(f'##[debug]Archiving File: {os.path.join(root, file)}')
            tar.add(os.path.join(root, file))
    tar.close()

    print(f'##vso[artifact.upload containerfolder=archive;artifactname=uploadedresult;]{archiveFullPath}')
    print(f'##vso[task.setvariable variable=tfeArchiveFileName;]{settings.tfeArchiveFileName}')

    # Revert working directory back
    os.chdir(currentDirectory)
    print(f'##[endgroup]')
    print()


def get_workspace_id(settings):
    """
    Get TFE Workspace Id from Workspace Name
    :param settings: All settings
    :return:
    """
    print(f'##[group]Get TFE Workspace Id')

    print(f'##[command]Getting workspace id from workspace name')
    resp = requests.get(
        f'https://{settings.tfeHostName}/api/v2/organizations/{settings.tfeOrganizationName}/workspaces/{settings.tfeWorkspaceName}',
        headers={'Authorization': f'Bearer {settings.tfeToken}',
                 'Content-Type': 'application/vnd.api+json'},
    )
    print(f'##[debug]getWorkspaceIdResponse: {resp.text}')

    id = resp.json()['data']['id']
    vars(settings)['tfeWorkspaceId'] = id  # set this on the setting Namespace for downstream consumption
    print(f'##[command]Workspace Id Found: {id}')
    print(f'##[endgroup]')
    print()

    # return id


def create_configuration_version(settings):
    print(f'##[group]Create Configuration Version')

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
    print(f'##[debug]tfConfig: {tfConfig}')
    print(f'##[debug]Creating Configuration Version')
    resp = requests.post(
        f'https://{settings.tfeHostName}/api/v2/workspaces/{settings.tfeWorkspaceId}/configuration-versions',
        headers={'Authorization': f'Bearer {settings.tfeToken}',
                 'Content-Type': 'application/vnd.api+json'},
        data=json.dumps(tfConfig)
    )
    print(f'##[debug]postConfigurationVersionRequest: {resp.request.body}')
    print(f'##[debug]postConfigurationVersionResponse: {resp.text}')

    vars(settings)['tfeConfigurationVersionId'] = resp.json()['data']['id']
    vars(settings)['tfeConfigurationVersionUploadUrl'] = resp.json()['data']['attributes']['upload-url']
    print(f'##[debug]tfeConfigurationVersionId: {settings.tfeConfigurationVersionId}')
    print(f'##[debug]tfeConfigurationVersionUploadUrl: {settings.tfeConfigurationVersionUploadUrl}')

    print(f'##[debug]Uploading Archive to Configuration Version')
    resp = requests.put(settings.tfeConfigurationVersionUploadUrl,
                        headers={'Authorization': f'Bearer {settings.tfeToken}',
                                 'Content-Type': 'application/octet-stream'},
                        data=open(settings.tfeArchiveFileName, 'rb').read()
                        )
    print(f'##[debug]Upload Result: {resp}')
    print(f'##[endgroup]')
    print()


def create_run_plan(settings):
    print(f'##[group]Create Run Plan')

    tfConfig = {
        "data": {
            "type": "runs",
            "attributes": {
                "is-destroy": settings.tfeDestroyPlan,
                "message": "ADO Triggered Build"
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

    print(f'##[debug]tfConfig: {tfConfig}')
    print(f'##[command]Creating Run')
    resp = requests.post(f'https://{settings.tfeHostName}/api/v2/runs',
                         headers={'Authorization': f'Bearer {settings.tfeToken}',
                                  'Content-Type': 'application/vnd.api+json'},
                         data=json.dumps(tfConfig)
                         )
    print(f'##[debug]postCreateRunRequest: {resp.request.body}')
    print(f'##[debug]postCreateRunResponse: {resp.text}')

    vars(settings)['tfeRunId'] = resp.json()['data']['id']
    vars(settings)['tfePlanId'] = resp.json()['data']['relationships']['plan']['data']['id']
    vars(settings)['tfeRunUrl'] = f'https://{settings.tfeHostName}/app/{settings.tfeOrganizationName}/{settings.tfeWorkspaceName}/runs/{settings.tfeRunId}'
    print(f'##[debug]tfeRunId: {settings.tfeRunId}')
    print(f'##[debug]tfePlanId: {settings.tfePlanId}')
    print(f'##vso[task.setvariable variable=tfeRunId;]{settings.tfeRunId}')
    print(f'##[command]TFE Run Link: {settings.tfeRunUrl}')

    print(f'##[endgroup]')
    print()


def create_run_comment(settings):
    print(f'##[group]Create Run Comment')

    tfConfig = {
        "data": {
            "attributes": {
                "body": f'ADO Build Link:<br />  {settings.adoBuildLink}'
            },
            "relationships": {
                "run": {
                    "data": {
                        "type": "runs",
                        "id": settings.tfeRunId
                    }
                }
            },
            "type": "comments"
        }
    }

    print(f'##[debug]tfConfig: {tfConfig}')
    print(f'##[command]Creating Run Comment')
    resp = requests.post(f'https://{settings.tfeHostName}/api/v2/runs/{settings.tfeRunId}/comments',
                         headers={'Authorization': f'Bearer {settings.tfeToken}',
                                  'Content-Type': 'application/vnd.api+json'},
                         data=json.dumps(tfConfig)
                         )
    print(f'##[debug]postCreateRunCommentRequest: {resp.request.body}')
    print(f'##[debug]postCreateRunCommentResponse: {resp.text}')
    print(f'##[debug]Comment Result: {resp}')

    print(f'##[endgroup]')
    print()


def wait_for_plan_complete(settings):
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
    # if relationships.cost-estimate is not present, no cost estimation
    vars(settings)['tfeIsCostEstimate'] = 'cost-estimate' in resp.json()['data']['relationships']
    if settings.tfeIsCostEstimate:
        vars(settings)['tfeCostEstimateId'] = resp.json()['data']['relationships']['cost-estimate']['data']['id']
    # if relationships.policy-checks.data[] is empty, no policy checks
    vars(settings)['tfeIsPolicyCheck'] = len(resp.json()['data']['relationships']['policy-checks']['data']) > 0
    if settings.tfeIsPolicyCheck:
        # TODO: Ensure there is only 1 sub 'data' policy check?
        vars(settings)['tfePolicyCheckId'] = resp.json()['data']['relationships']['policy-checks']['data'][0]['id']

    print(f'##[command]Current Run Cost Estimate will occur: {settings.tfeIsCostEstimate}')
    print(f'##[command]Current Run Policy Check will occur: {settings.tfeIsPolicyCheck}')

    # Loop until plan, cost estimate, and policy checks are all done (if applicable)
    planDone = checkStatus(currentRunStatus, settings.tfeIsPolicyCheck, settings.tfeIsCostEstimate)
    while planDone is False:
        time.sleep(settings.sleepInSeconds)
        resp = requests.get(f'https://{settings.tfeHostName}/api/v2/runs/{settings.tfeRunId}',
                            headers={'Authorization': f'Bearer {settings.tfeToken}',
                                     'Content-Type': 'application/vnd.api+json'},
                            )

        currentRunStatus = resp.json()['data']['attributes']['status']
        print(f'##[debug]Current Run Status: {currentRunStatus}')
        planDone = checkStatus(currentRunStatus, settings.tfeIsPolicyCheck, settings.tfeIsCostEstimate)
    print(f'##[command]Plan has completed, status: {currentRunStatus}')
    # print(f'##[debug]aaa')
    # print(f'##[debug]aaa')

    print(f'##[endgroup]')
    print()


def get_run_plan_logs(settings):
    print(f'##[group]Get Run Plan Logs')

    print(f'##[command]Getting Run Plan Logs Url')
    resp = requests.get(f'https://{settings.tfeHostName}/api/v2/plans/{settings.tfePlanId}',
                        headers={'Authorization': f'Bearer {settings.tfeToken}',
                                 'Content-Type': 'application/vnd.api+json'},
                        )
    print(f'##[debug]getPlanLogsUrlResponse: {resp.text}')

    vars(settings)['planLogsUrl'] = resp.json()['data']['attributes']['log-read-url']

    print(f'##[command]Getting Run Plan Logs')
    resp = requests.get(settings.planLogsUrl,
                        headers={'Authorization': f'Bearer {settings.tfeToken}',
                                 'Content-Type': 'application/vnd.api+json'},
                        )

    vars(settings)['planLogs'] = resp.text
    printLogs(settings.planLogs)

    print(f'##[endgroup]')
    print()


def get_run_cost_estimate_logs(settings):
    if not settings.tfeIsCostEstimate:
        return

    print(f'##[group]Get Run Cost Estimate Logs')

    print(f'##[command]Getting Run Cost Estimate Logs')
    resp = requests.get(f'https://{settings.tfeHostName}/api/v2/cost-estimates/{settings.tfeCostEstimateId}',
                        headers={'Authorization': f'Bearer {settings.tfeToken}',
                                 'Content-Type': 'application/vnd.api+json'},
                        )

    vars(settings)['tfeCostEstimateLogs'] = f"""\
resources-count:            {resp.json()['data']['attributes']['resources-count']}
matched-resources-count:    {resp.json()['data']['attributes']['matched-resources-count']}
unmatched-resources-count:  {resp.json()['data']['attributes']['unmatched-resources-count']}
prior-monthly-cost:         ${resp.json()['data']['attributes']['prior-monthly-cost']}/month
proposed-monthly-cost:      ${resp.json()['data']['attributes']['proposed-monthly-cost']}/month
delta-monthly-cost:         ${resp.json()['data']['attributes']['delta-monthly-cost']}/month
"""

    printLogs(settings.tfeCostEstimateLogs)
    print(f'##[endgroup]')
    print()


def get_run_policy_check_logs(settings):
    if not settings.tfeIsPolicyCheck:
        return

    print(f'##[group]Get Run Policy Check Logs')

    print(f'##[command]Getting Run Policy Check Logs Url')
    resp = requests.get(f'https://{settings.tfeHostName}/api/v2/runs/{settings.tfeRunId}/policy-checks',
                        headers={'Authorization': f'Bearer {settings.tfeToken}',
                                 'Content-Type': 'application/vnd.api+json'},
                        )
    print(f'##[debug]getPolicyCheckLogsUrlResponse: {resp.text}')

    vars(settings)['policyCheckLogsUrl'] = resp.json()['data'][0]['links']['output']

    print(f'##[command]Getting Run Policy Check Logs')
    resp = requests.get(f'https://{settings.tfeHostName}{settings.policyChecksLogsUrl}',
                        headers={'Authorization': f'Bearer {settings.tfeToken}',
                                 'Content-Type': 'application/vnd.api+json'},
                        )

    vars(settings)['policyCheckLogs'] = resp.text

    printLogs(settings.policyCheckLogs)
    print(f'##[endgroup]')
    print()


def create_summary(settings):
    print(f'##[group]Creating Summary Markdown')

    summary = []
    print(f'##[command]Generating Details')
    summary.append('## Details\n\n')
    if settings.tfeSpeculativePlan:
        summary.append(f'_Speculative Plan_\n\n')
    summary.append(f'Terraform Enterprise Run: <{settings.tfeRunUrl}>\n')
    summary.append(f'Azure DevOps Build: <{settings.adoBuildLink}>\n')
    summary.append('\n')

    if settings.tfeIsCostEstimate:
        print(f'##[command]Generating Cost Estimate logs')
        summary.append('## Cost Estimate\n\n')
        summary.append(settings.tfeCostEstimateLogs)
        summary.append('\n')

    print(f'##[command]Generating Plan logs')
    # remove color encodings, could pass -no-color flag but that will make the TFE output ugly...
    tfePlanClean = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub('', settings.planLogs)
    summary.append('## Plan\n\n')
    summary.append('```\n')
    summary.append(tfePlanClean)
    summary.append('\n```\n')

    if settings.tfeIsPolicyCheck:
        print(f'##[command]Generating Policy Check logs')
        summary.append('## Policy Check\n\n')
        summary.append('```\n')
        summary.append(settings.policyCheckLogs)
        summary.append('\n```\n')

    f = open("runsummary.md", "w")
    f.writelines(summary)
    f.close()
    print(f'##vso[task.uploadsummary]{os.getcwd()}/runsummary.md')
    print(f'##[endgroup]')
    print()


# Utility functions
def checkStatus(status, tfeIsPolicyCheck, tfeIsCostEstimate):
    """
    Check the current status to determine if 1. the run is still running, 2. the run has stopped, 3. there is a final state.
    :param status:
    :param tfeIsPolicyCheck:
    :param tfeIsCostEstimate:
    :return:
    """
    # Return True if done
    if status in ['queued', 'pending', 'plan_queued', 'planning']:
        # Plan is not complete
        return False
    if status in ['planned']:
        if not tfeIsPolicyCheck and not tfeIsCostEstimate:
            # If there are not policy checks or cost estimate, we are done
            return True
        else:
            return False
    if status in ['cost_estimating']:
        # Coste estimate is not complete
        return False
    if status in ['cost_estimated']:
        if not tfeIsPolicyCheck:
            # If there are no policy checks, we are done
            return True
        else:
            return False
    if status in ['policy_checking']:
        return False
    if status in ['policy_override']:
        # A sentinel policy has soft failed, and can be overridden, will it stay here or then move to checked?
        return False
    if status in ['policy_soft_failed']:
        return True
    if status in ['policy_checked']:
        # Regardless of how we get here, we are done
        return True

    if status in ['apply_queued', 'applying', 'confirmed']:
        return False
    if status in ['applied', 'planned_and_finished', 'discarded', 'errored', 'canceled', 'force_canceled']:
        # Final states, we are done
        return True


def printLogs(logs):
    print()
    print('#' * 80)
    print(logs)
    print('#' * 80)


settings = parse_args(parser)

archive_files(settings)

get_workspace_id(settings)

create_configuration_version(settings)

create_run_plan(settings)

create_run_comment(settings)

wait_for_plan_complete(settings)

get_run_plan_logs(settings)

get_run_cost_estimate_logs(settings)

get_run_policy_check_logs(settings)

create_summary(settings)
