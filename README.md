# lxmon - System Monitoring Platform

A comprehensive system monitoring solution with agent-based data collection, real-time dashboards, and command execution capabilities.

## 🏗️ Architecture

### Components

- **lxmon-agent**: Lightweight Go binary for system metrics collection
- **lxmon-server**: FastAPI backend with PostgreSQL and Redis
- **lxmon-dashboard**: React frontend with real-time monitoring

### Features

- ✅ Real-time system metrics (CPU, RAM, Disk, Network)
- ✅ Agent heartbeat monitoring
- ✅ Remote command execution
- ✅ Alert system with customizable rules
- ✅ Multi-tenant architecture
- ✅ RESTful API with OpenAPI documentation
- ✅ Modern React dashboard with Tailwind CSS

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Go 1.21+ (for agent development)
- Node.js 18+ (for dashboard development)

### 1. Clone and Setup

```bash
git clone <your-repo-url>
cd lxmon
cp .env.example .env
```

### 2. Start All Services

```bash
docker-compose up -d
```

This will start:
- PostgreSQL database
- Redis cache/queue
- FastAPI backend (port 8000)
- React dashboard (port 3000)

### 3. Access the Dashboard

Open http://localhost:3000 in your browser.

### 4. Default Credentials

Create a user account through the registration form, or use the API directly:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "email": "admin@example.com", "password": "password"}'
```

## 📦 Project Structure

```
lxmon/
├── lxmon-server/          # FastAPI backend
│   ├── main.py           # Application entry point
│   ├── core/             # Core functionality
│   ├── models/           # Database models
│   ├── routers/          # API endpoints
│   ├── database/         # Redis client
│   └── requirements.txt
├── lxmon-agent/          # Go monitoring agent
│   ├── main.go          # Agent implementation
│   └── Dockerfile
├── lxmon-dashboard/      # React frontend
│   ├── src/
│   │   ├── components/  # Reusable components
│   │   ├── pages/       # Page components
│   │   ├── services/    # API services
│   │   └── contexts/    # React contexts
│   └── Dockerfile
├── docker-compose.yml    # Orchestration
├── .env.example         # Environment template
└── README.md
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Backend
DEBUG=false
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://lxmon:lxmon@localhost:5432/lxmon
REDIS_URL=redis://localhost:6379
AGENT_API_KEYS=agent-key-1,agent-key-2

# Agent
LXMON_SERVER_URL=http://localhost:8000
LXMON_API_KEY=agent-key-1
LXMON_INTERVAL=60

# Dashboard
VITE_API_URL=http://localhost:8000
```

## 🏃‍♂️ Development

### Backend Development

```bash
cd lxmon-server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

API documentation: http://localhost:8000/docs

### Agent Development

```bash
cd lxmon-agent
go run main.go
```

### Dashboard Development

```bash
cd lxmon-dashboard
npm install
npm run dev
```

## � API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Get current user

### Servers
- `GET /api/servers` - List servers
- `GET /api/servers/{id}` - Get server details
- `POST /api/servers` - Create server
- `PUT /api/servers/{id}` - Update server
- `DELETE /api/servers/{id}` - Delete server
- `GET /api/servers/{id}/metrics` - Get server metrics
- `POST /api/servers/{id}/command` - Send command
- `GET /api/servers/{id}/commands` - Get command history

### Agent Endpoints
- `POST /api/agent/register` - Agent registration
- `POST /api/agent/heartbeat` - Agent heartbeat
- `POST /api/agent/metrics` - Submit metrics
- `GET /api/agent/commands` - Get pending commands
- `POST /api/agent/command-result` - Submit command result

### Alerts
- `GET /api/alerts/rules` - List alert rules
- `POST /api/alerts/rules` - Create alert rule
- `PUT /api/alerts/rules/{id}` - Update alert rule
- `DELETE /api/alerts/rules/{id}` - Delete alert rule
- `GET /api/alerts` - List alerts
- `PUT /api/alerts/{id}/resolve` - Resolve alert

## 🔐 Security

- JWT-based authentication for dashboard users
- API key authentication for agents
- Command whitelisting for security
- CORS protection
- Input validation and sanitization

## 📈 Monitoring & Metrics

The system collects:
- CPU usage percentage
- Memory usage (total, used, percentage)
- Disk usage by mount point
- Network I/O (bytes sent/received)
- System uptime
- Host information

## 🚀 Deployment

### Production Deployment

1. Update environment variables in `.env`
2. Use production Docker Compose:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes Deployment

Apply the Kubernetes manifests:

```bash
kubectl apply -f k8s/
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## � License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Common Issues

1. **Database connection failed**
   - Ensure PostgreSQL is running
   - Check DATABASE_URL in environment variables

2. **Redis connection failed**
   - Ensure Redis is running
   - Check REDIS_URL in environment variables

3. **Agent cannot connect**
   - Verify LXMON_SERVER_URL
   - Check API key is in AGENT_API_KEYS list

4. **Dashboard not loading**
   - Ensure backend is running on port 8000
   - Check VITE_API_URL configuration

### Logs

View service logs:
```bash
docker-compose logs lxmon-server
docker-compose logs lxmon-dashboard
docker-compose logs postgres
docker-compose logs redis
```

## � Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Go Documentation](https://golang.org/doc/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
