# IP Block Management API Documentation

## Overview

Admin endpoints để quản lý các IP addresses bị block do failed login attempts.

## Endpoints

### 1. Get All Blocked IPs

**GET** `/admin/blocked-ips`

Lấy danh sách tất cả IP addresses đang bị block.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "total": 3,
  "blocked_ips": [
    {
      "ip_address": "192.168.1.100",
      "ttl_seconds": 82800,
      "ttl_hours": 23.0,
      "attempts": 5,
      "expires_in": "23h 0m"
    },
    {
      "ip_address": "10.0.0.50",
      "ttl_seconds": 43200,
      "ttl_hours": 12.0,
      "attempts": 6,
      "expires_in": "12h 0m"
    }
  ]
}
```

**cURL Example:**
```bash
curl -X GET https://api.onehub.cfd/admin/blocked-ips \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 2. Unblock Specific IP

**POST** `/admin/unblock-ip`

Gỡ block cho một IP address cụ thể.

**Headers:**
```
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "ip_address": "192.168.1.100"
}
```

**Response:**
```json
{
  "message": "IP 192.168.1.100 has been unblocked",
  "ip_address": "192.168.1.100",
  "lockout_removed": true,
  "attempts_cleared": true,
  "status": "success"
}
```

**cURL Example:**
```bash
curl -X POST https://api.onehub.cfd/admin/unblock-ip \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ip_address": "192.168.1.100"}'
```

---

### 3. Check IP Status

**GET** `/admin/ip-status/{ip_address}`

Kiểm tra trạng thái của một IP address cụ thể.

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "ip_address": "192.168.1.100",
  "is_blocked": true,
  "failed_attempts": 5,
  "lockout_ttl_seconds": 82800,
  "lockout_expires_in": "23h 0m",
  "attempts_ttl_seconds": 3600,
  "attempts_reset_in": "60m 0s"
}
```

**cURL Example:**
```bash
curl -X GET https://api.onehub.cfd/admin/ip-status/192.168.1.100 \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 4. Clear All Blocked IPs

**DELETE** `/admin/blocked-ips`

⚠️ **WARNING:** Xóa TẤT CẢ IP blocks. Sử dụng cẩn thận!

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "message": "All blocked IPs have been cleared",
  "lockouts_removed": 15,
  "attempts_cleared": 23,
  "status": "success"
}
```

**cURL Example:**
```bash
curl -X DELETE https://api.onehub.cfd/admin/blocked-ips \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Frontend Integration Examples

### React/TypeScript Example

```typescript
// api/admin.ts
import axios from 'axios';

const adminAPI = axios.create({
  baseURL: 'https://api.onehub.cfd',
  withCredentials: true
});

// Get all blocked IPs
export const getBlockedIPs = async () => {
  const response = await adminAPI.get('/admin/blocked-ips');
  return response.data;
};

// Unblock specific IP
export const unblockIP = async (ipAddress: string) => {
  const response = await adminAPI.post('/admin/unblock-ip', {
    ip_address: ipAddress
  });
  return response.data;
};

// Check IP status
export const checkIPStatus = async (ipAddress: string) => {
  const response = await adminAPI.get(`/admin/ip-status/${ipAddress}`);
  return response.data;
};

// Clear all blocks
export const clearAllBlocks = async () => {
  const response = await adminAPI.delete('/admin/blocked-ips');
  return response.data;
};
```

### React Component Example

```tsx
// components/BlockedIPsManager.tsx
import React, { useState, useEffect } from 'react';
import { getBlockedIPs, unblockIP } from '../api/admin';

export const BlockedIPsManager: React.FC = () => {
  const [blockedIPs, setBlockedIPs] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadBlockedIPs();
  }, []);

  const loadBlockedIPs = async () => {
    setLoading(true);
    try {
      const data = await getBlockedIPs();
      setBlockedIPs(data.blocked_ips);
    } catch (error) {
      console.error('Failed to load blocked IPs:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUnblock = async (ipAddress: string) => {
    if (!confirm(`Unblock IP ${ipAddress}?`)) return;
    
    try {
      await unblockIP(ipAddress);
      alert(`IP ${ipAddress} has been unblocked`);
      loadBlockedIPs(); // Reload list
    } catch (error) {
      alert('Failed to unblock IP');
    }
  };

  return (
    <div className="blocked-ips-manager">
      <h2>Blocked IP Addresses ({blockedIPs.length})</h2>
      
      {loading ? (
        <p>Loading...</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>IP Address</th>
              <th>Failed Attempts</th>
              <th>Expires In</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {blockedIPs.map((ip) => (
              <tr key={ip.ip_address}>
                <td>{ip.ip_address}</td>
                <td>{ip.attempts}</td>
                <td>{ip.expires_in}</td>
                <td>
                  <button onClick={() => handleUnblock(ip.ip_address)}>
                    Unblock
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
```

