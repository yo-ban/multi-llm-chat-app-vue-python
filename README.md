# Multi-LLM Chat Application

<div align="center">
  <img src="images/icon.png" alt="App Icon" width="128" height="128">
</div>

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Vue](https://img.shields.io/badge/Vue.js-3.4-4FC08D?logo=vue.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?logo=fastapi&logoColor=white)

This application provides a chat interface for interacting with multiple Large Language Models (LLMs). It supports models from OpenAI, Anthropic, Google (Gemini), xAI (Grok), and custom models via OpenRouter. Key features include text and image input processing, file text extraction, and integration with MCP servers for tool usage.

> **Note**: Built for learning LLM APIs and web app integration, this project focuses on functional implementation rather than production-level architecture. It is intended solely for local, single-user use and lacks multi-user support.

## 🌟 Features

- **Multi-Model Support**: Seamlessly switch between different AI models:
  - OpenAI
  - Anthropic
  - Google AI Studio
  - xAI (Grok)
  - OpenRouter (Custom model IDs)
- **Real-time Chat**: Interactive conversations with streaming responses
- **Persona Management**: Create and manage custom AI assistant roles
- **Message Management**: Edit and delete both user and assistant messages at any time
- **Conversation Management**: Export, import, and manage chat histories
- **Image Support**:
    - Handle image inputs for multimodal models.
    - Generate images using specific models (e.g., Gemini 2.0 Flash Experimental).
- **Web Search Integration**: Enable web search capabilities for enhanced responses
- **File Processing**: Upload and extract text from various file formats (PDF, HTML, Markdown, etc.).
- **MCP Server Integration**: Connects to Model Context Protocol (MCP) compliant servers to leverage local tools and data sources.
  - **Server Configuration**: Add and manage connections to various MCP servers (Stdio or HTTP).
  - **Tool Control**: Enable or disable specific tools offered by connected MCP servers globally via settings.

## 📸 Screenshots

<div align="center">
  <img src="images/screenshot.png" alt="Chat Interface" width="600">
</div>

## 🚀 Tech Stack

### Frontend
- Vue 3 with Composition API
- TypeScript
- Pinia for state management
- PrimeVue for UI components
- Vite for build tooling

### Backend
- Python 3.11
- FastAPI

## ⚙️ Setup (Recommended: Docker)

Deploying using Docker Compose is the recommended way to run this application.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/multi-llm-chat-app-vue-python.git
    cd multi-llm-chat
    ```

2.  **Create Environment Variables**:
    Create a `.env` file in the root directory of the project with the following content. Replace the placeholder values with your actual credentials and settings.

    ```dotenv
    # Optional: Required for web search, browsing, and specific model features
    GEMINI_API_KEY=your_gemini_api_key
    GEMINI_MODEL_NAME=gemini-2.0-flash # Gemini model with support for grounding by Google search

    # Required for encryption of API keys and MCP configurations
    # Generate a secure key using: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY=your_secure_fernet_encryption_key

    # Required: PostgreSQL database connection details (used by Docker Compose)
    POSTGRES_DB=appdb
    POSTGRES_USER=user
    POSTGRES_PASSWORD=password
    ```
    *   **Note:** Ensure the `ENCRYPTION_KEY` is kept secret and secure. The `POSTGRES_*` variables should match the values defined in your `docker-compose.yml` if you customize them.

3.  **Build and Start**:
    Run the following command to build the Docker images and start the application containers in detached mode:
    ```bash
    docker compose up -d --build
    ```

The application will be available at:
- Frontend: http://localhost:10000
- Backend API: http://localhost:5200

## ⚙️ Setup (Optional: Manual Installation)

> **Warning:** Manual installation is **not the recommended setup** and might not be fully tested.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/multi-llm-chat-app-vue-python.git
    cd multi-llm-chat
    ```

2.  **Create Environment Variables**:
    Create a `.env` file in the `backend` directory of the project with the following content:

    ```dotenv
    # Optional: Required for web search, browsing, and specific model features
    GEMINI_API_KEY=your_gemini_api_key
    GEMINI_MODEL_NAME=gemini-2.0-flash # Gemini model with support for grounding by Google search

    # Required for encryption of API keys and MCP configurations
    # Generate a secure key using: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY=your_secure_fernet_encryption_key

    # Required: Database connection URL for the backend (replace with your actual DB connection)
    # Example for local PostgreSQL:
    DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/appdb
    # Example for SQLite (requires adjusting database.py and potentially alembic/env.py):
    # DATABASE_URL=sqlite:///./local_chat.db
    ```
    *   **Note:** For manual installation, you need to set up and manage your own database (e.g., PostgreSQL) and provide the correct `DATABASE_URL`. The encryption key is also mandatory.

3.  **Set up the backend**:
    ```bash
    cd backend
    # Recommended: Create and activate a virtual environment
    # python -m venv venv
    # source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    # Initialize or migrate the database
    alembic upgrade head
    ```

4.  **Set up the frontend**:
    ```bash
    cd ../frontend
    npm install
    ```

5.  **Start the servers**:
    ```bash
    # Backend (from backend directory)
    # Ensure your virtual environment is active if you created one
    python run_local.py # Or: uvicorn app.main:app --host 0.0.0.0 --port 5200 --reload

    # Frontend (from frontend directory, in a separate terminal)
    npm run dev
    ```

## 🔑 API Keys Configuration

Configure your API keys in the application settings:
- OpenAI 
- Anthropic
- Google AI Studio
- xAI
- OpenRouter

All API keys can be configured through the application settings interface.  
To avoid leaving the API key in the browser, it is stored in the backend DB using an encryption key.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Thanks to all the AI model providers for their amazing APIs
- The Vue.js and FastAPI communities for their excellent documentation
- All contributors who have helped shape this project

## 📧 Contact

For questions and support, please open an issue in the GitHub repository.

---
Built with ❤️ using Vue.js and FastAPI