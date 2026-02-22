# ASA Policy App - Backend API

FastAPI backend for the Augustana Students' Association (ASA) Policy Management System with Supabase integration.

## 🌐 Live Site

**Live API**: [https://asa-policy-backend.onrender.com](https://asa-policy-backend.onrender.com)

- **API Documentation**: https://asa-policy-backend.onrender.com/docs
- **Health Check**: https://asa-policy-backend.onrender.com/api/health

## Features

- **Policy Management**: Create, update, approve, and manage policies with version history
- **Bylaw Management**: Manage bylaws with approval workflow
- **Suggestions System**: Public users can submit suggestions for policies and bylaws
- **Policy Reviews**: Users can submit reviews (confirm/needs_work) for policies
- **Role-Based Access Control**: Three user roles (public, admin, policy_working_group)
- **Authentication**: Secure authentication using Supabase Auth
- **Version History**: Automatic version tracking for policy changes

## Prerequisites

- **Python 3.9 or higher** (3.9–3.13 supported)
- A Supabase account and project
- pip (Python package manager)

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd asa-policy-backend-temp
```

### 2. Set Up Supabase

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Wait for the project to be fully provisioned
3. Go to **Settings** → **API** to get your credentials:
   - **Project URL** (SUPABASE_URL)
   - **anon public** key (SUPABASE_KEY)
   - **service_role** key (SUPABASE_SERVICE_KEY) - Keep this secret!

### 3. Set Up Database Schema

1. In your Supabase project, go to **SQL Editor**
2. Open `database/database_schema.sql` from this project
3. Copy and paste the entire SQL script into the SQL Editor
4. Click **Run** to execute the script
5. Verify tables were created by going to **Table Editor** - you should see:
   - `policies`
   - `bylaws`
   - `suggestions`
   - `users`
   - `policy_versions`
   - `policy_reviews`

**Note:** The schema file includes all necessary tables, indexes, triggers, and Row-Level Security (RLS) policies.

### 4. Configure Environment Variables

1. Create a `.env` file in the project root:

   ```bash
   touch .env
   ```

2. Add your Supabase credentials to `.env`:

   ```env
   SUPABASE_URL=https://your-project-id.supabase.co
   SUPABASE_KEY=your-anon-key-here
   SUPABASE_SERVICE_KEY=your-service-role-key-here
   ```

3. **Important**: Never commit the `.env` file to git (it's already in `.gitignore`)

### 5. Set Up Virtual Environment

```bash
# Create virtual environment (recommended: .venv in project root)
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 6. Install Dependencies

```bash
# With virtual environment activated
pip install -r requirements.txt
```

### 7. Run the Backend

From the project root, with your virtual environment **activated**:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate

# Run with uvicorn (--reload enables auto-restart on code changes)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Or run uvicorn directly without activating (macOS/Linux):

```bash
.venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The backend will start at **http://127.0.0.1:8000** (and http://localhost:8000).

### 8. Verify It's Working

- **API Documentation**: http://127.0.0.1:8000/docs
- **Health Check**: http://127.0.0.1:8000/api/health
- **Root Endpoint**: http://127.0.0.1:8000/

## Project Structure

```
Policy-App-Backend/
├── app/
│   ├── core/              # Core functionality
│   │   ├── auth.py        # Authentication & authorization
│   │   ├── config.py      # Configuration settings
│   │   └── database.py    # Database client setup
│   ├── models/            # Pydantic schemas
│   │   └── schemas.py     # Request/response models
│   └── routers/           # API route handlers
│       ├── auth.py        # Authentication endpoints
│       ├── policies.py    # Policy management endpoints
│       ├── bylaws.py      # Bylaw management endpoints
│       └── suggestions.py # Suggestion endpoints
├── database/              # Database schema SQL files
│   └── database_schema.sql # Complete database schema
├── main.py                # FastAPI application entry point
├── requirements.txt       # Python dependencies
├── Procfile              # Process file for deployment
├── render.yaml           # Render deployment configuration
└── README.md             # This file
```

## Database Schema

The database schema is located in the `database/` folder:

- **`database/database_schema.sql`** - Complete database schema with all tables, indexes, triggers, and RLS policies

### Tables

- **policies**: Stores policy documents with sections and status
- **bylaws**: Stores bylaw documents with numbers and status
- **suggestions**: Stores user suggestions for policies and bylaws
- **users**: Stores user information and roles
- **policy_versions**: Tracks version history for policy changes
- **policy_reviews**: Tracks user reviews (confirm/needs_work) for policies

## Creating Your First Admin User

After setting up the database:

1. Go to Supabase Dashboard → **Authentication** → **Users**
2. Click **Add user** → **Create new user**
3. Enter email and password
4. Go to **Table Editor** → `users` table
5. Find the user by email and update the `role` field to `admin`

Or use SQL:

```sql
UPDATE users
SET role = 'admin'
WHERE email = 'your-email@example.com';
```

## API Endpoints

**Live API Documentation**: [https://asa-policy-backend.onrender.com/docs](https://asa-policy-backend.onrender.com/docs)

For local development, visit http://127.0.0.1:8000/docs for interactive API documentation with Swagger UI.

### Authentication (`/api/auth`)

- `POST /api/auth/login` - Login (admin or policy_working_group only)
- `POST /api/auth/register` - Register new user (admin only)
- `GET /api/auth/me` - Get current user information
- `POST /api/auth/logout` - Logout current user
- `GET /api/auth/users` - Get all users (admin only)
- `PUT /api/auth/users/{user_id}/role` - Update user role (admin only)
- `DELETE /api/auth/users/{user_id}` - Delete user (admin only)

### Policies (`/api/policies`)

- `GET /api/policies/` - Get all policies with filtering (admin or policy_working_group)
- `GET /api/policies/approved` - Get approved policies (public access)
- `GET /api/policies/{policy_id}` - Get single approved policy by ID (public access)
- `POST /api/policies/` - Create new policy (admin or policy_working_group)
- `PUT /api/policies/{policy_id}` - Update policy (admin or policy_working_group)
- `PUT /api/policies/{policy_id}/approve` - Approve policy (admin only)
- `DELETE /api/policies/{policy_id}` - Delete policy (admin only)
- `GET /api/policies/{policy_id}/versions` - Get policy version history (admin only)
- `POST /api/policies/{policy_id}/reviews` - Submit policy review (authenticated users)
- `GET /api/policies/{policy_id}/reviews` - Get policy reviews (public access)
- `DELETE /api/policies/reviews/reset-all` - Reset all policy reviews (admin only)

### Bylaws (`/api/bylaws`)

- `GET /api/bylaws/` - Get all bylaws with filtering (admin or policy_working_group)
- `GET /api/bylaws/approved` - Get approved bylaws (public access)
- `GET /api/bylaws/{bylaw_id}` - Get single approved bylaw by ID (public access)
- `POST /api/bylaws/` - Create new bylaw (admin or policy_working_group)
- `PUT /api/bylaws/{bylaw_id}` - Update bylaw (admin or policy_working_group)
- `PUT /api/bylaws/{bylaw_id}/approve` - Approve bylaw (admin only)
- `DELETE /api/bylaws/{bylaw_id}` - Delete bylaw (admin only)

### Suggestions (`/api/suggestions`)

- `GET /api/suggestions/` - Get all suggestions (admin or policy_working_group)
- `POST /api/suggestions/` - Create new suggestion (public access)
- `DELETE /api/suggestions/{suggestion_id}` - Delete suggestion (admin or policy_working_group)

### General

- `GET /` - Root endpoint with API information
- `GET /api/health` - Health check endpoint

## User Roles

The system supports three user roles:

- **public**: Default role for all users. Can view approved policies/bylaws and submit suggestions.
- **policy_working_group**: Can manage suggestions, create/update policies and bylaws (but not approve them).
- **admin**: Full access including approving policies/bylaws, managing users, and deleting content.

## Authentication

The API uses Supabase Auth for authentication. Include the access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

## Troubleshooting

### Virtual Environment Not Activated

If you get `ModuleNotFoundError: No module named 'fastapi'` or similar, you're likely using system Python instead of the project virtual environment. Activate the venv first:

```bash
# Check if venv is active (should show path to .venv)
echo $VIRTUAL_ENV

# If empty, activate it
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### Module Not Found Errors

```bash
# Create venv if you haven't, then activate and install dependencies
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### Database Connection Errors

- Verify your `.env` file has correct Supabase credentials
- Check that the database schema has been run in Supabase SQL Editor
- Ensure your Supabase project is active

### Port Already in Use

If port 8000 is already in use, specify a different port:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

## Development

The backend uses:

- **FastAPI** - Modern, fast web framework for building APIs
- **Supabase** - Database and authentication backend
- **Pydantic** - Data validation using Python type annotations
- **Uvicorn** - ASGI server for running FastAPI

For development, the server runs with `--reload` flag for auto-reloading on code changes.

## Deployment

See `DEPLOYMENT.md` for instructions on deploying to Render or other hosting platforms.

## License

[Add your license here]

## Contributing

[Add contributing guidelines here]
