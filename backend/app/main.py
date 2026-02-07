"""
Contact Extractor API
FastAPI backend for extracting contact information from websites.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List, Any
import uuid
from datetime import datetime
import validators

from app.scraper import extract_contacts

# Initialize FastAPI app
app = FastAPI(
    title="Contact Extractor API",
    description="Extract contact information (emails, phones, social links) from any website",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for async jobs (use Redis in production)
jobs: Dict[str, Dict[str, Any]] = {}


# Request/Response Models
class ExtractionRequest(BaseModel):
    """Request model for contact extraction."""
    url: str = Field(..., description="Website URL to extract contacts from")
    max_pages: int = Field(default=10, ge=1, le=50, description="Maximum pages to crawl")
    use_dynamic: bool = Field(default=False, description="Use headless browser for JS sites")
    timeout: int = Field(default=30, ge=5, le=120, description="Request timeout in seconds")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        # Add protocol if missing
        if not v.startswith(('http://', 'https://')):
            v = 'https://' + v

        if not validators.url(v):
            raise ValueError('Invalid URL format')
        return v


class PhoneInfo(BaseModel):
    """Phone number information."""
    e164: str
    formatted: str
    original: str


class WhatsAppInfo(BaseModel):
    """WhatsApp contact information."""
    number: str
    link: str


class SocialLink(BaseModel):
    """Social media link information."""
    username: str
    url: str
    platform: str


class ExtractionResponse(BaseModel):
    """Response model for contact extraction."""
    success: bool
    source_url: str
    pages_scraped: int
    emails: List[str]
    phones: List[Dict[str, str]]
    whatsapp: List[Dict[str, str]]
    social_links: Dict[str, List[Dict[str, str]]]
    names: List[str]
    addresses: List[str]
    extracted_at: str


class JobResponse(BaseModel):
    """Response for async job creation."""
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    """Response for job status check."""
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str


# API Endpoints
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/extract", response_model=ExtractionResponse)
async def extract_contacts_endpoint(request: ExtractionRequest):
    """
    Extract contacts from a website (synchronous).

    This endpoint will crawl the provided website and extract:
    - Email addresses
    - Phone numbers
    - WhatsApp links
    - Social media profiles (Facebook, Twitter, LinkedIn, Instagram, etc.)
    - Contact names
    - Physical addresses

    The extraction happens synchronously, so it may take several seconds
    depending on the website size and complexity.
    """
    try:
        result = await extract_contacts(
            url=request.url,
            max_pages=request.max_pages,
            use_dynamic=request.use_dynamic,
            timeout=request.timeout
        )

        return ExtractionResponse(
            success=True,
            source_url=result['source_url'],
            pages_scraped=result['pages_scraped'],
            emails=result['emails'],
            phones=result['phones'],
            whatsapp=result['whatsapp'],
            social_links=result['social_links'],
            names=result['names'],
            addresses=result['addresses'],
            extracted_at=datetime.utcnow().isoformat()
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


async def run_extraction_job(job_id: str, request: ExtractionRequest):
    """Background task for async extraction."""
    try:
        result = await extract_contacts(
            url=request.url,
            max_pages=request.max_pages,
            use_dynamic=request.use_dynamic,
            timeout=request.timeout
        )

        jobs[job_id].update({
            'status': 'completed',
            'result': result,
            'completed_at': datetime.utcnow().isoformat()
        })

    except Exception as e:
        jobs[job_id].update({
            'status': 'failed',
            'error': str(e),
            'completed_at': datetime.utcnow().isoformat()
        })


@app.post("/extract/async", response_model=JobResponse)
async def extract_contacts_async(
    request: ExtractionRequest,
    background_tasks: BackgroundTasks
):
    """
    Start async contact extraction job.

    Returns a job ID that can be used to check the status
    and retrieve results once complete.
    """
    job_id = str(uuid.uuid4())

    jobs[job_id] = {
        'status': 'pending',
        'url': request.url,
        'created_at': datetime.utcnow().isoformat(),
        'result': None,
        'error': None,
        'completed_at': None
    }

    background_tasks.add_task(run_extraction_job, job_id, request)

    return JobResponse(
        job_id=job_id,
        status='pending',
        message=f'Extraction job started. Poll /extract/status/{job_id} for results.'
    )


@app.get("/extract/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Get the status and result of an async extraction job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=job['status'],
        result=job.get('result'),
        error=job.get('error'),
        created_at=job['created_at'],
        completed_at=job.get('completed_at')
    )


@app.post("/batch-extract")
async def batch_extract(urls: List[str], max_pages: int = 5):
    """
    Extract contacts from multiple URLs.

    Returns results for each URL.
    """
    if len(urls) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 URLs allowed per batch"
        )

    results = []

    for url in urls:
        try:
            # Validate and normalize URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url

            result = await extract_contacts(
                url=url,
                max_pages=max_pages,
                use_dynamic=False,
                timeout=30
            )
            results.append({
                'url': url,
                'success': True,
                'data': result
            })
        except Exception as e:
            results.append({
                'url': url,
                'success': False,
                'error': str(e)
            })

    return {
        'total': len(urls),
        'successful': sum(1 for r in results if r['success']),
        'results': results
    }


# Export for CSV/Sheet format
@app.post("/extract/export")
async def extract_and_export(request: ExtractionRequest):
    """
    Extract contacts and return in spreadsheet-friendly format.

    Returns a flat structure suitable for importing into Google Sheets or Excel.
    """
    try:
        result = await extract_contacts(
            url=request.url,
            max_pages=request.max_pages,
            use_dynamic=request.use_dynamic,
            timeout=request.timeout
        )

        # Flatten for spreadsheet
        rows = []

        # Emails
        for email in result['emails']:
            rows.append({
                'type': 'email',
                'value': email,
                'formatted': email,
                'platform': '',
                'link': f'mailto:{email}',
                'source': result['source_url']
            })

        # Phones
        for phone in result['phones']:
            rows.append({
                'type': 'phone',
                'value': phone.get('e164', phone.get('original')),
                'formatted': phone.get('formatted', phone.get('original')),
                'platform': '',
                'link': f"tel:{phone.get('e164', phone.get('original'))}",
                'source': result['source_url']
            })

        # WhatsApp
        for wa in result['whatsapp']:
            rows.append({
                'type': 'whatsapp',
                'value': wa['number'],
                'formatted': wa['number'],
                'platform': 'whatsapp',
                'link': wa['link'],
                'source': result['source_url']
            })

        # Social links
        for platform, links in result['social_links'].items():
            for link in links:
                rows.append({
                    'type': 'social',
                    'value': link['username'],
                    'formatted': f"@{link['username']}",
                    'platform': platform,
                    'link': link['url'],
                    'source': result['source_url']
                })

        # Names
        for name in result['names']:
            rows.append({
                'type': 'name',
                'value': name,
                'formatted': name,
                'platform': '',
                'link': '',
                'source': result['source_url']
            })

        return {
            'source_url': result['source_url'],
            'pages_scraped': result['pages_scraped'],
            'total_items': len(rows),
            'rows': rows,
            'summary': {
                'emails': len(result['emails']),
                'phones': len(result['phones']),
                'whatsapp': len(result['whatsapp']),
                'social_links': sum(len(v) for v in result['social_links'].values()),
                'names': len(result['names']),
                'addresses': len(result['addresses'])
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
