# TAP Voice Re-Engagement Platform (MVP)

AI-powered multilingual voice engagement platform for re-engaging inactive students using conversational voice agents.

Built using:
- FastAPI
- VAPI
- RabbitMQ
- Deepgram STT
- Azure Speech TTS
- GPT-4o-mini

---

# Overview

Student drop-off after onboarding is one of the biggest challenges in large-scale government learning deployments.

This project implements an MVP for an AI-powered multilingual voice engagement platform that proactively interacts with inactive students and parents through conversational voice sessions.

The system:
- detects inactive students,
- personalizes engagement conversations,
- supports multilingual voice interactions,
- enables scalable async campaign orchestration.

---

# Features

## Voice Engagement
- AI-powered conversational voice sessions
- Personalized student interactions
- Browser-based voice testing
- VAPI voice orchestration

## Multilingual Support
- Hindi
- Marathi
- Punjabi
- English

## Backend Infrastructure
- FastAPI orchestration backend
- RabbitMQ async queue support
- Worker-ready architecture
- Modular service design

## Data Layer
- Dummy student dataset support
- Optional Frappe LMS integration
- Fallback data loading strategy

## Analytics
- Call/session logging
- Engagement tracking foundations
- Retry/escalation workflow foundations

---
