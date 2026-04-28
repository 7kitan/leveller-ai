# CORS Configuration Examples

## Scenario 1: Production Only
```bash
# Backend: https://api.onehub.cfd
# Frontend: https://onehub.cfd
ALLOWED_ORIGINS=https://onehub.cfd,https://www.onehub.cfd
```

## Scenario 2: Production + Local Development
```bash
# Backend: https://api.onehub.cfd (on server)
# Frontend: http://localhost:3000 (on your laptop)
ALLOWED_ORIGINS=https://onehub.cfd,http://localhost:3000,http://localhost:5173
```

## Scenario 3: Multiple Environments
```bash
# Production + Staging + Local
ALLOWED_ORIGINS=https://onehub.cfd,https://staging.onehub.cfd,http://localhost:3000,http://localhost:5173,http://localhost:8080
```

## Common Frontend Ports

| Framework | Default Port | Origin |
|-----------|-------------|---------|
| React (CRA) | 3000 | http://localhost:3000 |
| Next.js | 3000 | http://localhost:3000 |
| Vite | 5173 | http://localhost:5173 |
| Vue CLI | 8080 | http://localhost:8080 |
| Angular | 4200 | http://localhost:4200 |
| Svelte | 5000 | http://localhost:5000 |

## Testing CORS

### 1. From Browser Console
```javascript
// Test from your frontend
fetch('https://api.onehub.cfd/health', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN_HERE'
  }
})
.then(r => r.json())
.then(console.log)
.catch(console.error)
```

### 2. From curl
```bash
# Test CORS preflight
curl -X OPTIONS https://api.onehub.cfd/health \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -v

# Should return:
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Credentials: true
```

### 3. Check Backend Logs
```bash
# SSH to server
ssh user@server

# Check gateway logs
docker compose -f docker-compose.prod.yml logs -f gateway | grep CORS
```

## Common CORS Errors

### Error 1: "No 'Access-Control-Allow-Origin' header"
**Cause**: Origin not in ALLOWED_ORIGINS
**Fix**: Add your origin to .env
```bash
ALLOWED_ORIGINS=https://onehub.cfd,http://localhost:3000
```

### Error 2: "CORS policy: credentials mode is 'include'"
**Cause**: Trying to use credentials with wildcard origin
**Fix**: Use specific origins (already done in our config)

### Error 3: "Origin http://localhost:3000 is not allowed"
**Cause**: Missing port number or protocol
**Fix**: Use full origin with protocol and port
```bash
# ❌ Wrong
ALLOWED_ORIGINS=localhost

# ✅ Correct
ALLOWED_ORIGINS=http://localhost:3000
```

### Error 4: "Mixed Content" (HTTPS → HTTP)
**Cause**: HTTPS frontend calling HTTP backend
**Fix**: Use HTTPS for backend or HTTP for frontend (dev only)

## Security Best Practices

### ✅ DO
- Use specific origins (not wildcard "*")
- Use HTTPS in production
- Limit to necessary origins only
- Remove localhost origins in production

### ❌ DON'T
- Don't use `allow_origins=["*"]` with credentials
- Don't expose internal service URLs
- Don't include development origins in production
- Don't use HTTP in production

## Environment-Specific Configs

### Development (.env.local)
```bash
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000
```

### Staging (.env.staging)
```bash
ALLOWED_ORIGINS=https://staging.onehub.cfd,http://localhost:3000
```

### Production (.env.production)
```bash
ALLOWED_ORIGINS=https://onehub.cfd,https://www.onehub.cfd
```

## Troubleshooting Checklist

- [ ] Origin includes protocol (http:// or https://)
- [ ] Origin includes port if not default (80/443)
- [ ] No trailing slash in origin
- [ ] Backend .env has been updated
- [ ] Backend service has been restarted
- [ ] Browser cache cleared (Ctrl+Shift+R)
- [ ] Check browser console for CORS errors
- [ ] Check backend logs for CORS middleware logs
- [ ] Test with curl to verify server config
- [ ] Verify frontend is using correct API URL

## Quick Fix Commands

```bash
# 1. Update .env on server
ssh user@server
cd /opt/career-advisor/backend
nano .env
# Add: ALLOWED_ORIGINS=https://onehub.cfd,http://localhost:3000

# 2. Restart gateway
docker compose -f docker-compose.prod.yml restart gateway

# 3. Verify
curl -X OPTIONS https://api.onehub.cfd/health \
  -H "Origin: http://localhost:3000" \
  -v | grep Access-Control
```

## Frontend Configuration

Make sure your frontend API client is configured correctly:

### Axios Example
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://api.onehub.cfd',
  withCredentials: true, // Important for cookies/auth
  headers: {
    'Content-Type': 'application/json'
  }
});
```

### Fetch Example
```javascript
fetch('https://api.onehub.cfd/api/endpoint', {
  method: 'POST',
  credentials: 'include', // Important for cookies/auth
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
})
```

### React Query Example
```javascript
import { QueryClient } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: async ({ queryKey }) => {
        const res = await fetch(`https://api.onehub.cfd${queryKey[0]}`, {
          credentials: 'include'
        });
        return res.json();
      }
    }
  }
});
```
