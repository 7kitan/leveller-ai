# Export/Import by Parts - Design Document

## Problem
- Exporting all jobs/courses creates files too large to upload
- Need to split into manageable parts

## Solution: User-Controlled Part Splitting

### User Flow

1. **Get Export Info**
   ```
   GET /jd/admin/export-info
   
   Response:
   {
     "total_jobs": 10000,
     "recommended_parts": 5,
     "recommended_per_part": 2000,
     "estimated_size_per_part_mb": 15
   }
   ```

2. **User Decides Split**
   - Frontend shows: "Total: 10,000 jobs. Recommended: 5 parts (~15MB each)"
   - User can adjust: "Split into: [5] parts"

3. **Download Parts**
   ```
   GET /jd/admin/export-jobs?offset=0&limit=2000     # Part 1
   GET /jd/admin/export-jobs?offset=2000&limit=2000  # Part 2
   GET /jd/admin/export-jobs?offset=4000&limit=2000  # Part 3
   ...
   ```

4. **Import Parts**
   - User uploads part1.json, part2.json, etc.
   - Each part processed independently
   - Duplicates automatically skipped (already handled)

### API Implementation

#### New Endpoint: Export Info

```python
@app.get("/jd/admin/export-info")
def get_export_info(request: Request, db: Session = Depends(get_db)):
    """Get information for planning export."""
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    total = db.query(Job).filter(Job.status == "active").count()
    
    # Estimate size (rough calculation)
    # Average job: ~10KB (text + vector)
    avg_size_kb = 10
    total_size_mb = (total * avg_size_kb) / 1024
    
    # Recommend parts to keep each part under 20MB
    max_size_per_part_mb = 20
    recommended_parts = max(1, int(total_size_mb / max_size_per_part_mb) + 1)
    recommended_per_part = total // recommended_parts if recommended_parts > 0 else total
    
    return {
        "total_jobs": total,
        "recommended_parts": recommended_parts,
        "recommended_per_part": recommended_per_part,
        "estimated_total_size_mb": round(total_size_mb, 2),
        "estimated_size_per_part_mb": round(total_size_mb / recommended_parts, 2) if recommended_parts > 0 else 0
    }
```

#### Update Export Endpoint

```python
@app.get("/jd/admin/export-jobs")
async def admin_export_jobs(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(2000, ge=1, le=5000),  # Default 2000, max 5000
    offset: int = Query(0, ge=0),
    part: Optional[int] = Query(None, description="Part number (for filename)")
):
    """
    Admin only: Export jobs with pagination.
    
    Use /jd/admin/export-info to plan your export first.
    """
    if request.headers.get("X-User-Role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    total = db.query(Job).filter(Job.status == "active").count()
    
    # ... existing export logic ...
    
    return {
        "count": len(export_data),
        "jobs": export_data,
        "metadata": {
            "exported_at": datetime.utcnow().isoformat(),
            "total_available": total,
            "offset": offset,
            "limit": limit,
            "part": part,
            "has_more": (offset + limit) < total,
            "next_offset": offset + limit if (offset + limit) < total else None
        }
    }
```

### Frontend Implementation