---

## CLI Usage Examples

### Using cURL

```bash
# 1. Login as admin to get token
TOKEN=$(curl -X POST https://api.onehub.cfd/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password"}' \
  | jq -r '.access_token')

# 2. Get all blocked IPs
curl -X GET https://api.onehub.cfd/admin/blocked-ips \
  -H "Authorization: Bearer $TOKEN" \
  | jq

# 3. Check specific IP
curl -X GET https://api.onehub.cfd/admin/ip-status/192.168.1.100 \
  -H "Authorization: Bearer $TOKEN" \
  | jq

# 4. Unblock IP
curl -X POST https://api.onehub.cfd/admin/unblock-ip \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ip_address":"192.168.1.100"}' \
  | jq
```

### Using HTTPie

```bash
# 1. Login
http POST https://api.onehub.cfd/auth/login \
  email=admin@example.com password=password

# 2. Get blocked IPs (with cookie auth)
http GET https://api.onehub.cfd/admin/blocked-ips

# 3. Unblock IP
http POST https://api.onehub.cfd/admin/unblock-ip \
  ip_address=192.168.1.100
```

---

## Security Notes

1. **Admin Only:** Tất cả endpoints yêu cầu admin role
2. **Audit Logging:** Mọi thao tác unblock đều được log với admin email
3. **Rate Limiting:** Endpoints này cũng có rate limiting
4. **CORS:** Đảm bảo frontend domain được thêm vào ALLOWED_ORIGINS

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Missing or invalid token"
}
```

### 403 Forbidden
```json
{
  "detail": "Admin privileges required"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Failed to unblock IP: <error message>"
}
```

---

## Testing

### Test Blocked IP Flow

```bash
# 1. Intentionally fail login 5 times to block an IP
for i in {1..5}; do
  curl -X POST https://api.onehub.cfd/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrongpassword"}'
done

# 2. Check if IP is blocked
curl -X GET https://api.onehub.cfd/admin/ip-status/YOUR_IP \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 3. Unblock the IP
curl -X POST https://api.onehub.cfd/admin/unblock-ip \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ip_address":"YOUR_IP"}'

# 4. Verify unblocked
curl -X GET https://api.onehub.cfd/admin/ip-status/YOUR_IP \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

---

## Monitoring

### Check Logs

```bash
# View admin service logs
docker compose -f docker-compose.prod.yml logs -f admin-service | grep "ADMIN"

# Look for unblock events
docker compose -f docker-compose.prod.yml logs admin-service | grep "Unblocked IP"
```

### Redis Monitoring

```bash
# Connect to Redis
docker exec -it advisor_redis_prod redis-cli -a YOUR_PASSWORD

# Monitor real-time commands
MONITOR

# Count blocked IPs
KEYS lockout:* | wc -l
```

---

## Best Practices

1. **Review Before Unblocking:** Check IP status first to understand why it was blocked
2. **Log Review:** Always check logs after unblocking to see if attacks continue
3. **Whitelist Important IPs:** Consider implementing IP whitelist for office/VPN IPs
4. **Alert on Mass Blocks:** Set up monitoring to alert when many IPs get blocked
5. **Regular Cleanup:** Periodically review and clear old blocks

---

## Future Enhancements

- [ ] Add IP whitelist feature
- [ ] Add reason/notes when unblocking
- [ ] Export blocked IPs to CSV
- [ ] Automatic unblock after X hours
- [ ] IP geolocation information
- [ ] Block history/audit trail
- [ ] Bulk unblock operations
- [ ] Email notifications on block/unblock
