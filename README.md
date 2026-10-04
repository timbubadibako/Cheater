# ⚡ Cheater

<div align="center">

**High-Performance Multi-Service Subscription & Promo Hunter Engine**

*Automated virtual SMS rental, OTP validation, and promotional reward harvest with real-time CLI & Web dashboard.*

[![Python](https://img.shields.io/badge/python-3.9+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![CLI](https://img.shields.io/badge/CLI-Typer%20%2B%20Rich-red.svg?style=flat)](https://github.com/fastapi/typer)
[![Architecture](https://img.shields.io/badge/architecture-Modular%20Providers-brightgreen.svg?style=flat)](#-architecture--design)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat)](LICENSE)

</div>

---

## 📌 Overview

**Cheater** (powered by `jiofarm` core engine) is an automation platform designed to programmatically provision virtual phone numbers, intercept verification codes (OTP), authenticate against service endpoints, and claim promotional benefit links (such as Google AI Pro / Gemini Pro subscriptions).

Built with modularity, zero bloat, and resilient fault-tolerance, it features live concurrency, multi-provider abstraction, automatic non-delivery refunds, rotating proxy routing, and dual-interface telemetry (Terminal UI & Web Dashboard).

---

## ✨ Features

- **Multi-Service Architecture**: Pluggable service registry (`jio`, `airtel`, `canva`, and expandable custom services).
- **Multi-SMS Provider Fallback**: Seamless integration across major SMS rental APIs:
  - **SMS-Man** (API v2.0)
  - **Grizzly SMS** (with auto-refund monitor)
  - **5SIM**
  - **SMSPool**
- **Automated Lifecycle & Financial Safeguards**:
  - Auto-cancels and refunds numbers that do not receive OTP within configured SLAs.
  - Rate-limit & backoff management.
  - Price ceiling guards (`MAX_PRICE`) preventing unexpected balance drain.
- **Dual Telemetry Interfaces**:
  - **Terminal TUI**: Real-time worker matrix with progress indicators using Rich.
  - **Web Dashboard**: Embedded local web control center for headless and remote monitoring.
- **Network Resilience & Anti-Detect**:
  - Built-in DNS-over-HTTPS (DoH) resolver bypass.
  - Rotating residential/datacenter HTTP(S) proxy pool support.
- **Real-Time Alerts & Persistence**:
  - SQLite local audit log (`results.db`).
  - Instant Telegram bot dispatch upon successful link discovery.

---

## 🏗️ Architecture & Project Structure

```text
cheater/
├── .env.example            # Environment variables template
├── .gitignore              # Sensitive data and artifact exclusion
├── pyproject.toml          # Packaging configuration
├── requirements.txt        # Runtime dependencies
├── README.md               # Project documentation
└── jiofarm/                # Core hunter package
    ├── cli.py              # Typer command-line interface & TUI
    ├── config.py           # Typed environment configurations
    ├── console.py          # Shared rich console instance
    ├── engine.py           # Core concurrent orchestration engine
    ├── hunter.py           # Worker state machine & phases
    ├── proxy.py            # Proxy pool & rotation handler
    ├── shield.py           # Anti-censorship & DoH network protection
    ├── fivesim/            # 5SIM provider client
    ├── grizzly/            # GrizzlySMS client & refund daemon
    ├── smsman/             # SMS-Man provider client
    ├── smspool/            # SMSPool provider client
    ├── services/           # Service subscription scrapers & validators
    │   ├── base.py         # Abstract base service interface
    │   ├── jio.py          # Jio Selfcare & Google AI Pro hunter
    │   ├── airtel.py       # Airtel reward collector
    │   ├── canva.py        # Canva team/promo handler
    │   └── registry.py     # Service locator registry
    ├── storage/            # SQLite persistence store
    └── web/                # Local web dashboard UI & HTTP server
```

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.9 or higher
- Git

### 2. Installation

Clone this repository and set up a virtual environment:

```bash
git clone https://github.com/timbubadibako/Cheater.git
cd Cheater

# Create virtual environment
python -m venv .venv

# Activate environment (Linux/macOS)
source .venv/bin/activate
# Or on Windows (PowerShell/CMD):
# .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Install as local CLI command:
pip install -e .
```

### 3. Configuration

Copy the example configuration file and fill in your API tokens:

```bash
cp .env.example .env
```

Edit `.env` with your preferred settings:

```ini
# Provider Selection: smsman | grizzlysms | fivesim | smspool
PROVIDER=smsman

# Provider Credentials
SMSMAN_API_KEY=your_smsman_token
SMSMAN_COUNTRY_ID=22
SMSMAN_APPLICATION_ID=jio

# Price & Timeout Safeguards
MAX_PRICE=0.5
CANCEL_DELAY_SECONDS=150
OTP_FAIL_DELAY_SECONDS=420
CONCURRENCY=2

# Persistence & Storage
DB_PATH=results.db

# Optional Notifications
# TG_BOT_TOKEN=123456789:ABCdefGHIjklMNO
# TG_CHAT_ID=-100123456789

# Optional Proxies (Comma-separated or single proxy URL)
# PROXY_URL=http://user:pass@proxy.example.com:8080
```

---

## 💻 Usage

### Check Provider Balance

Quickly verify your account credentials and remaining funds:

```bash
python -m jiofarm balance
# or if installed:
jiofarm balance
```

### Run Hunter (Live Terminal UI)

Start hunting with real-time concurrency:

```bash
# Continuous run with default concurrency
python -m jiofarm run

# Limit total numbers rented
python -m jiofarm run --count 10

# Set maximum runtime duration
python -m jiofarm run --duration 1h30m
```

### Inspect Harvested Links

Query links stored in SQLite:

```bash
# Print to console
python -m jiofarm links

# Export to text file
python -m jiofarm links --out links.txt
```

### View Performance Statistics

```bash
python -m jiofarm stats
```

### Launch Web Dashboard

```bash
python -m jiofarm web --host 127.0.0.1 --port 8080
```

---

## 🔒 Security & Best Practices

- **Never commit `.env` or `results.db`**: Credentials and generated links contain sensitive personal or billing tokens.
- **Proxy Hygiene**: When running high concurrency, always utilize residential HTTP/HTTPS proxies to prevent IP blocks from telecom endpoints.
- **Graceful Termination**: Use `Ctrl+C` to cleanly exit. The worker will release leased numbers and attempt immediate refund requests for pending orders.

---

## ⚖️ Disclaimer

This project is created strictly for educational and research purposes. Automated interaction with third-party APIs and service providers must comply with their respective Terms of Service and acceptable use policies. The authors assume no liability for misuse, account suspension, or financial losses incurred through SMS provider services.

---

## 📄 License

Distributed under the [MIT License](LICENSE).
