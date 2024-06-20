#!/bin/bash -x
# backup the list of known secrets
cd $WORKSPACE/Medusa
cp .secrets.baseline .secrets.new

# find all the secrets in the repository
detect-secrets scan --baseline .secrets.new $(find . -type f ! -name '.secrets.*' ! -path '*/.git*' ! -path '*pycache*' ! -path '*venv*' ! -path '*.vscode*' ! -path '*.pytest_cache*')

# if there is any difference between the known and newly detected secrets, print and exit.
list_secrets() { jq -r '.results | keys[] as $key | "File: \($key), Line Number: \(.[$key] | .[] | .line_number), Type: \(.[$key] | .[] | .type)"' "$1" | sort; }

if ! diff <(list_secrets .secrets.baseline) <(list_secrets .secrets.new) >&2; then
  echo "Detected new secrets in the repo" >&2
  exit 1
fi
