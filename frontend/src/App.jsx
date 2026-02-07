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
  Clock
} from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '/api';
const MAX_URLS = 5;
const TIMEOUT_SECONDS = 30;

// Error Boundary to catch React crashes
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
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
              className="px-4 py-2 bg-blue-500 text-white rounded-lg"
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

const useCopyToClipboard = () => {
  const [copied, setCopied] = useState(null);

  const copy = useCallback(async (text, id) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        textArea.remove();
      }
      setCopied(id);
      setTimeout(() => setCopied(null), 2000);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  }, []);

  return { copied, copy };
};

const ResultCard = ({ type, icon: Icon, title, items, copied, onCopy, colorClass }) => {
  const [expanded, setExpanded] = useState(true);

  if (!items || !Array.isArray(items) || items.length === 0) return null;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
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
            const displayText = typeof item === 'string' ? item : (item?.formatted || item?.original || item?.username || item?.number || JSON.stringify(item));
            const linkUrl = item?.url || item?.link;

            return (
              <div key={index} className="flex items-center justify-between p-3 hover:bg-gray-50">
                <span className="text-gray-700 truncate flex-1">{displayText}</span>
                <div className="flex items-center gap-2 ml-2">
                  {linkUrl && (
                    <a
                      href={linkUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onCopy(displayText, `${type}-${index}`);
                    }}
                    className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded"
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

function ContactExtractor() {
  const [urls, setUrls] = useState(['']);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');
  const [elapsedTime, setElapsedTime] = useState(0);
  const [debugInfo, setDebugInfo] = useState('');
  const timerRef = useRef(null);
  const abortControllerRef = useRef(null);

  const { copied, copy } = useCopyToClipboard();

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (abortControllerRef.current) abortControllerRef.current.abort();
    };
  }, []);

  const addUrl = () => {
    if (urls.length < MAX_URLS) {
      setUrls([...urls, '']);
    }
  };

  const removeUrl = (index) => {
    if (urls.length > 1) {
      setUrls(urls.filter((_, i) => i !== index));
    }
  };

  const updateUrl = (index, value) => {
    const newUrls = [...urls];
    newUrls[index] = value;
    setUrls(newUrls);
  };

  const handleExtract = async () => {
    const validUrls = urls.map(u => u.trim()).filter(u => u);
    if (validUrls.length === 0) {
      setError('Please enter at least one URL');
      return;
    }

    setLoading(true);
    setError('');
    setResults(null);
    setElapsedTime(0);
    setDebugInfo('Starting extraction...');

    const startTime = Date.now();
    timerRef.current = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setElapsedTime(elapsed);

      if (elapsed >= TIMEOUT_SECONDS) {
        clearInterval(timerRef.current);
        if (abortControllerRef.current) abortControllerRef.current.abort();
        setLoading(false);
        setError(`Request timed out after ${TIMEOUT_SECONDS} seconds. Try a different URL.`);
      }
    }, 1000);

    abortControllerRef.current = new AbortController();

    try {
      const payload = validUrls.length === 1
        ? { url: validUrls[0], max_pages: 2 }
        : { urls: validUrls, max_pages: 2 };

      setDebugInfo(`Calling ${API_URL}/extract...`);

      const response = await axios.post(`${API_URL}/extract`, payload, {
        timeout: TIMEOUT_SECONDS * 1000,
        signal: abortControllerRef.current.signal
      });

      clearInterval(timerRef.current);
      setDebugInfo('Got response');

      const data = response.data;

      if (data.results && Array.isArray(data.results)) {
        setResults(data.results);
      } else if (data.success !== undefined) {
        setResults([data]);
      } else {
        setResults([data]);
      }
    } catch (err) {
      clearInterval(timerRef.current);
      console.error('Extraction error:', err);
      setDebugInfo(`Error: ${err.message}`);

      if (axios.isCancel(err) || err.name === 'AbortError') {
        setError('Request was cancelled');
      } else if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setError('Request timed out. The website might be slow.');
      } else if (err.response?.data?.error) {
        setError(err.response.data.error);
      } else if (err.response?.status === 500) {
        setError('Server error. The website might be blocking requests.');
      } else if (err.response?.status === 404) {
        setError('API not found. Deployment issue.');
      } else {
        setError(`Failed to extract: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    if (timerRef.current) clearInterval(timerRef.current);
    setLoading(false);
    setError('Extraction cancelled');
  };

  const exportCSV = () => {
    if (!results || results.length === 0) return;

    let csv = 'Type,Value,Platform,URL,Source\n';

    results.forEach(result => {
      const source = result?.source_url || '';

      (result?.emails || []).forEach(email => {
        csv += `email,"${email}",,mailto:${email},"${source}"\n`;
      });

      (result?.phones || []).forEach(phone => {
        csv += `phone,"${phone?.formatted || phone?.original || ''}",,tel:${phone?.digits || ''},"${source}"\n`;
      });

      (result?.whatsapp || []).forEach(wa => {
        csv += `whatsapp,"${wa?.number || ''}",whatsapp,"${wa?.link || ''}","${source}"\n`;
      });

      Object.entries(result?.social_links || {}).forEach(([platform, links]) => {
        (links || []).forEach(link => {
          csv += `social,"${link?.username || ''}",${platform},"${link?.url || ''}","${source}"\n`;
        });
      });
    });

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `contacts-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
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
                    placeholder={`Enter website URL ${urls.length > 1 ? `#${index + 1}` : '(e.g., example.com)'}`}
                    className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                    disabled={loading}
                    onKeyDown={(e) => e.key === 'Enter' && !loading && handleExtract()}
                  />
                </div>
                {urls.length > 1 && (
                  <button
                    onClick={() => removeUrl(index)}
                    className="p-3 text-red-500 hover:bg-red-50 rounded-xl"
                    disabled={loading}
                  >
                    <X className="w-5 h-5" />
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-3 mt-4">
            {urls.length < MAX_URLS && (
              <button
                onClick={addUrl}
                className="flex items-center gap-2 px-4 py-2 text-blue-600 hover:bg-blue-50 rounded-lg text-sm font-medium"
                disabled={loading}
              >
                <Plus className="w-4 h-4" />
                Add URL ({urls.length}/{MAX_URLS})
              </button>
            )}

            <div className="flex-1" />

            {loading && (
              <div className="flex items-center gap-2 text-gray-500">
                <Clock className="w-4 h-4" />
                <span className="text-sm font-mono">{elapsedTime}s</span>
              </div>
            )}

            {loading ? (
              <button
                onClick={handleCancel}
                className="px-6 py-3 bg-red-500 hover:bg-red-600 text-white rounded-xl font-medium flex items-center gap-2"
              >
                <X className="w-5 h-5" />
                Cancel
              </button>
            ) : (
              <button
                onClick={handleExtract}
                className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-xl font-medium flex items-center gap-2 shadow-lg shadow-blue-500/25"
              >
                <Search className="w-5 h-5" />
                Extract Contacts
              </button>
            )}
          </div>

          {loading && (
            <div className="mt-4 p-4 bg-blue-50 rounded-xl">
              <div className="flex items-center gap-3">
                <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                <div className="flex-1">
                  <p className="text-blue-800 font-medium">Extracting contacts...</p>
                  <p className="text-blue-600 text-sm">Scanning pages for emails, phones, and social links</p>
                </div>
                <div className="text-right">
                  <p className="text-blue-800 font-mono font-bold">{Math.max(0, TIMEOUT_SECONDS - elapsedTime)}s</p>
                  <p className="text-blue-600 text-xs">remaining</p>
                </div>
              </div>
              <div className="mt-3 h-2 bg-blue-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-1000"
                  style={{ width: `${Math.min(100, (elapsedTime / TIMEOUT_SECONDS) * 100)}%` }}
                />
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-red-800 font-medium">Error</p>
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          </div>
        )}

        {results && Array.isArray(results) && results.length > 0 && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">
                  Found {getTotalCount()} contacts
                </h2>
                <p className="text-sm text-gray-500">
                  From {results.length} website{results.length > 1 ? 's' : ''}
                  {results[0]?.time_taken && ` in ${results[0].time_taken}s`}
                </p>
              </div>
              {getTotalCount() > 0 && (
                <button
                  onClick={exportCSV}
                  className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg font-medium"
                >
                  <Download className="w-4 h-4" />
                  Export CSV
                </button>
              )}
            </div>

            {results.map((result, resultIndex) => (
              <div key={resultIndex} className="space-y-4">
                {results.length > 1 && (
                  <div className="flex items-center gap-2 text-sm">
                    <Globe className="w-4 h-4 text-gray-400" />
                    <span className="font-medium text-gray-700">{result?.source_url || 'Unknown'}</span>
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
                      type="email"
                      icon={Mail}
                      title="Emails"
                      items={result.emails}
                      copied={copied}
                      onCopy={copy}
                      colorClass="bg-blue-100 text-blue-600"
                    />
                    <ResultCard
                      type="phone"
                      icon={Phone}
                      title="Phone Numbers"
                      items={result.phones}
                      copied={copied}
                      onCopy={copy}
                      colorClass="bg-green-100 text-green-600"
                    />
                    <ResultCard
                      type="whatsapp"
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
                          key={platform}
                          type={platform}
                          icon={IconComponent}
                          title={platform.charAt(0).toUpperCase() + platform.slice(1)}
                          items={links}
                          copied={copied}
                          onCopy={copy}
                          colorClass="bg-purple-100 text-purple-600"
                        />
                      );
                    })}

                    {getTotalCount() === 0 && result.success && (
                      <div className="p-4 bg-yellow-50 rounded-xl text-center">
                        <p className="text-yellow-800">No contacts found on this website.</p>
                        <p className="text-yellow-600 text-sm">Try a different URL or a website with a contact page.</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

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
