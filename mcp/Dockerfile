FROM node:20-slim

# Set working directory
WORKDIR /mcp-servers

# Install git (for cloning) and build-essential (for potential native addons during npm install)
# Use --no-install-recommends to minimize image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    python3 \
    make \
    g++ \
    libgnutls30 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# RUN  apt install -y libgnutls30 
# RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 648ACFD622F3D138

# Install pm2 globally
RUN npm install -g pm2

# Define ARG for the list of repositories
# Default to an empty string if not provided
ARG MCP_REPOS=""

# Clone repositories, install dependencies, and build
# Use a RUN command with shell logic to loop through the repos
# Pass the ARG value to the shell environment
RUN \
  echo "Processing MCP repositories: $MCP_REPOS" && \
  # highlight-start
  # $MCP_REPOS を echo し、xargs で各 URL を処理
  # -n 1: 一度に1つの引数（URL）を処理
  # -I {}: 各引数（URL）を {} で参照できるようにする
  echo "$MCP_REPOS" | xargs -n 1 -I {} sh -c ' \
    repo_url="{}" && \
    # リポジトリ名を取得 (以前と同じ)
    repo_name=$(basename "$repo_url" .git) && \
    echo "--- Processing repository: $repo_url (Name: $repo_name) ---" && \
    # git clone を実行
    git clone --depth 1 "$repo_url" "$repo_name" && \
    # ディレクトリが存在するかチェック
    if [ -d "$repo_name" ]; then \
      # ディレクトリに移動して処理を続ける
      cd "$repo_name" && \
      pwd && \
      echo "Installing dependencies for $repo_name..." && \
      if [ -f "package-lock.json" ]; then \
        npm ci; \
      else \
        npm install; \
      fi && \
      if [ -f "package.json" ] && grep -q "\"build\":" package.json; then \
        echo "Building $repo_name..."; \
        npm run build; \
      else \
        echo "No build script found for $repo_name, skipping build."; \
      fi && \
      # 元のディレクトリに戻る
      cd .. ; \
    else \
      echo "!!! Failed to clone repository or directory not found: $repo_url -> $repo_name !!!"; \
      # exit 1; # 必要に応じてビルドを失敗させる
    fi \
  ' sh && \
  # highlight-end
  # デバッグ: 処理完了後の /mcp-servers の内容を確認
  echo "--- Contents of ${WORKDIR} after processing ---" && \
  ls -la ${WORKDIR} && \
  echo "--- End of RUN command ---"

# Copy the entrypoint script into the container
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Expose common ports (optional, for documentation/convenience)
# The actual ports used depend on the individual servers.
EXPOSE 3001 3002 3003

# Default CMD is not needed as ENTRYPOINT handles execution
