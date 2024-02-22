"""
script: validator.py

This script validates a pull request's title, body, labels & branch name.
If all the validations pass then it will allow merging the pull request.
Otherwise it will block the merge.
"""

class PRValidator:
    """
    This class consists of modules that validates each component namely title,
    body & labels. The validations for title & body are dependent on labels.
    """

    def __init__(self, pr_number: str):
        self.pr_number = pr_number
