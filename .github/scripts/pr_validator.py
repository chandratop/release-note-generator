"""
script: pr_validator.py

This script validates a pull request's title, body & branch name.
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
    body & labels.
    """

    def __init__(self, pr_number: str) -> None:

        self.pr_number = pr_number
        self.labels, self.title, self.body, self.branch = self._get_pr_variables()

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

    def validate_title(self) -> str:
        """
        The title should follow the pattern -
        ```
            type(Jira): Brief description
        ```
        """

        pattern = r'^(fix|enh|feat|break)\(\w+-\d+\): [\w\d\-\. ]+$|(chore): [\w\d\-\. ]+$'
        match = re.match(pattern, self.title)
        if not bool(match):
            raise ValueError(f"Improper title: {self.title}\nregex: '{pattern}'")
        else:
            if bool(match.group(1)):
                return match.group(1)
            else:
                return match.group(2)

    def validate_body(self, pr_type: str) -> None:
        """
        If the pr_type is one of `fix`, `enh`, `feat` or `break`,
        then the `Related Jira Tickets` section should not have `N/A`.
        If the pr_type is `break` then the `Breaking Changes` section
        should not have `N/A`
        """

        if pr_type in ["fix", "enh", "feat", "break"]:
            jira_section_start = self.body.find("### Related Jira Tickets")
            jira_section_end = self.body.find("-----", jira_section_start)
            jira_section_lines = self.body[jira_section_start:jira_section_end].split("\n")
            number_of_points = 0
            for line in jira_section_lines:
                if line.startswith("-"):
                    number_of_points += 1
                    if "N/A" in line:
                        raise ValueError(f"Jira section cannot contain N/A")
            if number_of_points == 0:
                raise ValueError(f"Jira section cannot be empty")

        if pr_type == "break":
            breaking_section_start = self.body.find("### Breaking Changes")
            breaking_section_end = self.body.find("-----", breaking_section_start)
            breaking_section_lines = self.body[breaking_section_start:breaking_section_end].split("\n")
            number_of_points = 0
            for line in breaking_section_lines:
                if line.startswith("-"):
                    number_of_points += 1
                    if "N/A" in line:
                        print(breaking_section_lines)
                        raise ValueError(f"Breaking Changes section cannot contain N/A")
            if number_of_points == 0:
                raise ValueError(f"Breaking Changes section cannot be empty")

    def validate_branch(self, pr_type: str) -> None:
        """
        If any `type` label which is associated with a Jira is attached then
        the pull request branch should start with the Jira ID
        """

        # form the regex pattern based on `pr_type`
        if pr_type == "chore":
            pattern = r'.+'
        else:
            pattern = r'[A-Z]+-\d+-[\w\d-]+'
        if not bool(re.match(pattern, self.branch)):
            raise ValueError(f"Improper branch: {self.branch}")

    def labeler(self, pr_type: str) -> None:
        """
        Post all checks are complete, it will validate and if needed
        correct the labels attached to the PR
        """

        type_mapping = {
            "fix": "type/bugfix",
            "enh": "type/enhancement",
            "feat": "type/feature",
            "break": "type/breaking",
            "chore": "type/chore"
        }
        remove_label = list()
        add_label = list()
        for label in self.labels:
            if label.startswith("type/"):
                if label != type_mapping[pr_type]:
                    if label not in remove_label:
                        remove_label.append(label)
        if type_mapping[pr_type] not in add_label and type_mapping[pr_type] not in self.labels:
            add_label.append(type_mapping[pr_type])

        # Form the command to fix labels
        cmd = f'gh pr edit "{self.pr_number}"'
        if len(add_label) > 0:
            labels_str = ",".join(add_label)
            cmd += f' --add-label "{labels_str}"'
        if len(remove_label) > 0:
            labels_str = ",".join(remove_label)
            cmd += f' --remove-label "{labels_str}"'
        if cmd != f'gh pr edit "{self.pr_number}"':
            result = run(cmd)
            if not result.fine:
                raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Fetch Pull Request number')
    parser.add_argument('pr_number', help='The number of the Pull Request')
    args = parser.parse_args()

    # Instantiate PR
    pr = PR(args.pr_number)

    # Validate
    pr_type = pr.validate_title()
    pr.validate_body(pr_type)
    pr.validate_branch(pr_type)
    pr.labeler(pr_type)
