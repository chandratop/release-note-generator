# release-note-generator

## Required artifacts
```
your-repository/
└── .github/
    ├── scripts/
    │   ├── utils/
    │   │   └── utils.py
    │   ├── pr_validator.py
    │   └── releaser.py
    ├── workflows/
    │   ├── initiate-release.yaml
    │   ├── pr-validator.yaml
    │   └── releaser.yaml
    ├── pull_request_template.md
    ├── release_template.md
    └── release.yml
```

## Required labels
| Label | Description |
| -------------- | -------------- |
| `help` | Request for help on slack |
| `ignore` | No need to include these pull requests in the GitHub release |
| `release` | Automated pull request for a new release |
| `type/breaking` | Pull Requests that mention breaking changes or deprecations |
| `type/bugfix` | Pull requests for addressing a fix for a bug |
| `type/chore` | Pull requests for addressing refactoring, documentation, etc |
| `type/enhancement` | Pull requests suggesting improvements to an existing feature |
| `type/feature` | Pull requests proposing the addition of a new feature |

### How to copy the artifacts to your repository?
1. Clone this repository
```shell
$ git clone https://github.com/chandratop/release-note-generator.git
```
2. Store the path to this repo in a variable
```shell
export RNG="/path/to/release-note-generator/.github/"
```
3. Navigate to your repository
```shell
$ cd /path/to/your-repository
```
4. Copy the necessary artifacts in your repository
```shell
rsync -av --ignore-existing $RNG .github/
```
5. Delete all existing labels from your repository from GitHub UI.
6. Clone the ones from `release-note-generator`
```shell
gh label clone chandratop/release-note-generator --repo owner/your-repository
```
