"""
Contact Extractor API
FastAPI backend for extracting contact information from websites.

Fixed issues:
- Input validation and sanitization
- Proper error handling
- Request size limits
- Timeout handling
- Better response structure
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List, Any
import uuid
import re
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

try:
    import validators
    HAS_VALIDATORS = True
except ImportError:
    HAS_VALIDATORS = False

from app.scraper import extract_contacts

# Constants
MAX_URL_LENGTH = 2000
MAX_URLS_BATCH = 10
MAX_PAGES_LIMIT = 50
REQUEST_TIMEOUT = 120
MAX_REQUEST_SIZE = 10000  # 10KB


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown - cleanup jobs
    jobs.clear()


# Initialize FastAPI app
app = FastAPI(
    title="Contact Extractor API",
    description="Extract contact information (emails, phones, social links) from any website",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,
)

# In-memory storage for async jobs (use Redis in production)
jobs: Dict[str, Dict[str, Any]] = {}


def validate_url(url: str) -> str:
    """Validate and normalize URL."""
    if not url or not isinstance(url, str):
        raise ValueError("URL is required")

    url = url.strip()[:MAX_URL_LENGTH]

    # Remove control characters
    url = re.sub(r'[\x00-\x1f\x7f]', '', url)

    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Validate format
    if HAS_VALIDATORS:
        if not validators.url(url):
            raise ValueError("Invalid URL format")
    else:
        # Basic validation
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not parsed.netloc or len(parsed.netloc) < 3:
            raise ValueError("Invalid URL format")

    # Block local/private IPs
    from urllib.parse import urlparse
    hostname = urlparse(url).netloc.lower().split(':')[0]
    blocked = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
    if hostname in blocked:
        raise ValueError("Local URLs not allowed")

    if hostname.startswith(('192.168.', '10.', '172.16.', '172.17.', '172.18.',
                           '172.19.', '172.20.', '172.21.', '172.22.', '172.23.',
                           '172.24.', '172.25.', '172.26.', '172.27.', '172.28.',
                           '172.29.', '172.30.', '172.31.')):
        raise ValueError("Private IP addresses not allowed")

    return url


# Request/Response Models
class ExtractionRequest(BaseModel):
    """Request model for contact extraction."""
    url: str = Field(..., description="Website URL to extract contacts from", max_length=MAX_URL_LENGTH)
    max_pages: int = Field(default=10, ge=1, le=MAX_PAGES_LIMIT, description="Maximum pages to crawl")
    use_dynamic: bool = Field(default=False, description="Use headless browser for JS sites")
    timeout: int = Field(default=30, ge=5, le=REQUEST_TIMEOUT, description="Request timeout in seconds")

    @field_validator('url')
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str


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


# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": f"Internal server error: {str(exc)[:200]}"
        }
    )


# API Endpoints
@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint - health check."""
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/extract")
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
        # Apply timeout
        result = await asyncio.wait_for(
            extract_contacts(
                url=request.url,
                max_pages=request.max_pages,
                use_dynamic=request.use_dynamic,
                timeout=request.timeout
            ),
            timeout=min(request.timeout + 10, REQUEST_TIMEOUT)
        )

        return {
            "success": True,
            "source_url": result.get('source_url', request.url),
            "pages_scraped": result.get('pages_scraped', 0),
            "emails": result.get('emails', []),
            "phones": result.get('phones', []),
            "whatsapp": result.get('whatsapp', []),
            "social_links": result.get('social_links', {}),
            "names": result.get('names', []),
            "addresses": result.get('addresses', []),
            "extracted_at": datetime.utcnow().isoformat()
        }

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Extraction timed out. The website might be slow or blocking requests."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)[:200]}"
        )


