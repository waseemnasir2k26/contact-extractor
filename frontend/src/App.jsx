import React, { useState, useCallback, useEffect, useRef, Component } from 'react';
import {
  Search,
  Mail,
  Phone,
  MessageCircle,
  Globe,
  Copy,
  Check,
  ExternalLink,
  Download,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Linkedin,
  Twitter,
  Facebook,
  Instagram,
  Youtube,
  Github,
  Send,
  Music2,
  Plus,
  X,
  Clock,
  RefreshCw
} from 'lucide-react';
import axios from 'axios';

// Configuration
const API_URL = import.meta.env.VITE_API_URL || '/api';
const MAX_URLS = 5;
const REQUEST_TIMEOUT = 25000; // 25 seconds
const MAX_RETRIES = 1;
const RETRY_DELAY = 1000; // 1 second

// Error Boundary to catch React crashes
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-red-50 p-4">
          <div className="bg-white p-6 rounded-xl shadow-lg max-w-md">
            <h2 className="text-xl font-bold text-red-600 mb-2">Something went wrong</h2>
            <p className="text-gray-600 mb-4">{this.state.error?.message || 'Unknown error'}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const socialIcons = {
  linkedin: Linkedin,
  twitter: Twitter,
  facebook: Facebook,
  instagram: Instagram,
  youtube: Youtube,
  github: Github,
  telegram: Send,
  tiktok: Music2,
  pinterest: Globe,
};

