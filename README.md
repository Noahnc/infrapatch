# infrapatch
CLI Tool and GitHub Action to patch your Terraform Code

Infrapatch is a CLI tool and GitHub Action to patch the Provider and Module dependencies in your Terraform Code.
The CLI works by scanning your .tf files for versioned providers and modules and then updating the version to the latest available version.

## CLI
The follwoing chapter describes the CLI usage.

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

### Usage

Currently, InfraPatch supports two main commands: `report` and `update`.
The `report` command will scan your Terraform code and report the current and newest version of all providers and modules.

```bash
infrapatch report
```

The `update` command will scan your Terraform code and ask you for confirmation to update the listed modules and providers to the newest version.

```bash
infrapatch update
```

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

This repository also contains a GitHub Action that can be used to automatically update your Terraform code.
The following example shows how to use the GitHub Action:


