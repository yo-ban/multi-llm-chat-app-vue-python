#!/bin/bash
set -e

BASE_DIR="/mcp-servers"
ECOSYSTEM_FILE="${BASE_DIR}/ecosystem.config.cjs"

echo "--- Debug: Listing ${BASE_DIR} at container start ---"
ls -la "${BASE_DIR}"
echo "--- Debug: End listing ---"

echo "Generating PM2 ecosystem file..."

echo "module.exports = {" > "${ECOSYSTEM_FILE}"
echo "  apps: [" >> "${ECOSYSTEM_FILE}"

# ポート番号リストを配列化
PORTS=($PORT_SERVER_1 $PORT_SERVER_2 $PORT_SERVER_3 $PORT_SERVER_4 $PORT_SERVER_5)

i=0
find "${BASE_DIR}" -maxdepth 1 -mindepth 1 -type d | while read repo_dir; do
  repo_name=$(basename "${repo_dir}")
  package_json="${repo_dir}/package.json"

  if [ -f "${package_json}" ]; then
    port=${PORTS[$i]}
    if [ -z "$port" ]; then
      port=$((3001 + i))
    fi

    echo "    {" >> "${ECOSYSTEM_FILE}"
    echo "      name: '${repo_name}'," >> "${ECOSYSTEM_FILE}"
    echo "      cwd: '${repo_dir}'," >> "${ECOSYSTEM_FILE}"
    echo "      script: 'npm'," >> "${ECOSYSTEM_FILE}"
    echo "      args: 'start $port'," >> "${ECOSYSTEM_FILE}"
    echo "      autorestart: true," >> "${ECOSYSTEM_FILE}"
    echo "      watch: false," >> "${ECOSYSTEM_FILE}"
    echo "      max_memory_restart: '250M'" >> "${ECOSYSTEM_FILE}"
    echo "    }," >> "${ECOSYSTEM_FILE}"

    i=$((i+1))
  else
    echo "  Skipping directory (no package.json found): ${repo_dir}"
  fi
done

echo "  ]" >> "${ECOSYSTEM_FILE}"
echo "};" >> "${ECOSYSTEM_FILE}"

echo "Ecosystem file generated at ${ECOSYSTEM_FILE}:"
cat "${ECOSYSTEM_FILE}"

echo "Starting PM2..."
exec pm2-runtime start "${ECOSYSTEM_FILE}"