# 📰 NewsIQ — AI-Powered News Intelligence

**Stay curious. Stay informed.**

NewsIQ is an AI-powered news platform that brings live news, article summaries, AI question-answering, and personalized reading into one dashboard. It also demonstrates cloud-native deployment using Docker and Kubernetes.

## ✨ Features

- 📰 Live news feeds across multiple categories
- 🤖 AI-generated article summaries
- 💬 Ask AI questions about articles
- 📅 AI Daily Briefing
- 🔐 User registration and login
- 🔖 Saved articles with PostgreSQL storage
- 🕒 Recently viewed articles
- 🐳 Docker containerization and Docker Compose
- ☸️ Kubernetes Deployments, Services, and persistent storage

## 🛠️ Tech Stack

| Component | Technologies |
|---|---|
| Frontend | React, Vite, CSS |
| Backend | Python, FastAPI |
| Database | PostgreSQL, SQLAlchemy |
| AI | Groq API |
| News | RSS feeds |
| DevOps | Docker, Docker Compose, Kubernetes, Minikube |

## 🏗️ Architecture

```text
User
  ↓
React Frontend
  ↓
FastAPI Backend
  ├── RSS News Feeds
  ├── Groq AI API
  └── PostgreSQL Database

Deployment: Docker + Kubernetes
```

## 🚀 Run Locally

**1. Clone the repository**

```bash
git clone YOUR_REPOSITORY_URL
cd NewsIQ
```

**2. Start the backend**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8011
```

Configure the required environment variables in `backend/.env` before starting the backend.

**3. Start the frontend** in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## 🐳 Docker

From the project root:

```bash
docker compose up -d --build
docker compose ps
```

Stop the containers with:

```bash
docker compose down
```

## ☸️ Kubernetes

With Minikube running and the required images, Secrets, ConfigMaps, and manifests configured:

```bash
kubectl apply -f k8s/
kubectl get pods
kubectl get deployments
kubectl get services
kubectl get pvc
```

## 🔐 Security

- Keep API keys, passwords, and `.env` files out of GitHub.
- Use environment variables and Kubernetes Secrets for sensitive configuration.
- Never commit real credentials.

## 🎯 Project Objective

To develop an AI-powered news application while demonstrating REST API development, database integration, containerization, Kubernetes orchestration, and persistent storage.

## 🔮 Future Scope

- Public cloud deployment
- CI/CD with GitHub Actions
- Autoscaling and monitoring
- Improved personalized recommendations

---
Made By Legendary Duo Mr.Suhan Poojary & Ms.Ishjyot Kaur