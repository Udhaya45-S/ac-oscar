# Oscar Air Care

Oscar Air Care is a Flask-based web application for booking AC repair and maintenance services.

## Features

- Book AC repair service
- Track booking using tracking code
- Admin login
- View all bookings
- Update booking status
- MySQL database integration

## Technologies Used

- Python
- Flask
- MySQL
- HTML
- CSS
- JavaScript

## Project Structure

```
oscar-air-care/
│── app.py
│── db.py
│── requirements.txt
│── Procfile
│── verify_db.py
│── .env.example
│── .gitignore
│── DEPLOY.md
│
├── templates/
│   ├── index.html
│   └── admin.html
│
└── static/
    ├── css/
    ├── js/
    └── images/
```

## Installation

1. Clone the repository

```
git clone https://github.com/your-username/oscar-air-care.git
```

2. Install dependencies

```
pip install -r requirements.txt
```

3. Configure the environment variables in `.env`

4. Run the application

```
python app.py
```

The application will start at:

```
http://localhost:5000
```

## License

This project is developed for educational purposes.
