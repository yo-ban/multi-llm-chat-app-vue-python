#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# Base directory where repositories are cloned
BASE_DIR="/mcp-servers"
# PM2 ecosystem configuration file path
ECOSYSTEM_FILE="${BASE_DIR}/ecosystem.config.cjs" # Use .cjs for explicit CommonJS

echo "--- Debug: Listing ${BASE_DIR} at container start ---"
ls -la "${BASE_DIR}"
echo "--- Debug: End listing ---"

echo "Generating PM2 ecosystem file..."

# Start ecosystem file structure (using CommonJS syntax)
echo "module.exports = {" > "${ECOSYSTEM_FILE}"
echo "  apps: [" >> "${ECOSYSTEM_FILE}"

# Find all directories directly under BASE_DIR (potential repos)
find "${BASE_DIR}" -maxdepth 1 -mindepth 1 -type d | while read repo_dir; do
  repo_name=$(basename "${repo_dir}")
  package_json="${repo_dir}/package.json"

  # Check if package.json exists
  if [ -f "${package_json}" ]; then
    echo "  Found MCP server: ${repo_name} in ${repo_dir}"

    # Extract start script or main file (optional, defaulting to 'npm start')
    # More robust parsing could be added here if needed
    start_script="npm"
    start_args="start"
    # You could try parsing package.json for main/start script if needed
    # start_command=$(node -p "require('${package_json}').scripts.start || 'node ' + require('${package_json}').main")

    # Add app entry to ecosystem file
    # Ensure proper quoting for paths and names containing spaces/special chars (though unlikely for repo names)
    echo "    {" >> "${ECOSYSTEM_FILE}"
    echo "      name: '${repo_name}'," >> "${ECOSYSTEM_FILE}"
    echo "      cwd: '${repo_dir}'," >> "${ECOSYSTEM_FILE}"
    echo "      script: '${start_script}'," >> "${ECOSYSTEM_FILE}"
    echo "      args: '${start_args}'," >> "${ECOSYSTEM_FILE}"
    # Add env section if you want to ensure container env vars are passed (pm2 usually does this)
    # echo "      env: process.env," >> "${ECOSYSTEM_FILE}"
    # Add any other PM2 options here (e.g., watch, instances, max_memory_restart)
    echo "      autorestart: true," >> "${ECOSYSTEM_FILE}"
    echo "      watch: false," >> "${ECOSYSTEM_FILE}" # Disable watch unless needed
    echo "      max_memory_restart: '250M'" >> "${ECOSYSTEM_FILE}" # Example memory limit
    echo "    }," >> "${ECOSYSTEM_FILE}"
  else
    echo "  Skipping directory (no package.json found): ${repo_dir}"
  fi
done

# Close the apps array and module.exports
echo "  ]" >> "${ECOSYSTEM_FILE}"
echo "};" >> "${ECOSYSTEM_FILE}"

echo "Ecosystem file generated at ${ECOSYSTEM_FILE}:"
cat "${ECOSYSTEM_FILE}"

# Start PM2 using the generated ecosystem file in the foreground
# Use pm2-runtime for better Docker integration (handles signals correctly)
echo "Starting PM2..."
exec pm2-runtime start "${ECOSYSTEM_FILE}"

