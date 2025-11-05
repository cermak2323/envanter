# 🚀 Render.com Environment Variables Setup

## Required Environment Variables

Render Dashboard → Your Service → Environment → Add Environment Variable

### 1. Database Configuration
```bash
DATABASE_URL=<PostgreSQL_Connection_String>
```
**Where to get:** Render Dashboard → PostgreSQL → Connection String

### 2. Session Security
```bash
SESSION_SECRET=<random_secret_key>
```
**Generate with:**
```python
import secrets
print(secrets.token_hex(32))
```

### 3. Backblaze B2 Storage (QR Codes)
```bash
B2_APPLICATION_KEY_ID=<your_key_id>
B2_APPLICATION_KEY=<your_key>
B2_BUCKET_NAME=envanter-qr-bucket
```
**Where to get:** Backblaze B2 Dashboard → App Keys

### 4. Admin Access
```bash
ADMIN_COUNT_PASSWORD=<secure_password>
```
**For admin count management**

## 🔧 Setup Steps

### Step 1: Create PostgreSQL Database
1. Render Dashboard → New → PostgreSQL
2. Choose plan (Free tier available)
3. Wait for deployment
4. Copy **External Database URL**

### Step 2: Create Backblaze B2 Bucket
1. Sign up/Login to Backblaze B2
2. Create bucket: `envanter-qr-bucket`
3. Create App Key with read/write permissions
4. Save Key ID and Key

### Step 3: Set Environment Variables
1. Go to your web service in Render
2. Environment → Add Environment Variable
3. Add all variables above
4. **IMPORTANT:** Set DATABASE_URL as **secret**

### Step 4: Deploy
1. Manual Deploy or Push to Git
2. Monitor build logs
3. Check deployment status

## 🔍 Troubleshooting

### Error: "DATABASE_URL environment variable not set"
- ✅ Add DATABASE_URL in Render Dashboard
- ✅ Use PostgreSQL External URL
- ✅ Redeploy after adding

### Error: B2 Storage Issues
- ✅ Check B2 credentials
- ✅ Verify bucket exists and accessible
- ✅ Check App Key permissions

### Error: Session Issues
- ✅ Set SESSION_SECRET
- ✅ Use long random string (64+ chars)

## 📋 Environment Variables Checklist

- [ ] DATABASE_URL (PostgreSQL External URL)
- [ ] SESSION_SECRET (Random 64-char string)
- [ ] B2_APPLICATION_KEY_ID (Backblaze)
- [ ] B2_APPLICATION_KEY (Backblaze)
- [ ] B2_BUCKET_NAME (envanter-qr-bucket)
- [ ] ADMIN_COUNT_PASSWORD (Admin access)

## 🧪 Test Deployment

After setting all variables:

1. ✅ App starts without errors
2. ✅ Database connection works
3. ✅ QR codes can be uploaded
4. ✅ B2 storage accessible
5. ✅ Admin panel works

## 🔐 Security Notes

- Never commit secrets to git
- Use Render's secret variables for sensitive data
- Rotate secrets regularly
- Monitor access logs

## 📞 Support

If issues persist:
1. Check Render build logs
2. Monitor runtime logs
3. Verify all environment variables set
4. Test with temporary SQLite (see logs)

---
*Generated for EnvanterQR Dual-Mode System*