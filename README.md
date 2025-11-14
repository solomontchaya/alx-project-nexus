# 🎓 **Project Nexus – Student Project Voting Platform Documentation**

This repository documents my backend engineering journey through the **ProDev Backend Engineering Program**, using a practical real-world project:
a **Student Project Voting Platform**.

The platform allows **student teams** to submit projects and **individual users** to vote once per project. This documentation showcases the concepts, tools, and best practices I learned while designing and building the backend for this system.

---

# 🧩 **Table of Contents**

1. [About the Program](#about-the-program)
2. [Project Overview](#project-overview)
3. [Technologies Used](#technologies-used)
4. [Backend Concepts Applied](#backend-concepts-applied)
5. [System Architecture](#system-architecture)
6. [Database Design](#database-design)
7. [API Endpoints Overview](#api-endpoints-overview)
8. [Challenges & Solutions](#challenges--solutions)
9. [Best Practices Followed](#best-practices-followed)
10. [Personal Takeaways](#personal-takeaways)
11. [Collaboration Notes](#collaboration-notes)

---

# 📚 **About the Program**

The **ProDev Backend Engineering Program** is designed to build strong foundations in backend development, covering APIs, databases, authentication, DevOps, and modern engineering tools.
This repository serves as my documentation hub, summarizing all the key learnings applied in building a real backend system.

---

# 🚀 **Project Overview – Student Project Voting Platform**

This platform enables:

### 👥 **Teams to:**

* Register and create team profiles
* Submit their project (title, description, media, etc.)

### 🧑‍🎓 **Students/Users to:**

* Sign up with email & password
* Log in to access the voting interface
* View all projects
* Cast **one vote per project**

### 📊 **Voting Rules:**

* A user can vote for multiple *different* projects
* But cannot vote for the **same project twice**
* Projects display vote counts in real-time

This project demonstrates core backend engineering skills such as user authentication, relational database modeling, and API development.

---

# 🛠️ **Technologies Used**

### **Languages & Frameworks**

* Python
* Django
* Django REST Framework (DRF)

### **Database**

* PostgreSQL or SQLite (dev)
* Django ORM

### **DevOps & Tools**

* Docker
* GitHub Actions (CI/CD)
* Environment variables (`.env`)
* Swagger / DRF-YASG for API documentation

---

# 🧠 **Backend Concepts Applied**

### **1. User Authentication**

* User registration & login
* Token-based authentication (JWT or DRF tokens)
* Secure password hashing

### **2. Role Management**

* Regular users (students)
* Team owners
* Admin (optional)

### **3. Project Submission**

* CRUD operations for project entries
* Media upload support (optional)

### **4. Voting Logic**

* One vote per user per project
* Prevent double-voting
* Efficient vote counting (annotate queries)

### **5. Database Relationships**

* One Team → Many Projects
* One User → Many Votes
* One Vote → Links User + Project

### **6. API Development**

* Serializers
* Permissions
* Validations
* Custom actions (e.g., `/projects/<id>/vote/`)

### **7. Deployment Concepts**

* Dockerizing the application
* Running migrations in containers
* Managing `.env` settings securely

---

# 🏗️ **System Architecture**

### **Backend Architecture Summary**

* **Django** handles authentication & API logic
* **DRF** exposes RESTful endpoints
* **Database** stores users, teams, projects, and votes
* **Permissions** ensure correct access control
* **Business logic** prevents multiple votes

A simple and clean backend architecture suitable for a student voting system.

---

# 🗄️ **Database Design**

### **Entities**

#### **User**

* id
* email
* password
* is_team_owner?
* created_at

#### **Team**

* id
* name
* members (optional)
* owner (User)

#### **Project**

* id
* team (FK)
* title
* description
* media_url (optional)
* created_at

#### **Vote**

* id
* user (FK)
* project (FK)
* timestamp
* **Unique constraint:** `(user, project)`

This ensures a single user cannot vote twice for the same project.

---

# 🔌 **API Endpoints Overview**

### **Authentication**

```
POST /auth/register/
POST /auth/login/
```

### **Teams**

```
GET  /teams/
POST /teams/             (team owner)
GET  /teams/<id>/
```

### **Projects**

```
GET  /projects/
POST /projects/          (team owner)
GET  /projects/<id>/
PATCH/PUT /projects/<id>/  (team owner)
```

### **Voting**

```
POST /projects/<id>/vote/
GET  /projects/<id>/votes/
```

---

# 🚧 **Challenges & Solutions**

### **1. Preventing Double Voting**

**Challenge:** Users could attempt to vote multiple times.
**Solution:**

* Added a **unique constraint** on the Vote model (`user`, `project`)
* Implemented custom validation in the vote endpoint

### **2. Designing Efficient Vote Counting**

**Challenge:** Counting votes on each request was slow.
**Solution:**

* Used Django ORM `.annotate(Count("votes"))` for efficient aggregation

### **3. Authentication Flow**

**Challenge:** Handling login & JWT correctly.
**Solution:**

* Used DRF SimpleJWT
* Added custom response payload with user info

### **4. API Permissions**

**Challenge:** Preventing non-team-owners from uploading projects.
**Solution:**

* Implemented custom DRF permissions:
  `IsTeamOwnerOrReadOnly`

---

# 🌟 **Best Practices Followed**

* Clean and modular Django project structure
* Consistent use of environment variables
* Clear API documentation
* Meaningful commit messages
* Proper use of `.gitignore`
* Database normalization
* Limited business logic inside views (moved to services)
* Secure password handling

---

# 💡 **Personal Takeaways**

* API development is easier with a clean database design
* Permissions and authentication are central to any real application
* Understanding relationships helps avoid future scaling issues
* Communication with frontend developers is key
* Good documentation saves time for everyone
* Thinking in systems, not just code, is important

---

# 🤝 **Collaboration Notes**

You should collaborate with:

### **Backend Learners**

* Compare models
* Discuss endpoint logic
* Review each other’s vote logic

### **Frontend Learners**

* They need your API endpoints to display projects and process votes
* Agree on response formats and endpoints early

### **Discord Channel**

**`#ProDevProjectNexus`**
Share progress, ask questions, and coordinate teams.

---

# 📦 **Repository Structure**

```
alx-project-nexus/
│
└── README.md   # Documentation hub for Student Project Voting Platform
```

---
