# Sprint 0 — Environment Setup

**Goal:** All tools and accounts ready before writing any code.
**Status:** Done
**Time estimate:** ~10 hours

---

## What Was Set Up

### Tools Installed (on your Mac)

| Tool | Version | Verify Command |
|------|---------|---------------|
| Python | 3.14.x | `python3 --version` |
| pip | latest | `pip --version` |
| Docker Desktop | 29.x | `docker --version` |
| Docker Compose | v5.x | `docker compose version` |
| Git | 2.x | `git --version` |
| VS Code | latest | `code --version` |

### Python Virtual Environment

```
Location : nearkart_backend/venv/
Activate : source venv/bin/activate
Packages : requirements/development.txt
```

### Accounts Needed

| Service | Purpose | Sprint Used |
|---------|---------|-------------|
| GitHub | Code repository | All sprints |
| AWS | S3 storage, hosting | S4, S12 |
| Firebase | Push notifications (FCM) | S5, S9 |
| Twilio | SMS OTP delivery | S2 |
| SendGrid | Email notifications | S6 |
| Google Cloud | Maps APIs | S3 |
| Sentry | Error monitoring | S1 |

> For Sprints 1-3 (current work), only GitHub is required.
> AWS/Firebase/Twilio can use dummy values in .env during development.

---

## Checklist

- [x] Python 3.14 installed
- [x] Docker Desktop installed and running
- [x] Git installed and configured
- [x] GitHub repo created (nearkart-backend)
- [x] Virtual environment created at `venv/`
- [x] `.env` file created from `.env.example`
- [ ] AWS account (needed for Sprint 4 - Video)
- [ ] Firebase project (needed for Sprint 5 - Chat)
- [ ] Twilio account (needed for Sprint 2 - real SMS)
- [ ] Google Maps API key (needed for Sprint 3 - Geo)
- [ ] Sentry project (needed for production)
