# Architecture – NEIL Solar AMC SaaS

## Overview
NEIL Solar is a multi-tenant SaaS platform for Solar EPC companies in India to run AMC (Annual Maintenance Contract) visits.

Core flow:
1) Supervisor schedules AMC visit (WorkOrder) and assigns Technician
2) Technician completes checklist + captures photos (max 20) + signs
3) Backend generates PDF report and sends approval link to customer site supervisor
4) Customer site supervisor signs via mobile web link
5) Final signed PDF is stored and visible to Owner/Supervisor/Customer portal

## Tech Stack
- UI: FlutterFlow (Technician mobile app + Owner/Supervisor web portal)
- Customer signing: Mobile web approval link (no app required)
- Auth: Firebase Auth (JWT)
- API: FastAPI on Cloud Run
- DB: Cloud SQL Postgres (managed)
- Media/PDF: Google Cloud Storage (GCS)
- Async: Cloud Run Jobs and stateless worker paths (report jobs, notification jobs, retention cleanup)
- IaC: Terraform
- Region: asia-south1 (Mumbai)

## Environments (single GCP project, MVP branch strategy)
Branch → Environment → Cloud Run service
- develop → dev → neilsolar-dev-api
- main → prod → neilsolar-prod-api

Each env has its own:
- Cloud Run service
- Cloud SQL instance
- GCS buckets (media + reports)
- service accounts
- secrets

## High-level Architecture (Mermaid)

```mermaid
flowchart LR
  subgraph Clients
    T[Technician App (FlutterFlow)]
    S[Supervisor/Owner Web (FlutterFlow)]
    C[Customer Supervisor\nMobile Web Approval Link]
  end

  subgraph Firebase
    FA[Firebase Auth]
  end

  subgraph GCP
    subgraph CloudRun
      API[FastAPI API Service]
      JOB[Worker Job\n(PDF/Notification/Retention)]
    end

    subgraph DB
      PG[(Cloud SQL Postgres)]
    end

    subgraph Storage
      MEDIA[(GCS Media Bucket)]
      REPORTS[(GCS Reports Bucket)]
    end
  end

  T -->|Firebase JWT| API
  S -->|Firebase JWT| API
  C -->|Token Link| API

  API --> PG
  API --> MEDIA
  API --> REPORTS
  API --> JOB

  JOB --> PG
  JOB --> MEDIA
  JOB --> REPORTS
