# Oscar Air Care

Oscar Air Care is a web-based AC service booking application developed using Flask and MySQL.

## Features

- Book AC repair and maintenance services
- Generate a unique tracking code
- Track booking status
- Admin login
- View all customer bookings
- Update booking status

## Technologies Used

- Python
- Flask
- MySQL
- HTML
- CSS
- JavaScript

## Project Structure

```
ac-oscar/
│── app.py
│── db.py
│── verify_db.py
│── requirements.txt
│── Procfile
│── .gitignore
│── .env.example
│── DEPLOY.md
│
├── templates/
│   ├── index.html
│   └── admin.html
│
└── static/
    ├── css/
    └── js/
```

## Installation

1. Clone the repository

```bash
git clone https://github.com/Udhaya45-S/ac-oscar.git
```

2. Install the required packages

```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`

4. Run the application

```bash
python app.py
```

5. Open your browser and visit

```
http://localhost:5000
```

## Author

**Udhaya Sivakumar**

## License

This project is created for educational purposes.
