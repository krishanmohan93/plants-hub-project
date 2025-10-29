# 🌿 Plants Hub - Product Management System

A modern Flask web application for managing plant and pot inventory with image uploads, search, filtering, and database support.

![Plants Hub](static/images/logo.png)

---

## ✨ Features

- 📦 **Product Management:** Add, edit, delete plant and pot products
- 🖼️ **Image Upload:** Upload and display product images
- 🔍 **Smart Search:** Search products by name or description
- 🏷️ **Category Filtering:** Filter by ceramic, plastic, terracotta, fiber pots, and plants
- 💰 **Price Range Filter:** Find products within your budget
- 📊 **Inventory Tracking:** Manage product quantities
- 🗄️ **Database:** SQLAlchemy ORM with SQLite (local) or PostgreSQL (production)
- 📱 **Responsive Design:** Works on desktop, tablet, and mobile

---

## 🚀 Quick Start

### Local Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR-USERNAME/plants-hub-project.git
   cd plants-hub-project
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Open in browser:**
   ```
   http://localhost:5000
   ```

---

## 🌐 Deployment

Ready to deploy your app to the cloud? See **[DEPLOYMENT.md](DEPLOYMENT.md)** for detailed instructions on deploying to:
- ✅ **Render.com** (free hosting)
- ✅ **Neon PostgreSQL** (free database)

---

## 📁 Project Structure

```
plants_hub_project/
├── app.py                    # Main Flask application
├── models.py                 # SQLAlchemy database models
├── init_db.py                # Database initialization script
├── migrate_to_postgres.py    # SQLite to PostgreSQL migration
├── requirements.txt          # Python dependencies
├── Procfile                  # Render deployment configuration
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules
├── static/
│   ├── css/
│   │   └── style.css         # Custom styles
│   └── images/               # Product images
│       └── logo.png
├── templates/
│   ├── index.html            # Home page (product list)
│   ├── add.html              # Add product form
│   └── edit.html             # Edit product form
├── products.csv              # Original CSV data (backup)
├── products_backup.csv       # CSV backup
└── plants.db                 # SQLite database (local dev)
```

---

## 🗄️ Database Schema

### Product Model

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key (auto-increment) |
| `name` | String(200) | Product name |
| `description` | Text | Product description |
| `category` | String(50) | Category (ceramic_pot, plastic_pot, etc.) |
| `price` | Numeric(10,2) | Product price |
| `quantity` | Integer | Stock quantity |
| `image_url` | String(255) | Image filename |
| `created_at` | DateTime | Creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file (copy from `.env.example`):

```env
# Database URL
DATABASE_URL=sqlite:///plants.db  # Local
# DATABASE_URL=postgresql://...  # Production

# Flask Secret Key
FLASK_SECRET_KEY=your-super-secret-key

# Environment
FLASK_ENV=development
```

---

## 📦 Dependencies

- **Flask 3.0.0:** Web framework
- **Flask-SQLAlchemy 3.1.1:** Database ORM
- **psycopg2-binary 2.9.9:** PostgreSQL adapter
- **gunicorn 21.2.0:** Production server
- **python-dotenv 1.0.0:** Environment variables

See `requirements.txt` for full list.

---

## 🎨 Categories

Products can be categorized as:

- 🏺 **Ceramic Pots**
- 🪴 **Plastic Pots**
- 🏺 **Terracotta/Soil Pots**
- 🌾 **Fiber Pots**
- 🏠 **Indoor Plants**
- 🌳 **Outdoor Plants**
- 🎨 **Colorful Pots**

---

## 🛠️ Development

### Initialize Database

```bash
python init_db.py
```

This will:
1. Create database tables
2. Migrate data from `products.csv` (if exists)
3. Add sample products (if database is empty)

### Migrate to PostgreSQL

```bash
# Set DATABASE_URL to your PostgreSQL connection string
export DATABASE_URL="postgresql://user:pass@host/db"

# Run migration
python migrate_to_postgres.py
```

---

## 🔒 Security

- ✅ CSRF protection via Flask secret key
- ✅ File upload validation (image types only)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Secure filename handling
- ✅ Environment variable for sensitive data

---

## 📸 Screenshots

### Home Page
- Product grid with images
- Search and filter options
- Category quick filters

### Add Product
- Form with validation
- Image upload
- Category selection

### Edit Product
- Pre-filled form
- Image update/keep option
- Delete confirmation modal

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

---

## 👤 Author

Created with ❤️ by Krishanmohan Kumar

---

## 🙏 Acknowledgments

- Flask framework and community
- Bootstrap for responsive design
- Bootstrap Icons for beautiful icons
- SQLAlchemy for powerful ORM

---

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact: your-krishanmohankumar9311@gmail.com
---

**Happy Planting! 🌱**
