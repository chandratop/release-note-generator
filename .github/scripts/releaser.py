"""
script: releaser.py

This script helps create a GitHub Release, CHANGELOG and Breaking-Change-SOPs
"""

import os
import re
import argparse
from utils.utils import run
from datetime import datetime


class Release:

    def __init__(self):
        self.tag = self.latest_tag()
        self.next_tag = ""
        self.prs = self.get_pr_list()

    def get_today(self) -> str:
        """
        return today's yyyy-mm-dd
        """

        current_datetime = datetime.now()
        formatted_date = current_datetime.strftime('%Y-%m-%d')
        return formatted_date

    def latest_tag(self) -> str:
        """
        Return the latest tag.
        """

        cmd = 'gh release list --exclude-drafts --exclude-pre-releases --limit 5 --json tagName --json isLatest'
        result = run(cmd)
        if result.fine:
            result_str = str(result.what)
            result_str = result_str.replace("true","True")
            result_str = result_str.replace("false","False")
            response_list: list = eval(result_str)
            for response in response_list:
                if response["isLatest"]:
                    return response["tagName"]
            raise ValueError(f"Latest tag not found in {response_list}")
        else:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

    def get_pr_list(self) -> list:
        """
        Returns a list of prs which will be mentioned in the next release.
        """

        cmd = f'git log {self.tag}..main --oneline'
        result = run(cmd)
        if result.fine:
            response_lines = result.what.split("\n")
            prs = list()
            pattern = r'^.+#(\d+).+$'
            for line in response_lines:
                match = re.match(pattern, line)
                if bool(match):
                    prs.append(match.group(1))
            return prs
        else:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

    def get_title_parts(self, pr: str) -> dict:
        """
        Get the type and description from the pr title.
        """

        cmd = f'gh pr view "{pr}" --json title'
        result = run(cmd)
        if result.fine:
            full_title = eval(result.what)["title"]
            title_split = full_title.split(": ")
            paranthesis_index = title_split[0].find("(")
            if paranthesis_index == -1:
                return {"type": title_split[0], "title": title_split[1].strip()}
            else:
                return {"type": title_split[0][:paranthesis_index], "title": title_split[1].strip()}
        else:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

    def get_author(self, pr: str) -> bool:
        """
        Get the author of the pr.
        """

        cmd = f'gh pr view "{pr}" --json author'
        result = run(cmd)
        if result.fine:
            result_str = str(result.what)
            result_str = result_str.replace("true","True")
            result_str = result_str.replace("false","False")
            return eval(result_str)["author"]["login"]
        else:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

    def get_url(self, pr: str) -> bool:
        """
        Get the url of the pr.
        """

        cmd = f'gh pr view "{pr}" --json url'
        result = run(cmd)
        if result.fine:
            return eval(result.what)["url"]
        else:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

    def get_jiras(self, pr: str) -> list:
        """
        Get the list or jira tickets mentioned in the pr.
        """

        cmd = f'gh pr view "{pr}" --json body'
        result = run(cmd)
        jiras = list()
        if result.fine:
            body = eval(result.what)["body"]
            jira_header_index: int = body.find("### Related Jira Tickets")
            jira_end_index: int = body.find("-----", jira_header_index)
            jira_section: str = body[jira_header_index:jira_end_index]
            jira_section_split: list[str] = jira_section.split("\n")
            for line in jira_section_split:
                if line.startswith("- "):
                    jiras.append(line[2:].strip())
            return jiras
        else:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

    def get_sops(self, pr: str) -> list:
        """
        Get the list or SOPs mentioned in the prs.
        """

        cmd = f'gh pr view "{pr}" --json body'
        result = run(cmd)
        sop = list()
        if result.fine:
            body = eval(result.what)["body"]
            sop_header_index: int = body.find("### Breaking Changes")
            sop_end_index: int = body.find("-----", sop_header_index)
            sop_section: str = body[sop_header_index:sop_end_index]
            sop_section_split: list[str] = sop_section.split("\n")
            for line in sop_section_split:
                if not line.startswith("<!") and "### Breaking Changes" not in line:
                    sop.append(f'{line.strip()}\n')
        else:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")
        return sop

    def is_ignore(self, pr: str) -> bool:
        """
        If the pr is labeled with `ignore` then return True, otherwise return False.
        """

        cmd = f'gh pr view "{pr}" --json labels'
        result = run(cmd)
        if result.fine:
            labels_list = eval(result.what)["labels"]
            for label in labels_list:
                if label["name"] == "ignore":
                    return True
            return False
        else:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

    def get_next_tag(self, index: int) -> str:
        """
        Calculate the next tag based on what to update (major/minor/patch)
        """

        pattern = r'^(\w*_*)(\d+\.\d+\.\d+)$'
        match = re.match(pattern, self.tag)
        if bool(match):
            tag = match.group(2)
            tag_split: list[int] = list(map(int, tag.split(".")))
            tag_split[index] += 1
            for i in range(index+1, 3):
                tag_split[i] = 0
            return match.group(1) + ".".join(list(map(str, tag_split)))
        else:
            raise ValueError(f"Unable to calculate next tag for {self.tag}")

    def get_tag_operation(self) -> int:
        """
        return 0 if major
        return 1 if minor
        return 2 if patch
        """

        all_types = list()
        for pr in self.prs:
            all_types.append(self.get_title_parts(pr)["type"])
        if "break" in all_types:
            return 0
        elif "feat" in all_types or "enh" in all_types:
            return 1
        else:
            return 2

    def get_release_details(self) -> dict:
        """
        Read the release_template.md file and return the formatted release
        Do the same for CHANGELOG.md and BREAKING_CHANGES.md
        """

        # Get the release template
        with open(".github/release_template.md") as f:
            body = f.read()

        # Get next tag
        self.next_tag = self.get_next_tag(index = self.get_tag_operation())

        # Form the changelog_body
        changelog_body = f'## {self.next_tag} [{self.get_today()}]\n| ID | Type | Title | Author | JIRA |\n| -------------- | -------------- | -------------- | -------------- | -------------- |\n'

        # Replace all template strings in body
        body = body.replace("NEXT_TAG", self.next_tag)
        body = body.replace("PREVIOUS_TAG", self.tag)

        # Group all PRs for the next release notes
        groups = {
            "feat": [],
            "break": [],
            "sop": [],
            "other": []
        }
        type_mapping = {
            "fix": "bugfix",
            "enh": "enhancement",
            "feat": "feature",
            "break": "breaking",
            "chore": "chore"
        }
        for pr in self.prs:
            # Continue if ignore
            if self.is_ignore(pr):
                continue

            # Form each part of the line
            title_parts = self.get_title_parts(pr)
            url = self.get_url(pr)
            type = type_mapping[title_parts["type"]]
            title = title_parts["title"]
            author = f'@{self.get_author(pr)}'
            jiras = ""
            jira_list = self.get_jiras(pr)
            for jira in jira_list:
                jiras += jira + ", "
            jiras = jiras[:-2]

            # Form the line
            line = f'| {url} | {type} | {title} | {author} | {jiras} |\n'

            # Save each part in its group
            if type in ["breaking"]:
                groups["break"].append(line)
                groups["sop"].append(f'{url}\n')
                groups["sop"].extend(self.get_sops(pr))
            elif type in ["feature", "enhancement"]:
                groups["feat"].append(line)
            else:
                groups["other"].append(line)

        # Update each group section in the body
        for key, value in groups.items():
            if value != []:
                body_end_identifier = f'<!--- {key} body end -->'
                body_end_identifier_index = body.find(body_end_identifier)
                lines = ""
                for line in value:
                    lines += line
                body = body[:body_end_identifier_index] + lines + body[body_end_identifier_index:]
                if key in ["feat", "break", "other"]:
                    changelog_body += lines
            else:
                # Remove the section as there are no changes
                header_start_identifier = f'<!--- {key} header start -->'
                body_end_identifier = f'<!--- {key} body end -->'
                header_start_identifier_index = body.find(header_start_identifier)
                body_end_identifier_index = body.find(body_end_identifier)
                body = body[:header_start_identifier_index] + body[body_end_identifier_index:]

        # Return formatted release body
        return {"release": body, "changelog": changelog_body}

    def update_changelog(self, body) -> None:
        """
        If the CHANGELOG.md file does not exist, create it.
        If it exists, then update the changelog for the next release
        """

        if not os.path.exists("CHANGELOG.md"):
            changelog = self.create_changelog()
        else:
            with open("CHANGELOG.md") as f:
                changelog = f.read()
        changelog_heading = "# Changelog\n"
        insert_index = len(changelog_heading) + 1
        changelog = changelog[:insert_index] + body + changelog[insert_index:]
        with open("CHANGELOG.md", "w") as f:
            f.write(changelog)

    def create_changelog(self):
        """
        Create the changelog file for the first time
        """

        # Get past tags (limit=240)
        cmd = 'gh release list --limit 240 --exclude-drafts --exclude-pre-releases --json publishedAt --json tagName'
        result = run(cmd)
        if result.fine:
            response = eval(result.what)
            changelog = ""
            for tag in response:
                pattern = r'^(\w*_*)(\d+\.\d+\.\d+)$'
                match = re.match(pattern, tag["tagName"])
                if bool(match):
                    changelog += f'<details><summary>{tag["tagName"]} [{tag["publishedAt"][:10]}]</summary>\n\n'
                    cmd_get_pr_body = f'gh release view "{tag["tagName"]}" --json body'
                    result_get_pr_body = run(cmd_get_pr_body)
                    if result_get_pr_body.fine:
                        changelog += eval(result_get_pr_body.what)["body"] + "\n\n</details>\n\n---\n\n"
                    else:
                        raise ValueError(f"Command failed: {cmd_get_pr_body}\nError: {result_get_pr_body.what}")
            changelog = "# Changelog\n\n" + "## Legacy Release Notes\n" + changelog
            return changelog
        else:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

    def release(self) -> None:
        """
        Create release
        """
        pass

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Fetch Pull Request number')
    parser.add_argument('action', help='notes or release')
    args = parser.parse_args()

    release = Release()

    if args.action == "notes":
        release_details = release.get_release_details()

        # write the changelog in CHANGELOG.md
        release.update_changelog(release_details["changelog"])

        # write the release notes for the next release in RELEASE.md
        with open("RELEASE.md", "w") as f:
            f.write(release_details["release"])

        # update any file with the new release tag
        for file_name in ["releases.yaml"]:
            with open(file_name) as f:
                body = f.read()
            body = body.replace(f'{release.tag}', f'{release.next_tag}')
            with open(file_name, "w") as f:
                f.write(body)

        # Add the changes
        cmd = 'git add .'
        result = run(cmd)
        if not result.fine:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

        # Create a branch
        branch = f'release-{release.next_tag}'
        cmd = f'git checkout -b {branch}'
        result = run(cmd)
        if not result.fine:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

        # Commit the changes
        cmd = f'git commit -m "{branch}"'
        result = run(cmd)
        if not result.fine:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

        # Push the changes
        cmd = f'git push --set-upstream origin {branch}'
        result = run(cmd)
        if not result.fine:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

        # Checkout to main branch
        cmd = f'git checkout main'
        result = run(cmd)
        if not result.fine:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

        # Create a pull request
        cmd = f'gh pr create --base main --head {branch} --title "chore: {branch}" --label release --body-file .github/pull_request_template.md'
        result = run(cmd)
        if not result.fine:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

    else:
        branch_name = release.get_title_parts(args.action)["title"]
        release_tag = branch_name[8:]

        # Checkout to branch_name
        cmd = f'git checkout {branch_name}'
        result = run(cmd)
        if not result.fine:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")

        # Create the release
        cmd = f'gh release create {release_tag} --notes RELEASE.md --title "{release_tag}"'
        result = run(cmd)
        if not result.fine:
            raise ValueError(f"Command failed: {cmd}\nError: {result.what}")
