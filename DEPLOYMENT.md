# 🚀 Deployment Guide: Plants Hub on Render.com + Neon PostgreSQL

This guide will help you deploy your Plants Hub Flask application to **Render.com** (free) with **Neon PostgreSQL** database (also free).

---

## 📋 Prerequisites

- GitHub account
- Neon.tech account (free)
- Render.com account (free)

---

## 🗄️ Step 1: Set Up Neon PostgreSQL Database

1. **Go to [neon.tech](https://neon.tech)** and sign up/login
2. **Create a new project:**
   - Click "New Project"
   - Name: `plants-hub-db`
   - Region: Choose closest to you
   - PostgreSQL version: Latest (16+)
3. **Get your connection string:**
   - Go to "Connection Details"
   - Copy the connection string (looks like this):
     ```
     postgresql://username:password@ep-xxxx-yyyy.region.neon.tech/plants_db
     ```
   - **Save this** - you'll need it for Render!

---

## 💾 Step 2: Migrate Data from SQLite to PostgreSQL (Optional but Recommended)

If you have existing data in `plants.db`, migrate it to Neon PostgreSQL:

### On Windows (PowerShell):
```powershell
# Set your Neon connection string
$env:DATABASE_URL="postgresql://username:password@ep-xxxx.neon.tech/plants_db"

# Install dependencies
pip install -r requirements.txt

# Run migration script
python migrate_to_postgres.py
```

### On Linux/Mac:
```bash
# Set your Neon connection string
export DATABASE_URL="postgresql://username:password@ep-xxxx.neon.tech/plants_db"

# Install dependencies
pip install -r requirements.txt

# Run migration script
python migrate_to_postgres.py
```

✅ **Result:** All your products are now in the cloud PostgreSQL database!

---

## 📦 Step 3: Push to GitHub

### Initialize Git (if not already done):
```bash
git init
git add .
git commit -m "Prepare Plants Hub for Render deployment"
```

### Create GitHub Repository:
1. Go to [github.com](https://github.com) and create a new repository
2. Name it: `plants-hub-project`
3. **Don't** initialize with README (you already have files)
4. Copy the repository URL

### Push to GitHub:
```bash
# Add your GitHub repo as remote
git remote add origin https://github.com/YOUR-USERNAME/plants-hub-project.git

# Push to main branch
git branch -M main
git push -u origin main
```

---

## 🌐 Step 4: Deploy on Render.com

### 4.1 Create Web Service

1. **Go to [render.com](https://render.com)** and sign up/login
2. **Click "New +"** → **"Web Service"**
3. **Connect your GitHub repository:**
   - Authorize Render to access your GitHub
   - Select `plants-hub-project`

### 4.2 Configure Service

Fill out the deployment form:

| Field | Value |
|-------|-------|
| **Name** | `plants-hub` (or any name you like) |
| **Region** | Same as your Neon database region |
| **Branch** | `main` |
| **Root Directory** | (leave empty) |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |

### 4.3 Add Environment Variables

Scroll down to **Environment Variables** and add:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Your Neon PostgreSQL connection string |
| `FLASK_SECRET_KEY` | Generate a random secret key (use a password generator) |
| `FLASK_ENV` | `production` |

Example:
```
DATABASE_URL=postgresql://user:pass@ep-xxxx.neon.tech/plants_db
FLASK_SECRET_KEY=super-random-secret-key-here
FLASK_ENV=production
```

### 4.4 Deploy!

1. Click **"Create Web Service"**
2. Wait 2-5 minutes for deployment
3. Render will show build logs
4. When done, you'll see: ✅ **"Live"**

---

## 🎉 Step 5: Access Your Live App

Your app will be available at:
```
https://plants-hub.onrender.com
```
(Replace with your actual Render URL)

### Test the app:
- ✅ View all products
- ✅ Add new products
- ✅ Edit existing products
- ✅ Delete products
- ✅ Search and filter products

---

## 📁 Important Files Created

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies for Render |
| `Procfile` | Tells Render how to start the app |
| `.gitignore` | Prevents committing sensitive files |
| `.env.example` | Template for environment variables |
| `migrate_to_postgres.py` | Data migration script |

---

## 🔧 Troubleshooting

### Problem: App shows "Application Error"
**Solution:** Check Render logs (click "Logs" tab) for errors

### Problem: Database connection failed
**Solution:** 
1. Verify `DATABASE_URL` in Render environment variables
2. Make sure Neon database is active (not hibernated)

### Problem: Images not showing
**Solution:** 
1. Images are stored in `static/images/` folder
2. Make sure images are pushed to GitHub
3. Render serves static files automatically

### Problem: App is slow on first load
**Solution:** Render free tier hibernates after inactivity. First request wakes it up (takes ~30 seconds)

---

## 🆓 Free Tier Limits

### Render.com Free Tier:
- ✅ 750 hours/month (plenty for one app)
- ✅ Automatic SSL (HTTPS)
- ⚠️ Hibernates after 15 minutes of inactivity
- ⚠️ Slow cold starts (~30 seconds)

### Neon PostgreSQL Free Tier:
- ✅ 3 GB storage
- ✅ Unlimited queries
- ⚠️ Database hibernates after 5 minutes of inactivity

---

## 🔐 Security Best Practices

1. **Never commit `.env` file** (already in `.gitignore`)
2. **Use strong secret keys** (generate random strings)
3. **Keep DATABASE_URL secret** (only in Render environment variables)
4. **Rotate secrets regularly** (change keys every few months)

---

## 🚀 Next Steps (Optional Enhancements)

### 1. Add Custom Domain
- Go to Render → Settings → Custom Domain
- Add your domain (e.g., `plantshub.com`)

### 2. Enable Auto-Deploy
- Already enabled by default!
- Push to GitHub → Render auto-deploys

### 3. Add Database Backups
- Neon provides automatic backups (7 days retention)
- Export data manually: use `migrate_to_postgres.py` in reverse

### 4. Monitor Performance
- Use Render's built-in metrics
- Check database usage in Neon dashboard

---

## 📞 Support

- **Render Docs:** https://render.com/docs
- **Neon Docs:** https://neon.tech/docs
- **Flask Docs:** https://flask.palletsprojects.com/

---

## ✅ Checklist

Before deploying, make sure:

- [ ] Neon PostgreSQL database created and connection string copied
- [ ] Data migrated from SQLite to PostgreSQL (if you had existing data)
- [ ] Code pushed to GitHub repository
- [ ] Render web service created and connected to GitHub repo
- [ ] Environment variables added in Render (DATABASE_URL, FLASK_SECRET_KEY)
- [ ] App deployed successfully and showing "Live" status
- [ ] Tested app functionality (add/edit/delete products)

---

**🎉 Congratulations! Your Plants Hub is now live on the internet!**

Share your URL with friends and colleagues. Your app is now accessible from anywhere in the world! 🌍
