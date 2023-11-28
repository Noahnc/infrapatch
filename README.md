# infrapatch
CLI Tool and GitHub Action to patch your Terraform Code

Infrapatch is a CLI tool and GitHub Action to patch the Provider and Module dependencies in your Terraform Code.
The CLI works by scanning your .tf files for versioned providers and modules and then updating the version to the latest available version.

## CLI
The follwoing chapter describes the CLI usage.

## Supported Platforms

Currently, the CLI supports only MacOS and Linux.

### Installation

Before installing the CLI, make sure you have Python 3.11 or higher installed.
The InfraPatch CLI can be installed via pip:

```bash
git clone "https://github.com/Noahnc/infrapatch.git"
cd infrapatch
pip install .
```

After the installation, InfraPatch can be run with the following command:

```bash
infrapatch --help
```
![infrapatch_help.png](asset%2Finfrapatch_help.png)

### Usage

Currently, InfraPatch supports two main commands: `report` and `update`.
The `report` command will scan your Terraform code and report the current and newest version of all providers and modules.

```bash
infrapatch report
```
![infrapatch_report.gif](asset%2Finfrapatch_report.gif)

The `update` command will scan your Terraform code and ask you for confirmation to update the listed modules and providers to the newest version.

```bash
infrapatch update
```
![infrapatch_update.gif](asset%2Finfrapatch_update.gif)

### Authentication

If you use private registries for your providers or modules, you can specify credentials for the CLI to use.
There are two ways to do so:

#### .terraformrc file:
InfraPatch will automatically look for a `.terraformrc` file in the users home folder and use the credentials specified there.
For more information about the `.terraformrc` file, see the [Terraform documentation](https://www.terraform.io/docs/commands/cli-config.html#credentials-1).

#### infrapatch_credentials.json file:

You can also specify the credentials in a `infrapatch_credentials.json` file in the current working directory.
The file must have the following structure:
```json
{
"spacelift.io": "<your_api_token>",
"<second_registry>": "<your_api_token>"
}
```

You can also specify the path to the credentials file with the `--credentials-file-path` flag.

```bash
infrapatch --credentials-file-path "path/to/credentials/file" update
```

### GitHub Action

This repository also contains a GitHub Action.
The Action can for example be run on a schedule to automatically update your terraform code and open a PR with the changes.

The following example workflow runs once a day:
    
```yaml
name: "InfraPatch"

permissions:
  contents: write
  pull-requests: write

on:
  schedule:
    - cron: '0 23 * * *'
  workflow_dispatch:

jobs:
  infrapatch:
    name: "Check Terraform Code for Updates"
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Run in update mode
        uses: Noahnc/infrapatch@main
        with:
          report_only: false

```

#### Providers

InfraPatch supports individual providers to detect and patch versions. Currently, the following providers are available:
| Name                | Description                            |
| ------------------- | -------------------------------------- |
| terraform_modules   | Provider to patch Terraform Modules.   |
| terraform_providers | Provider to patch Terraform Providers. |

Per default, all providers are enabled. You can only enable specific providers by specifying the provider names as comma separated list in the input `enabled_providers`:
  
  ```yaml
    - name: Run in update mode
      uses: Noahnc/infrapatch@main
      with:
        enabled_providers: terraform_modules,terraform_providers
  ```

#### Report only Mode

By default, the Action will create a Branch with all the changes and opens a PR to Branch for which the Action was triggered.
When setting the input `report_only` to `true`, the Action will only report available updates in the Action output.

#### Authentication

If you use private registries in your Terraform project, you can specify credentials for the Action with the Input `registry_secrets`:

```yaml
  - name: Run in update mode
    uses: Noahnc/infrapatch@main
    with:
      registry_secrets: |
        spacelift.io=${{ secrets.SPACELIFT_API_TOKEN }}
        <second_registry>=<registry_token>
```

Each secret must be specified in a new line with the following format: `<registry_name>=<registry_token>`

#### Working Directory

By default, the Action will run in the root directory of the repository. If you want to only scan a subdirectory, you can specify a subdirectory with the `working_directory_relative` input:

```yaml
  - name: Run in update mode
    uses: Noahnc/infrapatch@main
    with:
      working_directory: "path/to/terraform/code"
```
