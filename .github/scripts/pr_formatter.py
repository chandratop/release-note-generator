"""
script: formatter.py

This script looks at the labels on the pull request and formats the title and
body of the pull request. In the future this will also be able to send slack
notifications if the "help/request" label is attached.
"""

import argparse
from pr_validator import PR
from utils.utils import run

class PRFormatter(PR):

    def __init__(self, pr_number: str):
        super().__init__(pr_number)

    def generate_pr_body_format(self) -> str:
        """
        This function forms the body of the pull request and returns it.
        """

        body = ""
        if self.label_groups["type"][0] in ["chore", "documentation"]:
            with open(".github/templates/no-jira.md") as f:
                body += f.read()
        else:
            with open(".github/templates/jira.md") as f:
                body += f.read()
        for impact_type in self.label_groups["impact"]:
            with open(f".github/templates/{impact_type}.md") as f:
                body += f.read()
        return body

    def generate_pr_title_format(self) -> str:
        """
        This function forms the title template for a pull request and returns it.
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
        title = f"{mapping[self.label_groups['type'][0]]}"
        if self.label_groups["type"][0] not in ["chore", "documentation"]:
            title += "(JIRA-000)"
        if len(self.label_groups["impact"]) > 0:
            title += "!"
        title += ": Sample title"
        return title

    def save_previous_pr(self) -> None:
        """
        This backs up the current pull request body and title as a comment.
        """

        # Check if there is an existing backup comment
        has_existing = False
        cmd = f'gh pr view "{self.pr_number}" --json comments'
        result = run(cmd)
        if result.fine:
            all_comments = eval(result.what)["comments"]
            for comment in all_comments:
                comment_body: str = comment["body"]
                if comment_body.startswith("## BACKUP\n"):
                    has_existing = True
                    break

        else:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

        # Back up the current pull request
        cmd = f'gh pr comment "{self.pr_number}" --body "## BACKUP\n{self.title}\n{self.body}"'
        if has_existing:
            cmd += ' --edit-last'
        result = run(cmd)
        if not result.fine:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

    def format_pr_body(self, body, title) -> None:
        """
        Run the gh command to edit the pull request body and title.
        """

        cmd = f'gh pr edit "{self.pr_number}" --body "{body}" --title "{title}"'
        result = run(cmd)
        if not result.fine:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Fetch Pull Request number')
    parser.add_argument('pr_number', help='The number of the Pull Request')
    args = parser.parse_args()

    # Instantiate PR
    pr = PRFormatter(args.pr_number)

    # Take backup
    # pr.save_previous_pr()

    # Format
    pr.format_pr_body(
        body=pr.generate_pr_body_format(),
        title=pr.generate_pr_title_format()
    )