// URL validation helper
const isValidUrl = (url) => {
  if (!url || typeof url !== 'string') return false;
  const trimmed = url.trim();
  if (trimmed.length < 4) return false;

  // Check for basic structure
  const urlPattern = /^(https?:\/\/)?([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(\/.*)?$/;
  return urlPattern.test(trimmed);
};

// Normalize URL - add https:// if missing
const normalizeUrl = (url) => {
  if (!url) return '';
  let trimmed = url.trim();
  if (!trimmed) return '';
  if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
    trimmed = 'https://' + trimmed;
  }
  return trimmed;
};

// Copy to clipboard hook
const useCopyToClipboard = () => {
  const [copied, setCopied] = useState(null);
  const timeoutRef = useRef(null);

  const copy = useCallback(async (text, id) => {
    try {
      // Clear any existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        // Fallback for non-secure contexts
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        textArea.remove();
      }
      setCopied(id);
      timeoutRef.current = setTimeout(() => setCopied(null), 2000);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return { copied, copy };
};

// Result card component
const ResultCard = ({ type, icon: Icon, title, items, copied, onCopy, colorClass }) => {
  const [expanded, setExpanded] = useState(true);

  if (!items || !Array.isArray(items) || items.length === 0) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${colorClass}`}>
            <Icon className="w-5 h-5" />
          </div>
          <span className="font-medium text-gray-900">{title}</span>
          <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-sm rounded-full">
            {items.length}
          </span>
        </div>
        {expanded ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
      </div>

      {expanded && (
        <div className="border-t border-gray-100 divide-y divide-gray-50">
          {items.map((item, index) => {
            const displayText = typeof item === 'string'
              ? item
              : (item?.formatted || item?.original || item?.username || item?.number || String(item));
            const linkUrl = item?.url || item?.link;

            return (
              <div key={`${type}-${index}`} className="flex items-center justify-between p-3 hover:bg-gray-50 transition-colors">
                <span className="text-gray-700 truncate flex-1 font-mono text-sm">{displayText}</span>
                <div className="flex items-center gap-2 ml-2 flex-shrink-0">
                  {linkUrl && (
                    <a
                      href={linkUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
                      onClick={(e) => e.stopPropagation()}
                      title="Open link"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onCopy(displayText, `${type}-${index}`);
                    }}
                    className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded transition-colors"
                    title="Copy to clipboard"
                  >
                    {copied === `${type}-${index}` ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// Parse error for user-friendly message
const parseError = (err) => {
  if (axios.isCancel(err) || err.name === 'CanceledError' || err.name === 'AbortError') {
    return { type: 'cancelled', message: 'Request was cancelled' };
  }

  if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
    return { type: 'timeout', message: 'Request timed out. The website might be slow or blocking requests.' };
  }

  if (err.response) {
    const status = err.response.status;
    const serverError = err.response.data?.error;

    if (status === 404) {
      return { type: 'not_found', message: 'API endpoint not found. Please check deployment.' };
    }
    if (status === 429) {
      return { type: 'rate_limit', message: 'Too many requests. Please wait a moment and try again.' };
    }
    if (status === 500) {
      return { type: 'server_error', message: serverError || 'Server error. The website might be blocking requests.' };
    }
    if (status === 502 || status === 503 || status === 504) {
      return { type: 'gateway_error', message: 'Server temporarily unavailable. Please try again.' };
    }

    return { type: 'http_error', message: serverError || `Request failed (HTTP ${status})` };
  }

  if (err.request) {
    return { type: 'network', message: 'Network error. Please check your internet connection.' };
  }

  return { type: 'unknown', message: err.message || 'An unexpected error occurred' };
};

// Sleep helper for retry delay
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

function ContactExtractor() {
  const [urls, setUrls] = useState(['']);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [retryCount, setRetryCount] = useState(0);

  const timerRef = useRef(null);
  const abortControllerRef = useRef(null);
  const mountedRef = useRef(true);

  const { copied, copy } = useCopyToClipboard();

  // Track mounted state for cleanup
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      cleanup();
    };
  }, []);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  // URL management
  const addUrl = () => {
    if (urls.length < MAX_URLS) {
      setUrls(prev => [...prev, '']);
    }
  };

  const removeUrl = (index) => {
    if (urls.length > 1) {
      setUrls(prev => prev.filter((_, i) => i !== index));
    }
  };

  const updateUrl = (index, value) => {
    setUrls(prev => {
      const newUrls = [...prev];
      newUrls[index] = value;
      return newUrls;
    });
  };

  // Make API request with retry logic
  const makeRequest = async (payload, retries = 0) => {
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await axios.post(`${API_URL}/extract`, payload, {
        timeout: REQUEST_TIMEOUT,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      });

      return response.data;
    } catch (err) {
      // Don't retry if cancelled
      if (axios.isCancel(err) || err.name === 'AbortError') {
        throw err;
      }

      // Retry on certain errors
      const { type } = parseError(err);
      const shouldRetry = retries < MAX_RETRIES &&
        ['timeout', 'network', 'gateway_error'].includes(type);

      if (shouldRetry) {
        if (mountedRef.current) {
          setRetryCount(retries + 1);
        }
        await sleep(RETRY_DELAY * (retries + 1)); // Exponential backoff

        // Check if still mounted and not cancelled
        if (!mountedRef.current || !abortControllerRef.current) {
          throw err;
        }

        return makeRequest(payload, retries + 1);
      }

      throw err;
    }
  };

  // Extract handler
  const handleExtract = async () => {
    // Validate URLs
    const validUrls = urls
      .map(u => normalizeUrl(u))
      .filter(u => u && isValidUrl(u));

    if (validUrls.length === 0) {
      setError({ type: 'validation', message: 'Please enter at least one valid URL (e.g., example.com)' });
      return;
    }

    // Reset state
    cleanup();
    setLoading(true);
    setError(null);
    setResults(null);
    setElapsedTime(0);
    setRetryCount(0);

    // Start timer
    const startTime = Date.now();
    timerRef.current = setInterval(() => {
      if (mountedRef.current) {
        setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
      }
    }, 1000);

    try {
      // Build payload
      const payload = validUrls.length === 1
        ? { url: validUrls[0], max_pages: 2 }
        : { urls: validUrls, max_pages: 2 };

      const data = await makeRequest(payload);

      // Process response
      if (mountedRef.current) {
        let resultArray = [];
        if (data.results && Array.isArray(data.results)) {
          resultArray = data.results;
        } else if (data) {
          resultArray = [data];
        }

        setResults(resultArray);
        setError(null);
      }
    } catch (err) {
      if (mountedRef.current) {
        const parsedError = parseError(err);
        setError(parsedError);
        setResults(null);
      }
    } finally {
      // Always cleanup timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }

      if (mountedRef.current) {
        setLoading(false);
        setRetryCount(0);
      }
    }
  };

  // Cancel handler
  const handleCancel = () => {
    cleanup();
    setLoading(false);
    setError({ type: 'cancelled', message: 'Extraction cancelled' });
  };

  // Export to CSV
  const exportCSV = () => {
    if (!results || results.length === 0) return;

    const rows = ['Type,Value,Platform,URL,Source'];

    results.forEach(result => {
      if (!result) return;
      const source = result.source_url || '';

      (result.emails || []).forEach(email => {
        rows.push(`email,"${email}",,mailto:${email},"${source}"`);
      });

      (result.phones || []).forEach(phone => {
        const value = phone?.formatted || phone?.original || '';
        const e164 = phone?.e164 || phone?.original || '';
        rows.push(`phone,"${value}",,tel:${e164},"${source}"`);
      });

      (result.whatsapp || []).forEach(wa => {
        rows.push(`whatsapp,"${wa?.number || ''}",whatsapp,"${wa?.link || ''}","${source}"`);
      });

      Object.entries(result.social_links || {}).forEach(([platform, links]) => {
        (links || []).forEach(link => {
          rows.push(`social,"${link?.username || ''}",${platform},"${link?.url || ''}","${source}"`);
        });
      });
    });

    const csv = rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `contacts-${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Calculate total count
  const getTotalCount = () => {
    if (!results || !Array.isArray(results)) return 0;
    return results.reduce((total, r) => {
      if (!r) return total;
      return total +
        (r.emails?.length || 0) +
        (r.phones?.length || 0) +
        (r.whatsapp?.length || 0) +
        Object.values(r.social_links || {}).reduce((sum, arr) => sum + (arr?.length || 0), 0);
    }, 0);
  };

  const totalCount = getTotalCount();
  const maxTime = Math.ceil(REQUEST_TIMEOUT / 1000);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-100 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl">
              <Search className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Contact Extractor</h1>
              <p className="text-sm text-gray-500">Extract emails, phones & social links</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Input section */}
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 mb-8">
          <div className="space-y-3">
            {urls.map((url, index) => (
              <div key={index} className="flex gap-2">
                <div className="flex-1 relative">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="text"
                    value={url}
                    onChange={(e) => updateUrl(index, e.target.value)}
                    placeholder={urls.length > 1 ? `Website URL #${index + 1}` : 'Enter website URL (e.g., example.com)'}
                    className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                    disabled={loading}
                    onKeyDown={(e) => e.key === 'Enter' && !loading && handleExtract()}
                  />
                </div>
                {urls.length > 1 && (
                  <button
                    onClick={() => removeUrl(index)}
                    className="p-3 text-red-500 hover:bg-red-50 rounded-xl transition-colors"
                    disabled={loading}
                    title="Remove URL"
                  >
                    <X className="w-5 h-5" />
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-3 mt-4">
            {urls.length < MAX_URLS && (
              <button
                onClick={addUrl}
                className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg text-sm font-medium transition-colors"
                disabled={loading}
              >
                <Plus className="w-4 h-4" />
                Add URL ({urls.length}/{MAX_URLS})
              </button>
            )}

            <div className="flex-1" />

            {/* Timer display */}
            {loading && (
              <div className="flex items-center gap-2 text-gray-500">
                <Clock className="w-4 h-4" />
                <span className="text-sm font-mono">{elapsedTime}s</span>
                {retryCount > 0 && (
                  <span className="flex items-center gap-1 text-orange-500">
                    <RefreshCw className="w-3 h-3" />
                    Retry {retryCount}
                  </span>
                )}
              </div>
            )}

            {/* Extract/Cancel button */}
            {loading ? (
              <button
                onClick={handleCancel}
                className="px-6 py-3 bg-red-500 hover:bg-red-600 text-white rounded-xl font-medium flex items-center gap-2 transition-colors"
              >
                <X className="w-5 h-5" />
                Cancel
              </button>
            ) : (
              <button
                onClick={handleExtract}
                className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-xl font-medium flex items-center gap-2 shadow-lg shadow-blue-500/25 transition-all"
              >
                <Search className="w-5 h-5" />
                Extract Contacts
              </button>
            )}
          </div>

          {/* Loading indicator */}
          {loading && (
            <div className="mt-4 p-4 bg-blue-50 rounded-xl">
              <div className="flex items-center gap-3">
                <Loader2 className="w-5 h-5 text-blue-600 animate-spin flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-blue-800 font-medium">
                    {retryCount > 0 ? 'Retrying...' : 'Extracting contacts...'}
                  </p>
                  <p className="text-blue-600 text-sm truncate">Scanning pages for emails, phones, and social links</p>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-blue-800 font-mono font-bold">{Math.max(0, maxTime - elapsedTime)}s</p>
                  <p className="text-blue-600 text-xs">remaining</p>
                </div>
              </div>
              <div className="mt-3 h-2 bg-blue-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-1000"
                  style={{ width: `${Math.min(100, (elapsedTime / maxTime) * 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Error display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="min-w-0">
              <p className="text-red-800 font-medium">
                {error.type === 'timeout' ? 'Timeout' :
                 error.type === 'network' ? 'Network Error' :
                 error.type === 'validation' ? 'Invalid Input' :
                 error.type === 'cancelled' ? 'Cancelled' :
                 'Error'}
              </p>
              <p className="text-red-600 text-sm break-words">{error.message}</p>
            </div>
          </div>
        )}

        {/* Results display */}
        {results && Array.isArray(results) && results.length > 0 && (
          <div className="space-y-6">
            {/* Results header */}
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Found {totalCount} contact{totalCount !== 1 ? 's' : ''}
                </h2>
                <p className="text-sm text-gray-500">
                  From {results.length} website{results.length > 1 ? 's' : ''}
                  {results[0]?.time_taken && ` in ${results[0].time_taken}s`}
                </p>
              </div>
              {totalCount > 0 && (
                <button
                  onClick={exportCSV}
                  className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Export CSV
                </button>
              )}
            </div>

            {/* Results list */}
            {results.map((result, resultIndex) => (
              <div key={resultIndex} className="space-y-4">
                {results.length > 1 && (
                  <div className="flex items-center gap-2 text-sm flex-wrap">
                    <Globe className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <span className="font-medium text-gray-700 truncate">{result?.source_url || 'Unknown'}</span>
                    {result?.time_taken && (
                      <span className="text-gray-400">({result.time_taken}s)</span>
                    )}
                    {result?.error && (
                      <span className="text-red-500">- {result.error}</span>
                    )}
                  </div>
                )}

                {result && result.success !== false && (
                  <div className="grid gap-4">
                    <ResultCard
                      type={`email-${resultIndex}`}
                      icon={Mail}
                      title="Emails"
                      items={result.emails}
                      copied={copied}
                      onCopy={copy}
                      colorClass="bg-blue-100 text-blue-600"
                    />
                    <ResultCard
                      type={`phone-${resultIndex}`}
                      icon={Phone}
                      title="Phone Numbers"
                      items={result.phones}
                      copied={copied}
                      onCopy={copy}
                      colorClass="bg-green-100 text-green-600"
                    />
                    <ResultCard
                      type={`whatsapp-${resultIndex}`}
                      icon={MessageCircle}
                      title="WhatsApp"
                      items={result.whatsapp}
                      copied={copied}
                      onCopy={copy}
                      colorClass="bg-emerald-100 text-emerald-600"
                    />

                    {result.social_links && Object.entries(result.social_links).map(([platform, links]) => {
                      if (!links || !Array.isArray(links) || links.length === 0) return null;
                      const IconComponent = socialIcons[platform] || Globe;
                      return (
                        <ResultCard
                          key={`${platform}-${resultIndex}`}
                          type={`${platform}-${resultIndex}`}
                          icon={IconComponent}
                          title={platform.charAt(0).toUpperCase() + platform.slice(1)}
                          items={links}
                          copied={copied}
                          onCopy={copy}
                          colorClass="bg-purple-100 text-purple-600"
                        />
                      );
                    })}
                  </div>
                )}

                {/* No results message */}
                {result && result.success !== false && totalCount === 0 && (
                  <div className="p-4 bg-yellow-50 rounded-xl text-center">
                    <p className="text-yellow-800">No contacts found on this website.</p>
                    <p className="text-yellow-600 text-sm">Try a different URL or a website with a contact page.</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && !results && !error && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Ready to extract contacts</h3>
            <p className="text-gray-500 max-w-md mx-auto">
              Enter up to {MAX_URLS} website URLs above to extract emails, phone numbers, WhatsApp links, and social media profiles.
            </p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-100 mt-12 py-6">
        <div className="max-w-4xl mx-auto px-4 text-center text-sm text-gray-500">
          <p>Free to use. No login required. No data stored.</p>
        </div>
      </footer>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ContactExtractor />
    </ErrorBoundary>
  );
}

export default App;
