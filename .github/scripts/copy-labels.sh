#!/bin/bash

labels=$(gh api repos/$1/$2/labels | jq -r '.[].name')
for label in $labels; do
  gh label delete $label --yes
done
gh label clone chandratop/release-note-generator --repo $1/$2
