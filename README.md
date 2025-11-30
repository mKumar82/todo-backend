🖥 Todo App API — FastAPI

A fully functional backend API built using FastAPI, SQLModel, and JWT Authentication.
Designed specifically for the Todo Mobile App.

⸻

🚀 Features

🔐 Authentication
	•	Signup
	•	Login
	•	JWT Token generation
	•	Protected routes with OAuth2

📝 Todo Management
	•	Create Todo
	•	List Todos
	•	Update Todo
	•	Toggle Completion
	•	Delete Todo

👤 User Profile
	•	Fetch authenticated user details

⸻

🛠 Tech Stack
	•	FastAPI
	•	SQLModel
	•	SQLite
	•	JWT (python-jose)
	•	Passlib (bcrypt hashing)
	•	Uvicorn

📂 Project Structure

backend/
 ├── main.py
 ├── todo.db (auto-generated)
 ├── requirements.txt
 └── README.md

 🔧 Setup & Installation

1️⃣ Create virtual environment
python3 -m venv todoenv
source todoenv/bin/activate   # macOS/Linux
todoenv\Scripts\activate      # Windows

2️⃣ Install dependencies
pip install -r requirements.txt

3️⃣ Start server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

🧪 Testing (Postman)

Import these endpoints:
	•	POST /auth/signup
	•	POST /auth/login
	•	GET /users/me
	•	POST /todos
	•	GET /todos
	•	DELETE /todos/{id}

⸻

📄 License

MIT License