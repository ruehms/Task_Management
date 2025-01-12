# Flask
# Flask Task Management App with Docker

This project is a **Flask-based Task Management and Report Subscription System**. It allows users to manage tasks, subscribe to automated reports, and receive scheduled email summaries.

## **Features**

- User authentication (Sign Up, Sign In)
- Create, update, and delete tasks
- Batch task deletion and undo delete
- Email subscriptions with daily/weekly/monthly task reports
- PostgreSQL database with Docker integration
- Automatic job scheduling using APScheduler

---

## **Project Structure**

/pythonProject 
├── app.py # Main Flask application 
├── Dockerfile # Docker configuration for Flask app 
├── docker-compose.yml # Docker Compose configuration 
├── requirements.txt # Python dependencies 
└── README.md # Project documentation

---

## **Getting Started**

### **Prerequisites**
Make sure you have the following installed:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- GitHub account

---

### **Installation Steps**

1. Clone this repository:
   ```bash
   git clone https://github.com/ruehms/Task_Management.git
   cd Flask

   docker-compose build #Build and run the Docker containers:

   docker-compose up



3. Access the app in your browser:
    http://127.0.0.1:5001


## **Endpoints**

### **User Authentication**
| Method | Endpoint   | Description  |
|--------|------------|--------------|
| `POST` | `/signup`  | Register a new user |
| `POST` | `/signin`  | User login (returns JWT token) |

### **Task Management**
| Method  | Endpoint       | Description          |
|---------|----------------|---------------------|
| `POST`  | `/tasks`        | Create a new task    |
| `GET`   | `/tasks`        | Get all tasks        |
| `PUT`   | `/tasks/<id>`   | Update a task by ID  |
| `DELETE`| `/tasks/<id>`   | Delete a task by ID  |

### **Subscription Management**
| Method  | Endpoint         | Description                       |
|---------|------------------|------------------------------------|
| `POST`  | `/subscribe`      | Subscribe to automated reports     |
| `DELETE`| `/unsubscribe`    | Unsubscribe from automated reports |

---

### **Request Body for Subscribe (`POST /subscribe`)**

```json
{
  "start_date": "YYYY-MM-DD",
  "frequency": "daily/weekly/monthly",
  "report_time": "HH:MM:SS"
}
```


### **Environment Variables**

Create a `.env` file with your environment variables:

```env
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
DATABASE_URI=postgresql://user:password@db:5432/task_management_db
JWT_SECRET_KEY=your-secret-key
```  

### Docker Commands

#### Build Docker image:
```docker-compose build```
#### Start containers:
```docker-compose up```
#### Stop containers:
```docker-compose down```

## **Postman Collection**

A **Postman collection** is included in this repository for easier API testing.

### **Steps to Use:**
1. Open [Postman](https://www.postman.com/downloads/).
2. Click **Import**.
3. Select the file `postman_collection.json`.
4. You will now see all pre-configured API requests ready for testing.


### Contributing

Feel free to fork this repository and submit pull requests.

### License

This project is open-source and available under the MIT License.


