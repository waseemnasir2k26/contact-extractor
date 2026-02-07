import React, { useState, useCallback } from 'react';
import {
  Search,
  Mail,
  Phone,
  MessageCircle,
  Globe,
  User,
  MapPin,
  Copy,
  Check,
  ExternalLink,
  Download,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronUp,
  Settings,
  Linkedin,
  Twitter,
  Facebook,
  Instagram,
  Youtube,
  Github,
  Send,
  Music2
} from 'lucide-react';
import axios from 'axios';

// API configuration
const API_URL = import.meta.env.VITE_API_URL || '/api';

// Social media icons mapping
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

// Copy to clipboard hook with fallback
const useCopyToClipboard = () => {
  const [copied, setCopied] = useState(null);

  const copy = useCallback(async (text, id) => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        // Fallback for non-HTTPS contexts
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
      setTimeout(() => setCopied(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, []);

  return { copied, copy };
};

// Result Card Component
const ResultCard = ({ type, icon: Icon, title, items, copied, onCopy }) => {
  const [expanded, setExpanded] = useState(true);

  if (!items || items.length === 0) return null;

  const badgeClass = {
    email: 'badge-email',
    phone: 'badge-phone',
    whatsapp: 'badge-whatsapp',
    social: 'badge-social',
    name: 'bg-orange-100 text-orange-800',
    address: 'bg-gray-100 text-gray-800',
  }[type] || 'badge-social';

  return (
    <div className="result-card fade-in">
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${type === 'email' ? 'bg-blue-100' : type === 'phone' ? 'bg-green-100' : type === 'whatsapp' ? 'bg-emerald-100' : 'bg-purple-100'}`}>
            <Icon className={`w-5 h-5 ${type === 'email' ? 'text-blue-600' : type === 'phone' ? 'text-green-600' : type === 'whatsapp' ? 'text-emerald-600' : 'text-purple-600'}`} />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">{title}</h3>
            <span className={`badge ${badgeClass}`}>{items.length} found</span>
          </div>
        </div>
        {expanded ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
      </div>

      {expanded && (
        <div className="mt-4 space-y-2">
          {items.map((item, idx) => {
            const displayValue = typeof item === 'string' ? item : item.formatted || item.value || item.username;
            const copyValue = typeof item === 'string' ? item : item.e164 || item.number || item.value || item.url;
            const link = typeof item === 'string' ? null : item.link || item.url;
            const itemId = `${type}-${idx}`;

            return (
              <div
                key={idx}
                className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-100 hover:border-primary-200 transition-all"
              >
                <div className="flex items-center gap-3 overflow-hidden">
                  {item.platform && socialIcons[item.platform] && (
                    React.createElement(socialIcons[item.platform], {
                      className: 'w-4 h-4 text-gray-500 flex-shrink-0'
                    })
                  )}
                  <span className="text-gray-700 truncate">{displayValue}</span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {link && (
                    <a
                      href={link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 text-gray-400 hover:text-primary-600 transition-colors"
                      title="Open link"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                  )}
                  <button
                    onClick={() => onCopy(copyValue, itemId)}
                    className="p-2 text-gray-400 hover:text-primary-600 transition-colors"
                    title="Copy to clipboard"
                  >
                    {copied === itemId ? (
                      <Check className="w-4 h-4 text-green-500" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
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

// Social Links Section
const SocialLinksSection = ({ socialLinks, copied, onCopy }) => {
  const [expanded, setExpanded] = useState(true);

  const allLinks = Object.entries(socialLinks).flatMap(([platform, links]) =>
    links.map(link => ({ ...link, platform }))
  );

  if (allLinks.length === 0) return null;

  return (
    <div className="result-card fade-in">
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-purple-100">
            <Globe className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Social Media</h3>
            <span className="badge badge-social">{allLinks.length} profiles</span>
          </div>
        </div>
        {expanded ? <ChevronUp className="w-5 h-5 text-gray-400" /> : <ChevronDown className="w-5 h-5 text-gray-400" />}
      </div>

      {expanded && (
        <div className="mt-4 space-y-2">
          {allLinks.map((link, idx) => {
            const SocialIcon = socialIcons[link.platform] || Globe;
            const itemId = `social-${idx}`;

            return (
              <div
                key={idx}
                className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-100 hover:border-primary-200 transition-all"
              >
                <div className="flex items-center gap-3 overflow-hidden">
                  <SocialIcon className="w-5 h-5 text-gray-500 flex-shrink-0" />
                  <div className="overflow-hidden">
                    <span className="text-gray-700 font-medium capitalize">{link.platform}</span>
                    <p className="text-gray-500 text-sm truncate">@{link.username}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 text-gray-400 hover:text-primary-600 transition-colors"
                    title="Open profile"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                  <button
                    onClick={() => onCopy(link.url, itemId)}
                    className="p-2 text-gray-400 hover:text-primary-600 transition-colors"
                    title="Copy URL"
                  >
                    {copied === itemId ? (
                      <Check className="w-4 h-4 text-green-500" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
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

// Main App Component
function App() {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState({
    maxPages: 10,
    useDynamic: false,
    timeout: 30
  });

  const { copied, copy } = useCopyToClipboard();

  const handleExtract = async (e) => {
    e.preventDefault();

    if (!url.trim()) {
      setError('Please enter a website URL');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await axios.post(`${API_URL}/extract`, {
        url: url.trim(),
        max_pages: settings.maxPages,
        use_dynamic: settings.useDynamic,
        timeout: settings.timeout
      });

      setResults(response.data);
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to extract contacts';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (!results) return;

    const rows = [
      ['Type', 'Value', 'Platform', 'Link', 'Source']
    ];

    // Emails
    results.emails.forEach(email => {
      rows.push(['Email', email, '', `mailto:${email}`, results.source_url]);
    });

    // Phones
    results.phones.forEach(phone => {
      rows.push(['Phone', phone.formatted || phone.original, '', `tel:${phone.e164 || phone.original}`, results.source_url]);
    });

    // WhatsApp
    results.whatsapp.forEach(wa => {
      rows.push(['WhatsApp', wa.number, 'whatsapp', wa.link, results.source_url]);
    });

    // Social links
    Object.entries(results.social_links).forEach(([platform, links]) => {
      links.forEach(link => {
        rows.push(['Social', `@${link.username}`, platform, link.url, results.source_url]);
      });
    });

    // Names
    results.names.forEach(name => {
      rows.push(['Name', name, '', '', results.source_url]);
    });

    // Convert to CSV
    const csv = rows.map(row =>
      row.map(cell => `"${(cell || '').replace(/"/g, '""')}"`).join(',')
    ).join('\n');

    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const downloadUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = `contacts-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(downloadUrl);
  };

  const copyAllToClipboard = () => {
    if (!results) return;

    const lines = [];

    if (results.emails.length > 0) {
      lines.push('EMAILS:');
      results.emails.forEach(e => lines.push(e));
      lines.push('');
    }

    if (results.phones.length > 0) {
      lines.push('PHONES:');
      results.phones.forEach(p => lines.push(p.formatted || p.original));
      lines.push('');
    }

    if (results.whatsapp.length > 0) {
      lines.push('WHATSAPP:');
      results.whatsapp.forEach(w => lines.push(w.link));
      lines.push('');
    }

    Object.entries(results.social_links).forEach(([platform, links]) => {
      if (links.length > 0) {
        lines.push(`${platform.toUpperCase()}:`);
        links.forEach(l => lines.push(l.url));
        lines.push('');
      }
    });

    navigator.clipboard.writeText(lines.join('\n'));
    copy('all', 'all-contacts');
  };

  const totalContacts = results ? (
    results.emails.length +
    results.phones.length +
    results.whatsapp.length +
    Object.values(results.social_links).flat().length +
    results.names.length
  ) : 0;

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-white/20 backdrop-blur-lg rounded-2xl mb-4">
            <Search className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
            Contact Extractor
          </h1>
          <p className="text-white/80 text-lg">
            Extract emails, phones & social links from any website
          </p>
        </div>

        {/* Search Form */}
        <form onSubmit={handleExtract} className="card mb-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Globe className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Enter website URL (e.g., example.com)"
                className="input-field pl-12"
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary flex items-center justify-center gap-2 min-w-[140px]"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Extracting...
                </>
              ) : (
                <>
                  <Search className="w-5 h-5" />
                  Extract
                </>
              )}
            </button>
          </div>

          {/* Settings Toggle */}
          <div className="mt-4">
            <button
              type="button"
              onClick={() => setShowSettings(!showSettings)}
              className="flex items-center gap-2 text-gray-500 hover:text-gray-700 text-sm"
            >
              <Settings className="w-4 h-4" />
              Advanced Settings
              {showSettings ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {showSettings && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Max Pages
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="50"
                    value={settings.maxPages}
                    onChange={(e) => setSettings({ ...settings, maxPages: parseInt(e.target.value) || 10 })}
                    className="input-field text-sm py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Timeout (seconds)
                  </label>
                  <input
                    type="number"
                    min="5"
                    max="120"
                    value={settings.timeout}
                    onChange={(e) => setSettings({ ...settings, timeout: parseInt(e.target.value) || 30 })}
                    className="input-field text-sm py-2"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    JavaScript Sites
                  </label>
                  <label className="flex items-center gap-2 mt-2">
                    <input
                      type="checkbox"
                      checked={settings.useDynamic}
                      onChange={(e) => setSettings({ ...settings, useDynamic: e.target.checked })}
                      className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                    <span className="text-sm text-gray-600">Use headless browser</span>
                  </label>
                </div>
              </div>
            )}
          </div>
        </form>

        {/* Error Message */}
        {error && (
          <div className="card mb-6 border-l-4 border-red-500 bg-red-50 fade-in">
            <div className="flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
              <p className="text-red-700">{error}</p>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="card text-center py-12">
            <div className="loader mx-auto mb-4"></div>
            <p className="text-gray-600 font-medium">Extracting contacts...</p>
            <p className="text-gray-400 text-sm mt-1">This may take a moment</p>
          </div>
        )}

        {/* Results */}
        {results && !loading && (
          <div className="space-y-4 fade-in">
            {/* Summary Card */}
            <div className="card">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    Extraction Complete
                  </h2>
                  <p className="text-gray-500 text-sm mt-1">
                    Found {totalContacts} contacts from {results.pages_scraped} pages
                  </p>
                  <p className="text-gray-400 text-xs mt-1 truncate">
                    Source: {results.source_url}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={copyAllToClipboard}
                    className="btn-secondary flex items-center gap-2"
                  >
                    {copied === 'all-contacts' ? (
                      <Check className="w-4 h-4 text-green-500" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                    Copy All
                  </button>
                  <button
                    onClick={handleExportCSV}
                    className="btn-secondary flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    Export CSV
                  </button>
                </div>
              </div>

              {/* Quick Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
                <div className="p-4 rounded-lg bg-blue-50 text-center">
                  <Mail className="w-6 h-6 text-blue-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-blue-700">{results.emails.length}</div>
                  <div className="text-sm text-blue-600">Emails</div>
                </div>
                <div className="p-4 rounded-lg bg-green-50 text-center">
                  <Phone className="w-6 h-6 text-green-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-green-700">{results.phones.length}</div>
                  <div className="text-sm text-green-600">Phones</div>
                </div>
                <div className="p-4 rounded-lg bg-emerald-50 text-center">
                  <MessageCircle className="w-6 h-6 text-emerald-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-emerald-700">{results.whatsapp.length}</div>
                  <div className="text-sm text-emerald-600">WhatsApp</div>
                </div>
                <div className="p-4 rounded-lg bg-purple-50 text-center">
                  <Globe className="w-6 h-6 text-purple-600 mx-auto mb-2" />
                  <div className="text-2xl font-bold text-purple-700">{Object.values(results.social_links).flat().length}</div>
                  <div className="text-sm text-purple-600">Social</div>
                </div>
              </div>
            </div>

            {/* Email Results */}
            <ResultCard
              type="email"
              icon={Mail}
              title="Email Addresses"
              items={results.emails}
              copied={copied}
              onCopy={copy}
            />

            {/* Phone Results */}
            <ResultCard
              type="phone"
              icon={Phone}
              title="Phone Numbers"
              items={results.phones}
              copied={copied}
              onCopy={copy}
            />

            {/* WhatsApp Results */}
            <ResultCard
              type="whatsapp"
              icon={MessageCircle}
              title="WhatsApp Contacts"
              items={results.whatsapp}
              copied={copied}
              onCopy={copy}
            />

            {/* Social Links */}
            <SocialLinksSection
              socialLinks={results.social_links}
              copied={copied}
              onCopy={copy}
            />

            {/* Names */}
            <ResultCard
              type="name"
              icon={User}
              title="Contact Names"
              items={results.names}
              copied={copied}
              onCopy={copy}
            />

            {/* Addresses */}
            <ResultCard
              type="address"
              icon={MapPin}
              title="Physical Addresses"
              items={results.addresses}
              copied={copied}
              onCopy={copy}
            />

            {/* No Results Message */}
            {totalContacts === 0 && (
              <div className="card text-center py-8">
                <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-700">No contacts found</h3>
                <p className="text-gray-500 mt-1">
                  Try enabling JavaScript rendering or check if the website has a contact page.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-12 text-white/60 text-sm">
          <p>Contact Extractor - Extract publicly available contact information</p>
          <p className="mt-1">No AI APIs required - 100% self-hosted</p>
        </div>
      </div>
    </div>
  );
}

export default App;
