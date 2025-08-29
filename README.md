# 🏗️ lxmon – System Architecture

## 1. **Components**

### **lxmon-agent**

* Lightweight binary (Go / Rust / Python) installed on each server.
* Responsibilities:

  * Collect system metrics (CPU, RAM, Disk, Network, service status).
  * (Optional) Forward logs.
  * Receive and execute commands from `lxmon-server`.
* Works in **pull model** → sends regular **heartbeats** and checks for new commands.

### **lxmon-server (API & Backend)**

* Built with FastAPI / Django / Go + gRPC (for performance).
* Responsibilities:

  * API layer: agents and dashboard connect here.
  * Authentication & security (JWT / API Key / OAuth).
  * Command queue management.
  * Store agent metrics in the database.
  * Multi-tenant isolation in SaaS mode.

### **Dashboard (Frontend)**

* React + Tailwind (using `shadcn/ui` for a modern panel).
* Responsibilities:

  * Server list, metrics, health checks.
  * Command execution (e.g., restart nginx).
  * Alerts & notifications (email, Slack, webhook).

### **Database**

* PostgreSQL (multi-tenant capable).
* Redis (command queue + cache).
* Time-series: InfluxDB or PostgreSQL Timescale.

### **Message Broker (Optional)**

* RabbitMQ / Kafka → required only at large SaaS scale.
* For MVP: PostgreSQL + Redis are sufficient.

---

## 2. **API Layer**

### 🔐 Authentication

* Agent → API Key (unique per agent).
* Dashboard user → JWT session.
* SaaS model → `tenant_id` separation.

### 🔄 API Endpoints

#### Agent → Server

* `POST /api/agent/register` → Agent registration.
* `POST /api/agent/metrics` → Push metrics (CPU, RAM, Disk, etc.).
* `GET /api/agent/commands` → Fetch pending commands.
* `POST /api/agent/command-result` → Report command results.

#### Dashboard → Server

* `GET /api/servers` → List servers.
* `GET /api/servers/{id}/metrics` → Fetch server metrics.
* `POST /api/servers/{id}/command` → Send command.
* `GET /api/commands/{id}/status` → Command result.
* `POST /api/alerts` → Create alert rules.

---

## 3. **Command Execution Flow**

1. User selects **“Restart Nginx”** from dashboard.
2. `POST /api/servers/{id}/command` → stored in DB (status: pending).
3. Agent calls `GET /api/agent/commands` → sees pending command.
4. Agent executes the command → sends result via `POST /api/agent/command-result`.
5. Dashboard updates → shows live result (`exit 0, success`).

---

## 4. **Agent Structure**

* **Core**: Go binary (portable, single file), runs as systemd service.
* **Metric Collector**: Reads `/proc`, `psutil`, `systemd DBus`.
* **Command Executor**: Uses `subprocess` to run shell commands.

  * Whitelist / plugin system (only allowed commands).
* **Transport**: Secure HTTPS (TLS).

  * Each request signed with JWT / API Key.

---

## 5. **SaaS Architecture**

* **Multi-Tenant**:

  * Single DB → `tenant_id` column separation.
  * Or separate schemas per tenant.
* **Deployment**:

  * API + DB → Kubernetes (for scaling).
  * Agent → lightweight binary, supports self-update.
* **Billing**:

  * Based on number of agents + data retention period (Datadog-style).

---

## 6. **MVP Roadmap**

### 🟢 Phase 1 – MVP

* Agent (Go/Python) → sends CPU/RAM/Disk.
* Server (FastAPI) → stores in DB.
* Dashboard (React) → server list + metric charts.

### 🟡 Phase 2 – Command System

* Command queue (Postgres + Redis).
* Send commands from dashboard.
* Agent executes commands and reports results.

### 🔴 Phase 3 – SaaS Readiness

* Multi-tenant support.
* Billing & subscriptions.
* Scaling (K8s, load balancer).

---

## 7. **Future Features**

* Log forwarding (similar to Datadog Logs).
* Alerting (thresholds, anomaly detection).
* Plugin system (e.g., MySQL monitoring, Nginx log analysis).
* Mobile app (push notifications for alerts).

---

## 📌 Summary

* **Agent** → heartbeat + metrics + command executor.
* **API** → command queue + metrics DB + authentication.
* **Dashboard** → visualization + command execution.
* **SaaS** → multi-tenant, billing, scaling.
