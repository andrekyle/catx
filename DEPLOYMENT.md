# 🚀 Vercel Deployment Guide for ShopIt

## Quick Start

### Step 1: GitHub Repository ✅
- Repository: https://github.com/andrekyle/shopit.git
- Code has been pushed and is ready for deployment

### Step 2: Deploy to Vercel

#### Option A: Web Interface (Recommended)
1. Go to https://vercel.com/new
2. Click "Import Git Repository"
3. Select `andrekyle/shopit` from GitHub
4. Configure project settings:
   - **Framework Preset**: Other
   - **Root Directory**: `./` (default)
   - **Build Command**: `bash build.sh`
   - **Output Directory**: Leave empty
   - **Install Command**: `pip install -r requirements.txt`

#### Option B: Vercel CLI
```bash
npm i -g vercel
cd /path/to/shopit
vercel --prod
```

### Step 3: Environment Variables

Add these environment variables in Vercel Dashboard:

```
SECRET_KEY=your-production-secret-key-change-this
POSTGRES_URL=postgres://0199cd7a-e98f-79db-935e-93827b9423b3:6e576d8f-193c-4587-9d8d-2f7bc60b16fc@us-west-2.db.thenile.dev/shopit
NILEDB_URL=postgres://0199cd7a-e98f-79db-935e-93827b9423b3:6e576d8f-193c-4587-9d8d-2f7bc60b16fc@us-west-2.db.thenile.dev/shopit
NILEDB_USER=0199cd7a-e98f-79db-935e-93827b9423b3
NILEDB_PASSWORD=6e576d8f-193c-4587-9d8d-2f7bc60b16fc
NILEDB_API_URL=https://us-west-2.api.thenile.dev/v2/databases/0199cd7a-e756-7fd6-aa7d-17c67c5ee715
NILEDB_POSTGRES_URL=postgres://us-west-2.db.thenile.dev/shopit
```

### Step 4: Deploy!

Click "Deploy" and wait for the build to complete.

## Expected Deployment Flow

1. **Build Phase**: 
   - Install Python dependencies
   - Create upload directories
   - Set permissions

2. **Runtime Phase**:
   - Connect to Nile Database
   - Auto-migrate database schema
   - Initialize with sample data
   - Start Flask server

## Post-Deployment

### Default Admin Access
- **URL**: Your Vercel domain (e.g., `https://shopit-xyz.vercel.app`)
- **Admin Login**: admin@brandcartel.com
- **Password**: admin123

### First Steps After Deployment
1. Login to admin panel
2. Change admin password
3. Configure site settings
4. Upload logo and branding
5. Add product categories
6. Start adding products

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify Nile database credentials
   - Check environment variables
   - Ensure database is accessible

2. **Build Failures**
   - Check build logs in Vercel dashboard
   - Verify requirements.txt
   - Check build.sh permissions

3. **Runtime Errors**
   - Check function logs in Vercel
   - Verify all environment variables are set
   - Check for missing dependencies

### Debug Commands
```bash
# Check deployment logs
vercel logs [deployment-url]

# Check function logs
vercel logs --follow
```

## Database Migration

The application automatically handles database migrations on startup:
- Creates tables if they don't exist
- Adds missing columns
- Initializes with sample data

## Support

For deployment issues:
1. Check Vercel documentation
2. Review application logs
3. Verify database connectivity
4. Check environment variables

---

**Ready to deploy!** 🎉
