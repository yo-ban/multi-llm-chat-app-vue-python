# Multi-LLM Chat Application

<div align="center">
  <img src="images/icon.png" alt="App Icon" width="128" height="128">
</div>

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Vue](https://img.shields.io/badge/Vue.js-3.4-4FC08D?logo=vue.js&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.3-3178C6?logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?logo=fastapi&logoColor=white)

A versatile chat application that enables interaction with multiple Large Language Models (LLMs) through a unified interface. This application supports various AI models including OpenAI, Anthropic, Gemini, DeepSeek, and custom models through OpenRouter, offering features like image analysis, web search, and file processing capabilities.

> **Note**: This is a learning project created for exploring and understanding various LLM APIs and web application development. The architecture and implementation choices are kept simple for educational purposes and may not reflect production-grade best practices.

## 🌟 Features

- **Multi-Model Support**: Seamlessly switch between different AI models:
  - OpenAI
  - Anthropic
  - Google AI Studio
  - DeepSeek
  - OpenRouter (Custom model IDs)
- **Real-time Chat**: Interactive conversations with streaming responses
- **Message Management**: Edit and delete both user and assistant messages at any time
- **Image Analysis**: Send and process images during conversations
- **Web Search Integration**: Enable web search capabilities for enhanced responses
- **File Processing**: Upload and analyze various file formats (PDF, HTML, Markdown, etc.)
- **Persona Management**: Create and manage custom AI assistant roles
- **Conversation Management**: Export, import, and manage chat histories

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

## ⚙️ Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/multi-llm-chat-app-vue-python.git
cd multi-llm-chat
```

2. Set up the frontend:
```bash
cd frontend
npm install
```

3. Set up the backend:
```bash
cd backend
pip install -r requirements.txt
```

4. Optional: Create environment variables:
```bash
# Backend (.env)
# Optional: Only required if you want to use web search functionality
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL_NAME=gemini-2.0-flash
```

5. Start the development servers:
```bash
# Frontend
cd frontend
npm run dev

# Backend
cd backend
python run_local.py
```

## 🐳 Docker Deployment

Deploy using Docker Compose:
1. Optional: Create environment variables:
```bash
# Root directory (.env)
# Optional: Only required if you want to use web search functionality
GEMINI_API_KEY=your_gemini_api_key
```

2. Build and start the application:
```bash
docker compose up -d --build
```

The application will be available at:
- Frontend: http://localhost:10000
- Backend: http://localhost:5200

## 🔑 API Keys Configuration

Configure your API keys in the application settings:
- OpenAI 
- Anthropic
- Google AI Studio
- DeepSeek
- OpenRouter

All API keys can be configured through the application settings interface.

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