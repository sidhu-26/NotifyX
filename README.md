# 🚀 NotifyX — Scalable, Fault-Tolerant Notification System

A production-grade, event-driven notification system built with **Django, Celery, and Redis**, designed to handle real-world challenges like retries, duplicate events, failures, and traffic spikes.

---

# 🧠 Problem Statement

Modern applications (e-commerce, fintech, booking platforms) rely heavily on notifications.
However, most systems fail in production due to:

* ❌ Duplicate notifications
* ❌ Lost messages during failures
* ❌ Delayed delivery under high load
* ❌ Tight coupling between API and notification logic

---

# 🎯 Solution

NotifyX solves these problems by implementing a:

> **Scalable, event-driven, asynchronous notification pipeline with reliability guarantees**

---

# 🏗️ Architecture Overview

```text
Client / Webhook
        ↓
Django API (Event Producer)
        ↓
Event Layer (create_event)
        ↓
Celery Queue (Redis Broker)
        ↓
Worker Pool (Priority-based)
        ↓
Notification Processor
        ↓
Channel Handlers (Email / Future: SMS, Push)
        ↓
Database (Notification + DLQ)
```

---

# ⚙️ Tech Stack

* **Backend:** Django + Django REST Framework
* **Async Processing:** Celery
* **Message Broker:** Redis
* **Database:** PostgreSQL
* **Email Service:** SMTP (Gmail)
* **Queue Monitoring:** Celery Events (`-E`)

---

# 🔥 Key Features

---

## ⚡ Event-Driven Architecture

* Decouples business logic from notification delivery
* Webhooks → Events → Queue → Worker

---

## 🔄 Asynchronous Processing

* Non-blocking API responses
* Background workers handle heavy tasks

---

## 🔁 Retry Mechanism (Exponential Backoff)

```text
Retry Pattern:
1s → 2s → 4s → 8s → 16s → 32s
```

* Automatic retries on failure
* Prevents system overload

---

## 🛡️ Idempotency (Duplicate Protection)

* Each notification has a unique `idempotency_key`
* Ensures:

  * No duplicate emails
  * Safe retries
  * Consistent system state

---

## 🎯 Priority Queueing

```text
HIGH PRIORITY → payment events
LOW PRIORITY  → background notifications
```

* Prevents critical tasks from being delayed
* Dedicated workers per queue

---

## 💀 Dead Letter Queue (DLQ)

* Stores permanently failed events
* Includes:

  * payload
  * user_id
  * error message

---

### 🔁 DLQ Recovery

* Failed events can be reprocessed manually
* Enables debugging + system recovery

---

## 🚦 Rate Limiting (Redis-based)

```text
Max 5 notifications / user / minute
```

* Prevents spam
* Protects infrastructure

---

## 📡 Observability & Logging

* Structured logs for:

  * event ingestion
  * retries
  * failures
  * DLQ insertion

---

## 📬 Channel Abstraction

```text
EmailChannel → implemented
SMSChannel   → pluggable
PushChannel  → pluggable
```

* Easily extendable multi-channel system

---

# 🧩 Data Models

---

## Notification

```text
user
event_type
status (PENDING, PROCESSING, SENT, FAILED)
retry_count
idempotency_key (unique)
payload
```

---

## DeadLetterQueue

```text
event_type
user_id
payload
error_message
created_at
```

---

# 🔄 End-to-End Flow

---

## ✅ Successful Flow

```text
1. User places order
2. Payment webhook received
3. Event created
4. Event pushed to Redis queue
5. Celery worker processes event
6. Notification created
7. Email sent
8. Status updated → SENT
```

---

## ❌ Failure Flow

```text
1. Event fails
2. Retry triggered
3. Exponential backoff applied
4. Max retries reached
5. Event moved to DLQ
```

---

# 🧪 How to Run

---

## 1. Start Redis

```bash
redis-server
```

---

## 2. Run Django Server

```bash
python manage.py runserver
```

---

## 3. Start Celery Workers

### High Priority Worker

```bash
celery -A notifyx worker -Q high_priority -l info --pool=solo
```

---

### Low Priority Worker

```bash
celery -A notifyx worker -Q low_priority,default -l info --pool=solo
```

---

### Optional (Enable Monitoring)

```bash
celery -A notifyx worker -E -l info
```

---

# 🧪 Demo Flow

---

## 1. Create Order

```bash
POST /api/orders/
```

---

## 2. Trigger Webhook

```bash
POST /api/payments/webhook/
```

---

## 3. Observe:

* Event queued
* Worker processes task
* Notification created
* Email sent

---

## 4. Simulate Failure

* Trigger failure inside task
* Observe retries
* Check DLQ entry

---

## 5. Recover from DLQ

* Use `retry_dlq_event(dlq_id)`
* Event reprocessed

---

# 🧠 System Design Highlights

---

## ✔️ Decoupled Architecture

* API does NOT handle notification logic

---

## ✔️ Fault Tolerance

* Retry + DLQ ensures no data loss

---

## ✔️ Scalability

* Horizontal worker scaling
* Queue-based load handling

---

## ✔️ Consistency

* Idempotency guarantees no duplicates

---

## ✔️ Extensibility

* Plug-and-play channel system

---

# 📈 Future Enhancements

* Multi-channel delivery (SMS, Push)
* Notification preferences per user
* Scheduled notifications
* Batching system
* Metrics dashboard (success/failure rates)

---

# 🎯 Key Takeaways

---

> This project demonstrates how to design a **real-world scalable backend system**, not just CRUD APIs.

It focuses on:

* reliability
* system design
* failure handling
* asynchronous processing

---

# 👨‍💻 Author

Built as part of a backend system design journey focused on real-world scalability and fault tolerance.

---

⭐ If you found this useful, feel free to star the repo!
