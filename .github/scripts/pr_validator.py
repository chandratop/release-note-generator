"""
script: validator.py

This script validates a pull request's title, body, labels & branch name.
If all the validations pass then it will allow merging the pull request.
Otherwise it will block the merge.
"""

import re
import argparse
from typing import Any, List, Tuple, Literal
from utils.utils import run


class PR:
    """
    This class consists of modules that validates each component namely title,
    body & labels. The validations for title & body are dependent on labels.
    """

    def __init__(self, pr_number: str) -> None:

        self.pr_number = pr_number
        self.labels, self.title, self.body, self.branch = self._get_pr_variables()
        self.label_groups = self.validate_labels()

    def _get_pr_variables(self) -> Tuple[List[str], str, str, str]:

        return self._get_value(type="list", variable="labels"),\
            self._get_value(type="str", variable="title"),\
            self._get_value(type="str", variable="body"),\
            self._get_value(type="str", variable="headRefName")

    def _get_value(
        self,
        type: Literal["list","str"],
        variable: Literal[
            "labels",
            "title",
            "body",
            "headRefName"
        ]) -> Any:

        cmd = f'gh pr view "{self.pr_number}" --json {variable}'
        result = run(cmd)
        if result.fine:
            if type == "str":
                return eval(result.what)[f"{variable}"]
            elif type == "list":
                return [var["name"] for var in eval(result.what)[f"{variable}"]]
        else:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

    def validate_labels(self) -> dict[str, List[str]]:
        """
        This function validates the list of labels attadched to the pr and if
        it passes all the checks then it organizes the labels into a groups
        dict and returns it. The different groups are: `type`, `impact`,
        `global`, `help` & `size`.

        The checks performed are:
        - If the label has a sub-type using a `/` then it should exist
        - There can't be more than one `type`, `help` and `size` label
        - There needs to be one `type` and `size` label

        Any custom label which doesn't have a `/` will be grouped under `global`
        """

        groups = {"type": [], "impact": [], "global": [], "help": [], "size": []}
        for label in self.labels:
            if "/" in label:
                label_split = label.split("/")
                if label_split[0] in groups:
                    if label_split[0] in ["type", "help", "size"] and len(groups[label_split[0]]) != 0:
                        raise ValueError(f"Only one '{label_split[0]}' label is allowed on a pull request.")
                    groups[label_split[0]].append(label_split[1])
                else:
                    raise KeyError(f"Label group '{label_split[0]}' not found.")
            else:
                groups["global"].append(label)
        for group in ["type", "size"]:
            if len(groups[group]) != 1:
                raise ValueError(f"No '{group}' label found. One required.")
        return groups

    def validate_title(self) -> None:
        """
        The title should follow the pattern -
        ```
            type(Jira): Brief description
        ```
        The `type` field is required mandatorily but the `[Jira]` section is required
        only when the `type` is a `fix`, `feat` or `enh`.
        """

        mapping = {
            "bugfix": "fix",
            "chore": "chore",
            "dependency": "dep",
            "documentation": "doc",
            "enhancement": "enh",
            "feature": "feat",
            "performance": "perf",
            "security": "sec"
        }

        # form the regex pattern based on the `tyoe` labels
        if self.label_groups["type"][0] in ["chore", "documentation"]:
            pattern = r'(chore|doc): (?!.*:).*'
        else:
            # If there is an `impact` label then indicate it using an `!`
            if len(self.label_groups["impact"]) > 0:
                pattern = r'(fix|dep|enh|feat|perf|sec)\([^)][A-Z]+-\d+\)!: (?!.*:).*'
            else:
                pattern = r'(fix|dep|enh|feat|perf|sec)\([^)][A-Z]+-\d+\): (?!.*:).*'
        if not bool(re.match(pattern, self.title)):
            raise ValueError(f"Improper title: {self.title}\nregex: '{pattern}'")
        if not self.title.startswith(mapping[self.label_groups["type"][0]]):
            raise ValueError(f"Improper title, should start with {mapping[self.label_groups['type'][0]]}")

    def validate_body(self) -> None:
        """
        For pull requests which contain a list of Jira tickets, it should
        include a section to have `Related Jira Tickets`. Similarily, for pull
        requests which mention deprecations or breaking changes it should have
        sections with `Deprecations` and `Breaking Changes` respectively.
        """

        lines = self.body.split("\n")

        # Validate Jira section
        if self.label_groups["type"][0] not in ["chore", "documentation"]:
            try:
                jira_header = lines.index("### Related Jira Tickets\r")
                jira_footer = lines.index("---\r", jira_header)
                pattern = r'^- \[\w+-\d+\]\([\w\d\.:/-]+\)\r$'
                jira_count = 0
                for i in range(jira_header+1, jira_footer):
                    if "<!---" in lines[i]:
                        continue
                    if lines[i] == "\r":
                        continue
                    if not bool(re.match(pattern, lines[i])):
                        raise Exception(f"Improper Jira section in body, no bullet point.")
                    jira_count += 1
                if jira_count == 0:
                    raise Exception(f"No Jira listed in the Jira section.")
            except ValueError as ve:
                raise ValueError(f"Jira section not found in body.")
        else:
            try:
                jira_header = lines.index("### Related Jira Tickets\r")
            except:
                pass
            else:
                raise ValueError(f"Jira section found in body, but the label attached is {self.label_groups['type'][0]}.")

        # Validate Breaking Changes section
        if "breaking" in self.label_groups["impact"]:
            try:
                breaking_header = lines.index("### Breaking Changes\r")
                breaking_footer = lines.index("---\r", breaking_header)
                for i in range(breaking_header+1, breaking_footer):
                    if "### " in lines[i]:
                        raise Exception(f"Improper breaking changes section in body, presence of another heading detected.")
            except ValueError as ve:
                raise ValueError(f"Breaking Changes section not found in body.")
        else:
            try:
                breaking_header = lines.index("### Breaking Changes\r")
            except:
                pass
            else:
                raise ValueError(f"Breaking Changes header found in body, but the `impact/breaking` label was not attached.")

        # Validate deprecations section
        if "deprecate" in self.label_groups["impact"]:
            try:
                deprecate_header = lines.index("### Deprecations\r")
                deprecate_footer = lines.index("---\r", deprecate_header)
                for i in range(deprecate_header+1, deprecate_footer):
                    if "### " in lines[i]:
                        raise Exception(f"Improper deprecations section in body, presence of another heading detected.")
            except ValueError as ve:
                raise ValueError(f"Deprecations section not found in body.")
        else:
            try:
                deprecate_header = lines.index("### Deprecations\r")
            except:
                pass
            else:
                raise ValueError(f"Deprecations header found in body, but the `impact/deprecate` label was not attached.")

    def validate_branch(self) -> None:
        """
        If any `type` label which is associated with a Jira is attached then
        the pull request branch should start with the Jira ID
        """

        # form the regex pattern based on the `tyoe` labels
        if self.label_groups["type"][0] in ["chore", "documentation"]:
            pattern = r'.+'
        else:
            pattern = r'[A-Z]+-\d+-[\w\d-]+'
        if not bool(re.match(pattern, self.branch)):
            raise ValueError(f"Improper branch: {self.branch}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Fetch Pull Request number')
    parser.add_argument('pr_number', help='The number of the Pull Request')
    args = parser.parse_args()

    # Instantiate PR
    pr = PR(args.pr_number)

    # Validate
    pr.validate_title()
    pr.validate_body()
    pr.validate_branch()
