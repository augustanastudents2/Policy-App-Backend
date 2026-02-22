# Deploying to Render

This guide walks you through deploying the ASA Policy App backend to Render.

## Prerequisites

1. A [Render](https://render.com) account (free tier available)
2. Your Supabase project already set up
3. Your code pushed to a Git repository (GitHub, GitLab, or Bitbucket)

**Quick Start**: If you want to create a separate repository just for the backend (recommended for class projects), see `SETUP_NEW_REPO.md` for step-by-step instructions.

## Private Repository Setup

**Option 1: Create a Separate Backend Repository (Recommended)**

This is the easiest approach for class projects:

1. **Create a new repository** (can be public or private):

   - Go to GitHub/GitLab/Bitbucket
   - Create a new repository (e.g., `asa-policy-backend`)
   - You can make it public (since it's just backend code, no secrets)

2. **Copy backend folder contents**:

   ```bash
   # Navigate to your project root
   cd /path/to/Project--7-ASA-Policy-App-2026

   # Create a new directory for the backend repo
   mkdir ../asa-policy-backend
   cd ../asa-policy-backend

   # Copy all backend files
   cp -r ../Project--7-ASA-Policy-App-2026/backend/* .

   # Initialize git and push
   git init
   git add .
   git commit -m "Initial backend setup"
   git branch -M main
   git remote add origin https://github.com/yourusername/asa-policy-backend.git
   git push -u origin main
   ```

3. **Deploy from the new repo**:
   - Connect this new repository to Render
   - Since it's separate, you can make it public (no class project code exposed)
   - Render can easily access it

**Option 2: Connect Private Class Repository**

If you want to keep everything in one repo:

1. **Connect Your Git Account**:

   - In Render dashboard, go to **Account Settings** → **Connected Accounts**
   - Click **"Connect"** next to GitHub/GitLab/Bitbucket
   - Authorize Render to access your repositories
   - You can grant access to:
     - All repositories
     - Only specific repositories (recommended for private repos)

2. **Grant Repository Access**:
   - When creating a new service, Render will show your private repos
   - Select your private repository
   - Render will have access to deploy from it

**Note**: If you're using a private repository for a class project, you can:

- Grant Render access to just that one repository (not all repos)
- Or use the manual deployment method below

## Step 1: Prepare Your Code

### 1.1 Create a Procfile

A `Procfile` is already created in the backend directory. It tells Render how to run your application:

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

### 1.2 Update CORS Origins (if needed)

If you know your frontend URL, update `app/core/config.py` to include it in `CORS_ORIGINS`:

```python
CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8000",
    "https://your-frontend-domain.com",  # Add your production frontend URL
]
```

Or set it via environment variable (see Step 3).

### 1.3 Commit and Push to Git

Make sure all your changes are committed and pushed to your repository:

```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

## Step 2: Create a Render Web Service

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your Git repository:

   - **For Private Repos**: Make sure you've connected your Git account first (see "Private Repository Setup" above)
   - Select your Git provider (GitHub, GitLab, or Bitbucket)
   - If prompted, authorize Render to access your repositories
   - You can grant access to:
     - **All repositories** (not recommended for private repos)
     - **Only specific repositories** (recommended - select just your class project)
   - Select the repository containing your backend code

4. Configure the service:

   - **Name**: `asa-policy-backend` (or your preferred name)
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: `backend` (important - this tells Render where your backend code is)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

   **Important**: Render automatically sets the `$PORT` environment variable, so your Procfile should use it.

## Step 3: Configure Environment Variables

In the Render dashboard, go to your service → **Environment** tab, and add these variables:

### Required Variables:

```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-key-here
SUPABASE_SERVICE_KEY=your-service-role-key-here
```

### Optional Variables (with defaults):

```
POLICIES_TABLE=policies
BYLAWS_TABLE=bylaws
SUGGESTIONS_TABLE=suggestions
USERS_TABLE=users
POLICY_VERSIONS_TABLE=policy_versions
DEBUG=False
ENVIRONMENT=production
```

### CORS Origins (if you have a frontend):

```
CORS_ORIGINS=http://localhost:3000,https://your-frontend-domain.com
```

**Note**: Render reads environment variables from the dashboard, so you don't need a `.env` file in production.

## Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will:
   - Clone your repository
   - Install dependencies from `requirements.txt`
   - Start your application using the Procfile
3. Wait for the build to complete (usually 2-5 minutes)
4. Your service will be available at: `https://your-service-name.onrender.com`

## Step 5: Verify Deployment

1. **Health Check**: Visit `https://your-service-name.onrender.com/health`

   - Should return: `{"status": "healthy"}`

2. **API Documentation**: Visit `https://your-service-name.onrender.com/docs`

   - Should show Swagger UI

3. **Test an Endpoint**:
   ```bash
   curl https://your-service-name.onrender.com/api/policies/approved
   ```

## Step 6: Update Frontend (if applicable)

If you have a frontend, update your API base URL to point to your Render service:

```javascript
const API_BASE_URL = "https://your-service-name.onrender.com/api";
```

## Important Notes

### Free Tier Limitations

- **Spins down after 15 minutes of inactivity**: First request after inactivity may take 30-60 seconds
- **512 MB RAM**: Should be sufficient for this backend
- **Limited CPU**: May be slower during peak times

### Upgrading to Paid Tier

If you need:

- Always-on service (no spin-down)
- More resources
- Better performance

Consider upgrading to the **Starter** plan ($7/month).

### Database

Your Supabase database is already hosted separately, so no additional database setup is needed on Render.

### Environment Variables Security

- Never commit `.env` files to Git
- Use Render's environment variables for all secrets
- The `SUPABASE_SERVICE_KEY` is sensitive - keep it secure

## Troubleshooting

### Build Fails with Rust/Cargo Errors

If you see errors about Rust/Cargo or "read-only file system":

1. **The issue**: Some packages (like `cryptography`) need to compile Rust code, which can fail on Render
2. **Solution**: The `requirements.txt` already includes a pinned `cryptography` version with pre-built wheels
3. **If still failing**: Try updating the Python version in Render settings:
   - Go to your service → **Settings** → **Environment**
   - Set `PYTHON_VERSION=3.11.9` (must include patch version, e.g., 3.11.9, not just 3.11)
   - Redeploy

### Build Fails (General)

1. Check build logs in Render dashboard
2. Verify `requirements.txt` has all dependencies
3. Ensure Python version is compatible (3.9+)
4. Try pinning Python version to 3.11.9 in Render environment variables (must include patch version)

### Application Crashes

1. Check logs in Render dashboard
2. Verify all environment variables are set correctly
3. Test locally with the same environment variables

### CORS Errors

1. Add your frontend URL to `CORS_ORIGINS` environment variable
2. Ensure `allow_credentials=True` is set (already configured)

### Slow First Request

- This is normal on the free tier (cold start)
- Consider upgrading to paid tier for always-on service

## Custom Domain (Optional)

1. Go to your service → **Settings** → **Custom Domains**
2. Add your domain
3. Follow Render's DNS configuration instructions

## Monitoring

Render provides:

- **Logs**: View real-time application logs
- **Metrics**: CPU, memory, and request metrics
- **Events**: Deployment and service events

Access these from your service dashboard.

## Updating Your Deployment

Whenever you push changes to your repository:

1. Render automatically detects the push
2. Builds a new version
3. Deploys it (zero-downtime deployment)
4. Your service URL stays the same

You can also manually trigger deployments from the Render dashboard.

## Alternative: Manual Deployment (If Git Access Issues)

If you can't connect your private repository, you can deploy manually:

### Option 1: Deploy via Render CLI

1. Install Render CLI:

   ```bash
   npm install -g render-cli
   ```

2. Login to Render:

   ```bash
   render login
   ```

3. Create a service manually:
   ```bash
   cd backend
   render deploy
   ```

### Option 2: Deploy via Render Dashboard (Manual Upload)

1. Create a new Web Service in Render
2. Instead of connecting Git, choose **"Manual Deploy"**
3. Upload your `backend` folder as a ZIP file
4. Set environment variables in the dashboard
5. Render will build and deploy from the uploaded code

**Note**: With manual upload, you'll need to re-upload when you make changes (no auto-deploy).

### Option 3: Use Other Hosting Platforms

If Render doesn't work for your private repo, consider:

#### Railway

- Supports private GitHub repos
- Free tier available
- Similar setup to Render
- Visit: [railway.app](https://railway.app)

#### Fly.io

- Supports private repos
- Free tier available
- Good for Python apps
- Visit: [fly.io](https://fly.io)

#### Heroku

- Supports private repos
- Free tier limited (may require paid plan)
- Visit: [heroku.com](https://heroku.com)

#### PythonAnywhere

- Simple Python hosting
- Free tier available
- Manual deployment via web interface
- Visit: [pythonanywhere.com](https://www.pythonanywhere.com)

---

**Need Help?**

- [Render Documentation](https://render.com/docs)
- [Render Community](https://community.render.com)
- [Render Support](https://render.com/support)
