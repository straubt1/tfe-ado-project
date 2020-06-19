#!/usr/bin/python

import sys
import os
import tarfile
import argparse

# Parse arguments, these can be set via parameters or environment variables
parser = argparse.ArgumentParser(
    description='Get the TFE Workspace Id when given the Workspace Name.')
parser.add_argument('-tfeArchiveFileName',
                    default='terraform.tar.gz',
                    help='The file name to create as the archive file.')
parser.add_argument('-terraformWorkingDirectory',
                    default='',
                    help='The path of the Terraform code.')

# Throw exception if any arguments were not set
try:
    args = parser.parse_args()
    if None in vars(args).values():
        raise Exception('Missing required arguments')
except Exception:
    parser.print_help()
    raise

# Assign local variables
tfeArchiveFileName = args.tfeArchiveFileName
terraformWorkingDirectory = args.terraformWorkingDirectory

print(f'tfeArchiveFileName:{tfeArchiveFileName}')
print(f'terraformWorkingDirectory:{terraformWorkingDirectory}')

currentDirectory = os.getcwd()
archiveFullPath = os.path.join(currentDirectory, tfeArchiveFileName)

print(f'{currentDirectory}')
# cd if needed
os.chdir(terraformWorkingDirectory)

tar = tarfile.open(archiveFullPath, "w:gz")
for root, dirs, files in os.walk('./', topdown=True):
    # skip any potential temp directories
    dirs[:] = [d for d in dirs if d not in ['.git', '.terraform']]

    for file in files:
        print(os.path.join(root, file))
        tar.add(os.path.join(root, file))
tar.close()

print(
    f'##vso[artifact.upload containerfolder=archive;artifactname=uploadedresult;]{archiveFullPath}')
print(
    f'##vso[task.setvariable variable=tfeArchiveFileName;]{tfeArchiveFileName}')