```typescript
// ExportJobsDialog.tsx

interface ExportInfo {
  total_jobs: number;
  recommended_parts: number;
  recommended_per_part: number;
  estimated_total_size_mb: number;
  estimated_size_per_part_mb: number;
}

function ExportJobsDialog() {
  const [exportInfo, setExportInfo] = useState<ExportInfo | null>(null);
  const [numParts, setNumParts] = useState(1);
  const [downloading, setDownloading] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });

  // Load export info
  useEffect(() => {
    api.get('/jd/admin/export-info').then(res => {
      setExportInfo(res.data);
      setNumParts(res.data.recommended_parts);
    });
  }, []);

  const handleExportAll = async () => {
    if (!exportInfo) return;
    
    setDownloading(true);
    const perPart = Math.ceil(exportInfo.total_jobs / numParts);
    
    for (let i = 0; i < numParts; i++) {
      const offset = i * perPart;
      const limit = perPart;
      
      setProgress({ current: i + 1, total: numParts });
      
      try {
        const response = await api.get('/jd/admin/export-jobs', {
          params: { offset, limit, part: i + 1 },
          responseType: 'blob'
        });
        
        // Download file
        const blob = new Blob([JSON.stringify(response.data, null, 2)], {
          type: 'application/json'
        });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `jobs_export_part${i + 1}_of_${numParts}.json`;
        link.click();
        window.URL.revokeObjectURL(url);
        
        // Wait a bit between downloads
        await new Promise(resolve => setTimeout(resolve, 500));
        
      } catch (error) {
        console.error(`Failed to download part ${i + 1}:`, error);
        alert(`Failed to download part ${i + 1}. Please try again.`);
        break;
      }
    }
    
    setDownloading(false);
    setProgress({ current: 0, total: 0 });
  };

  if (!exportInfo) return <div>Loading...</div>;

  return (
    <div className="export-dialog">
      <h2>Export Jobs</h2>
      
      <div className="info">
        <p>Total jobs: {exportInfo.total_jobs.toLocaleString()}</p>
        <p>Estimated size: ~{exportInfo.estimated_total_size_mb}MB</p>
      </div>
      
      <div className="parts-selector">
        <label>
          Split into parts:
          <input
            type="number"
            min="1"
            max="20"
            value={numParts}
            onChange={(e) => setNumParts(parseInt(e.target.value))}
          />
        </label>
        <p className="hint">
          {Math.ceil(exportInfo.total_jobs / numParts)} jobs per part
          (~{(exportInfo.estimated_total_size_mb / numParts).toFixed(1)}MB each)
        </p>
      </div>
      
      {downloading && (
        <div className="progress">
          Downloading part {progress.current} of {progress.total}...
        </div>
      )}
      
      <button
        onClick={handleExportAll}
        disabled={downloading}
      >
        {downloading ? 'Downloading...' : `Download ${numParts} Part${numParts > 1 ? 's' : ''}`}
      </button>
    </div>
  );
}
```

### Import Multiple Parts

```typescript
function ImportJobsDialog() {
  const [files, setFiles] = useState<File[]>([]);
  const [importing, setImporting] = useState(false);
  const [results, setResults] = useState<any[]>([]);

  const handleImportAll = async () => {
    setImporting(true);
    const importResults = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        
        const response = await api.post('/jd/admin/import-jobs-full', data);
        
        importResults.push({
          file: file.name,
          success: true,
          ...response.data
        });
        
      } catch (error) {
        importResults.push({
          file: file.name,
          success: false,
          error: error.message
        });
      }
    }
    
    setResults(importResults);
    setImporting(false);
  };

  return (
    <div className="import-dialog">
      <h2>Import Jobs</h2>
      
      <input
        type="file"
        multiple
        accept=".json"
        onChange={(e) => setFiles(Array.from(e.target.files || []))}
      />
      
      {files.length > 0 && (
        <div className="file-list">
          <p>Selected {files.length} file(s):</p>
          <ul>
            {files.map((f, i) => (
              <li key={i}>{f.name} ({(f.size / 1024 / 1024).toFixed(2)}MB)</li>
            ))}
          </ul>
        </div>
      )}
      
      <button
        onClick={handleImportAll}
        disabled={files.length === 0 || importing}
      >
        {importing ? 'Importing...' : `Import ${files.length} File(s)`}
      </button>
      
      {results.length > 0 && (
        <div className="results">
          <h3>Import Results:</h3>
          {results.map((r, i) => (
            <div key={i} className={r.success ? 'success' : 'error'}>
              <strong>{r.file}:</strong>
              {r.success ? (
                <span>
                  Imported: {r.imported_count}, 
                  Skipped: {r.skipped_count}, 
                  Errors: {r.error_count}
                </span>
              ) : (
                <span>Failed: {r.error}</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

## Advantages

✅ **Simple**: Uses existing pagination
✅ **User Control**: User decides split size
✅ **No Background Jobs**: Synchronous downloads
✅ **Predictable**: Clear file sizes upfront
✅ **Duplicate Safe**: Already handled by DB constraints
✅ **Progress Tracking**: Frontend shows which part downloading
✅ **Resumable**: Can re-download failed parts

## Same for Courses

Apply same pattern to `/recommender/admin/export-courses`