async def run_extraction_job(job_id: str, url: str, max_pages: int, use_dynamic: bool, timeout: int):
    """Background task for async extraction."""
    try:
        result = await asyncio.wait_for(
            extract_contacts(
                url=url,
                max_pages=max_pages,
                use_dynamic=use_dynamic,
                timeout=timeout
            ),
            timeout=min(timeout + 10, REQUEST_TIMEOUT)
        )

        if job_id in jobs:
            jobs[job_id].update({
                'status': 'completed',
                'result': result,
                'completed_at': datetime.utcnow().isoformat()
            })

    except asyncio.TimeoutError:
        if job_id in jobs:
            jobs[job_id].update({
                'status': 'failed',
                'error': 'Extraction timed out',
                'completed_at': datetime.utcnow().isoformat()
            })
    except Exception as e:
        if job_id in jobs:
            jobs[job_id].update({
                'status': 'failed',
                'error': str(e)[:200],
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

    background_tasks.add_task(
        run_extraction_job,
        job_id,
        request.url,
        request.max_pages,
        request.use_dynamic,
        request.timeout
    )

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
async def batch_extract(
    urls: List[str],
    max_pages: int = 5,
    timeout: int = 30
):
    """
    Extract contacts from multiple URLs.

    Returns results for each URL.
    """
    if len(urls) > MAX_URLS_BATCH:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_URLS_BATCH} URLs allowed per batch"
        )

    # Validate and normalize URLs
    validated_urls = []
    for url in urls:
        try:
            validated_urls.append(validate_url(url))
        except ValueError as e:
            validated_urls.append(None)

    results = []
    max_pages = min(max_pages, 10)  # Lower limit for batch
    timeout = min(timeout, 60)  # Lower limit for batch

    for i, url in enumerate(urls):
        if validated_urls[i] is None:
            results.append({
                'url': url,
                'success': False,
                'error': 'Invalid URL'
            })
            continue

        try:
            result = await asyncio.wait_for(
                extract_contacts(
                    url=validated_urls[i],
                    max_pages=max_pages,
                    use_dynamic=False,
                    timeout=timeout
                ),
                timeout=timeout + 10
            )
            results.append({
                'url': url,
                'success': True,
                'data': result
            })
        except asyncio.TimeoutError:
            results.append({
                'url': url,
                'success': False,
                'error': 'Timeout'
            })
        except Exception as e:
            results.append({
                'url': url,
                'success': False,
                'error': str(e)[:100]
            })

    return {
        'total': len(urls),
        'successful': sum(1 for r in results if r.get('success')),
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
        result = await asyncio.wait_for(
            extract_contacts(
                url=request.url,
                max_pages=request.max_pages,
                use_dynamic=request.use_dynamic,
                timeout=request.timeout
            ),
            timeout=min(request.timeout + 10, REQUEST_TIMEOUT)
        )

        # Flatten for spreadsheet
        rows = []
        source_url = result.get('source_url', request.url)

        # Emails
        for email in result.get('emails', []):
            rows.append({
                'type': 'email',
                'value': email,
                'formatted': email,
                'platform': '',
                'link': f'mailto:{email}',
                'source': source_url
            })

        # Phones
        for phone in result.get('phones', []):
            rows.append({
                'type': 'phone',
                'value': phone.get('e164', phone.get('original', '')),
                'formatted': phone.get('formatted', phone.get('original', '')),
                'platform': '',
                'link': f"tel:{phone.get('e164', phone.get('original', ''))}",
                'source': source_url
            })

        # WhatsApp
        for wa in result.get('whatsapp', []):
            rows.append({
                'type': 'whatsapp',
                'value': wa.get('number', ''),
                'formatted': wa.get('number', ''),
                'platform': 'whatsapp',
                'link': wa.get('link', ''),
                'source': source_url
            })

        # Social links
        for platform, links in result.get('social_links', {}).items():
            for link in links:
                rows.append({
                    'type': 'social',
                    'value': link.get('username', ''),
                    'formatted': f"@{link.get('username', '')}",
                    'platform': platform,
                    'link': link.get('url', ''),
                    'source': source_url
                })

        # Names
        for name in result.get('names', []):
            rows.append({
                'type': 'name',
                'value': name,
                'formatted': name,
                'platform': '',
                'link': '',
                'source': source_url
            })

        # Addresses
        for address in result.get('addresses', []):
            rows.append({
                'type': 'address',
                'value': address,
                'formatted': address,
                'platform': '',
                'link': '',
                'source': source_url
            })

        return {
            'success': True,
            'source_url': source_url,
            'pages_scraped': result.get('pages_scraped', 0),
            'total_items': len(rows),
            'rows': rows,
            'summary': {
                'emails': len(result.get('emails', [])),
                'phones': len(result.get('phones', [])),
                'whatsapp': len(result.get('whatsapp', [])),
                'social_links': sum(len(v) for v in result.get('social_links', {}).values()),
                'names': len(result.get('names', [])),
                'addresses': len(result.get('addresses', []))
            }
        }

    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Extraction timed out"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)[:200]}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
