from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import subprocess
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
import uuid

app = FastAPI(
    title="SecureScope API",
    description="Enterprise SECops Platform for Automated Vulnerability Discovery",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Pydantic models
class ScanRequest(BaseModel):
    domain: str
    scan_type: str = "xss"
    notify_email: Optional[str] = None
    webhook_url: Optional[str] = None

class ScanResponse(BaseModel):
    scan_id: str
    status: str
    message: str

class ScanStatus(BaseModel):
    scan_id: str
    status: str
    progress: int
    results: Optional[Dict] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class VulnerabilityResult(BaseModel):
    id: str
    domain: str
    vulnerability_type: str
    severity: str
    url: str
    parameter: Optional[str] = None
    payload: Optional[str] = None
    confidence: str
    discovered_at: datetime

# In-memory storage (replace with database in production)
scans_db = {}
results_db = {}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "SecureScope API",
        "version": "1.0.0",
        "documentation": "/docs"
    }

@app.post("/api/v1/scans", response_model=ScanResponse)
async def create_scan(
    scan_request: ScanRequest,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new vulnerability scan"""
    
    # Generate unique scan ID
    scan_id = str(uuid.uuid4())
    
    # Store scan in database
    scans_db[scan_id] = ScanStatus(
        scan_id=scan_id,
        status="queued",
        progress=0,
        created_at=datetime.utcnow()
    )
    
    # Start background scan
    background_tasks.add_task(run_scan, scan_id, scan_request.domain, scan_request.scan_type)
    
    return ScanResponse(
        scan_id=scan_id,
        status="queued",
        message=f"Scan queued for domain: {scan_request.domain}"
    )

@app.get("/api/v1/scans/{scan_id}", response_model=ScanStatus)
async def get_scan_status(scan_id: str):
    """Get scan status and progress"""
    
    if scan_id not in scans_db:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    return scans_db[scan_id]

@app.get("/api/v1/scans", response_model=List[ScanStatus])
async def list_scans(
    limit: int = 10,
    offset: int = 0,
    status: Optional[str] = None
):
    """List all scans with pagination"""
    
    scans = list(scans_db.values())
    
    # Filter by status if provided
    if status:
        scans = [scan for scan in scans if scan.status == status]
    
    # Apply pagination
    total = len(scans)
    scans = scans[offset:offset + limit]
    
    return scans

@app.get("/api/v1/scans/{scan_id}/results", response_model=List[VulnerabilityResult])
async def get_scan_results(scan_id: str):
    """Get scan results"""
    
    if scan_id not in scans_db:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    if scan_id not in results_db:
        return []
    
    return results_db[scan_id]

@app.delete("/api/v1/scans/{scan_id}")
async def delete_scan(scan_id: str):
    """Delete a scan and its results"""
    
    if scan_id not in scans_db:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Remove from databases
    del scans_db[scan_id]
    if scan_id in results_db:
        del results_db[scan_id]
    
    return {"message": "Scan deleted successfully"}

@app.get("/api/v1/stats")
async def get_stats():
    """Get platform statistics"""
    
    total_scans = len(scans_db)
    completed_scans = len([s for s in scans_db.values() if s.status == "completed"])
    total_vulnerabilities = sum(len(results) for results in results_db.values())
    
    return {
        "total_scans": total_scans,
        "completed_scans": completed_scans,
        "running_scans": len([s for s in scans_db.values() if s.status == "running"]),
        "total_vulnerabilities": total_vulnerabilities,
        "uptime": "99.9%",  # Mock data
        "last_updated": datetime.utcnow()
    }

async def run_scan(scan_id: str, domain: str, scan_type: str):
    """Background task to run vulnerability scan"""
    
    try:
        # Update scan status
        scans_db[scan_id].status = "running"
        scans_db[scan_id].progress = 10
        
        # Run the actual scan using the original auto_xss.sh script
        result = await execute_scan_script(domain, scan_type)
        
        # Update progress
        scans_db[scan_id].progress = 50
        
        # Parse results
        vulnerabilities = parse_scan_results(scan_id, domain, result)
        
        # Store results
        results_db[scan_id] = vulnerabilities
        
        # Update final status
        scans_db[scan_id].status = "completed"
        scans_db[scan_id].progress = 100
        scans_db[scan_id].completed_at = datetime.utcnow()
        scans_db[scan_id].results = {
            "total_vulnerabilities": len(vulnerabilities),
            "high_severity": len([v for v in vulnerabilities if v.severity == "high"]),
            "medium_severity": len([v for v in vulnerabilities if v.severity == "medium"]),
            "low_severity": len([v for v in vulnerabilities if v.severity == "low"])
        }
        
    except Exception as e:
        # Update scan status on error
        scans_db[scan_id].status = "failed"
        scans_db[scan_id].results = {"error": str(e)}

async def execute_scan_script(domain: str, scan_type: str) -> str:
    """Execute the original auto_xss.sh script"""
    
    try:
        # Create a subprocess to run the scan
        process = await asyncio.create_subprocess_exec(
            "/app/auto_xss.sh", "-u", domain,
            cwd="/app",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"Scan failed: {stderr.decode()}")
        
        return stdout.decode()
        
    except Exception as e:
        raise Exception(f"Failed to execute scan: {str(e)}")

def parse_scan_results(scan_id: str, domain: str, scan_output: str) -> List[VulnerabilityResult]:
    """Parse scan results and convert to structured format"""
    
    vulnerabilities = []
    
    # Try to read the results file generated by auto_xss.sh
    results_file = f"/app/results/{domain}/{domain}_vulnerable_xss.txt"
    
    if os.path.exists(results_file):
        with open(results_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Parse dalfox output format
                    vulnerability = VulnerabilityResult(
                        id=str(uuid.uuid4()),
                        domain=domain,
                        vulnerability_type="XSS",
                        severity="medium",  # Default severity
                        url=line.split()[0] if line.split() else line,
                        confidence="medium",
                        discovered_at=datetime.utcnow()
                    )
                    
                    # Extract additional information if available
                    if "[HIGH]" in line:
                        vulnerability.severity = "high"
                    elif "[LOW]" in line:
                        vulnerability.severity = "low"
                    
                    vulnerabilities.append(vulnerability)
    
    return vulnerabilities

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)