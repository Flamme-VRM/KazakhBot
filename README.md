# AsylBILIM 📚 - Your Intelligent Study Companion for Kazakh Students

![Logo](https://github.com/user-attachments/assets/330db4a3-7fea-4dcc-8b18-365795c3dd15)


AsylBILIM is an innovative AI-powered Telegram bot designed specifically to empower Kazakhstani students. Built on a sophisticated Large Language Model (LLM), AsylBILIM provides instant, accurate, and localized assistance for a wide range of academic needs, all in the Kazakh language.

## ✨ Why AsylBILIM?

Navigating academic challenges can be tough. AsylBILIM streamlines your study process by offering:

* **100% Kazakh Language Support:** Get answers and explanations exclusively in Kazakh, ensuring clarity and cultural relevance.
* **Comprehensive Exam Preparation:** Master entrance exams like **ENT, IELTS, SAT, and TOEFL** with targeted assistance.
* **Academic Writing Aid:** Refine your essays, reports, and research papers with intelligent writing support.
* **Study Material Clarification:** Understand complex topics and difficult concepts with clear, concise explanations.
* **Personalized Learning Experience:** Leverage AI to adapt to your unique learning style and pace.

**AsylBILIM is more than just a chatbot; it's your dedicated AI tutor, always ready to help you excel!**

## 🚀 Key Features

* **Intelligent Q&A (LLM-Powered):** Ask any academic question and receive accurate, contextually relevant answers based on the advanced AlatauLLM.
* **Voice Input Support:** Seamlessly interact with the bot using voice messages. Our Speech-to-Text service accurately transcribes your Kazakh speech into text for AI processing.
* **Conversation History Management:** The bot remembers your past interactions, providing a more coherent and personalized conversation flow (history is stored for 7 days).
* **Efficient Caching System:** Frequently asked questions and their responses are cached for faster retrieval and reduced API costs.
* **User Session Management:** Keeps track of user-specific data like preferred language and session start time.
* **Robust Error Handling:** Provides user-friendly messages for AI generation issues or technical errors.
* **Markdown to HTML Conversion:** Ensures well-formatted, readable responses within Telegram using basic markdown (bold, italic, code).

## ⚙️ Technologies Used

AsylBILIM is built with a modern and efficient technology stack:

* **Python:** The core programming language for the bot's logic.
* **aiogram:** A powerful and asynchronous framework for building Telegram bots.
* **Google Generative AI (Gemini API):** Powers the core Large Language Model (LLM) for intelligent responses.
* **Redis:** Used as a high-performance in-memory data store for caching AI responses and managing user session history.
* **python-dotenv:** For secure management of environment variables.
* **SpeechRecognition:** Converts voice messages into text for AI processing.
* **pydub:** Handles audio file conversions (OGG to WAV) for speech recognition.
* **asyncio:** For asynchronous programming, ensuring the bot remains responsive.

## 🤝 Contributing

We welcome contributions from the community! If you'd like to contribute, please follow these steps:

1.  **Fork the repository.**
2.  **Create a new branch** (`git checkout -b feature/your-feature-name`).
3.  **Make your changes.**
4.  **Commit your changes** (`git commit -m 'Add new feature'`).
5.  **Push to the branch** (`git push origin feature/your-feature-name`).
6.  **Open a Pull Request.**

Please ensure your code adheres to the existing style and includes relevant tests.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

If you have any questions, issues, or suggestions, please feel free to:

* Open an issue on this GitHub repository.
* Contact the project maintainers tg:(@Vermeei).

---

### Additional Sections you might consider:

* **Getting Started (For Developers):**
    * **Prerequisites:** List software needed (Python, Docker, aiogram, python-dotenv, Redis, google-generativeai).
    * **Installation:**
        ```bash
        git clone [https://github.com/Flamme-VRM/KazakhBot.git](https://github.com/Flamme-VRM/KazakhBot.git)
        cd KazakhBot
        pip install -r requirements.txt
        ```
    * **Environment Variables (`.env` file):**
        ```
        BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
        LLM_API_KEY=YOUR_GOOGLE_GEMINI_API_KEY
        MODEL=gemini-pro # Or other preferred model
        REDIS_HOST=localhost
        REDIS_PORT=6379
        REDIS_DB=0
        SYSTEM_PROMPT="You are AsylBILIM, an AI assistant for Kazakhstani students..."
        ```
    * **Running the Bot:**
        ```bash
        python main.py
        ```
    * **Running Redis (if not already running):** Instructions for running Redis locally or via Docker.
* **Demo / Screenshots:**
    * "See AsylBILIM in action!"
    *  (![изображение]https://github.com/user-attachments/assets/316add7b-4352-4b44-bf71-bd786d72938b
    *  
    *  (![изображение](https://github.com/user-attachments/assets/dc650f41-927c-423f-961c-0d1f811d65f6)
    *  It can completely understand the context of conversation:
    *   (![изображение](https://github.com/user-attachments/assets/6555d968-606a-43d1-bd8b-be900844cc48)

* **Roadmap:**
* 
We have exciting plans for the future of AsylBILIM, constantly striving to enhance its intelligence and utility for Kazakh students. Here are some key features and improvements we're actively working on or planning:

* **Implementing a RAG (Retrieval Augmented Generation) System:** Our top priority is to integrate a robust RAG system. This will enable AsylBILIM to retrieve information from a curated knowledge base (e.g., educational materials, textbooks, exam guidelines specific to Kazakhstan) before generating responses. This ensures that the bot provides the most **relevant, accurate, and concise** answers, significantly reducing hallucinations and improving the factual correctness of information, especially for academic queries.

* **Acknowledgements:**
    * This bot can make mistakes, please double-check responses. 

---
