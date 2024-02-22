"""
script: formatter.py

This script looks at the labels on the pull request and formats the title and
body of the pull request. In the future this will also be able to send slack
notifications if the "help/request" label is attached.
"""

from pr_validator import PRValidator

class PRFormatter(PRValidator):

    def __init__(self, pr_number: str):
        super().__init__(pr_number)
