#!/bin/bash

# Load environment variables
if [ -f /home/khkh/Documents/github/intrising_workspace_monitor/.env ]; then
    export $(grep -v '^#' /home/khkh/Documents/github/intrising_workspace_monitor/.env | grep GITHUB_TOKEN | xargs)
fi

# Repository list
repos=(
    "Intrising/QA-Switch-OS5"
    "Intrising/test-cloud"
    "Intrising/QA-Switch-OS6"
    "Intrising/QA-Video-switch"
    "Intrising/QA-Switch-OS3OS4"
    "Intrising/QA-Switch-OS2"
    "Intrising/QA-Viewer"
    "Intrising/test-switch"
)

output_file="/tmp/issue_templates_output.txt"
> "$output_file"

echo "Fetching issue templates from GitHub repositories..."
echo ""

for repo in "${repos[@]}"; do
    echo "=============================================" | tee -a "$output_file"
    echo "Repository: $repo" | tee -a "$output_file"
    echo "=============================================" | tee -a "$output_file"
    echo "" | tee -a "$output_file"

    # Get the list of files in .github/ISSUE_TEMPLATE
    response=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/repos/$repo/contents/.github/ISSUE_TEMPLATE")

    # Check if the directory exists
    if echo "$response" | grep -q "Not Found"; then
        echo "No .github/ISSUE_TEMPLATE directory found" | tee -a "$output_file"
        echo "" | tee -a "$output_file"
        continue
    fi

    if echo "$response" | grep -q "message"; then
        echo "Error accessing repository: $(echo $response | jq -r '.message' 2>/dev/null || echo 'Unknown error')" | tee -a "$output_file"
        echo "" | tee -a "$output_file"
        continue
    fi

    # Parse the file list
    file_count=$(echo "$response" | jq '. | length' 2>/dev/null)

    if [ -z "$file_count" ] || [ "$file_count" = "null" ]; then
        echo "No issue templates found or error parsing response" | tee -a "$output_file"
        echo "" | tee -a "$output_file"
        continue
    fi

    echo "Found $file_count template file(s)" | tee -a "$output_file"
    echo "" | tee -a "$output_file"

    # Iterate through each file
    for i in $(seq 0 $((file_count - 1))); do
        filename=$(echo "$response" | jq -r ".[$i].name")
        download_url=$(echo "$response" | jq -r ".[$i].download_url")

        echo "-------------------------------------------" | tee -a "$output_file"
        echo "Template 文件: $filename" | tee -a "$output_file"
        echo "-------------------------------------------" | tee -a "$output_file"
        echo "內容:" | tee -a "$output_file"
        echo "" | tee -a "$output_file"

        # Download and display the content
        content=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "$download_url")
        echo "$content" | tee -a "$output_file"

        echo "" | tee -a "$output_file"
        echo "" | tee -a "$output_file"
    done

    echo "" | tee -a "$output_file"
done

echo "============================================="
echo "All templates have been saved to: $output_file"
echo "============================================="
