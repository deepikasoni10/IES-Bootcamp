import { useState } from 'react';
import { Copy, Check } from 'lucide-react';

function colorize(json) {
  return json.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    (match) => {
      if (/^"/.test(match)) {
        if (/:$/.test(match)) return `<span class="json-key">${match}</span>`;
        return `<span class="json-string">${match}</span>`;
      }
      if (/true|false/.test(match)) return `<span class="json-bool">${match}</span>`;
      if (/null/.test(match))       return `<span class="json-null">${match}</span>`;
      return `<span class="json-number">${match}</span>`;
    }
  );
}

export default function JsonViewer({ data, maxHeight = '400px', title }) {
  const [copied, setCopied] = useState(false);
  const json = JSON.stringify(data, null, 2);

  const copy = () => {
    navigator.clipboard.writeText(json);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-xl overflow-hidden border border-slate-700/50">
      {title && (
        <div className="flex items-center justify-between px-4 py-2.5 bg-slate-800/80 border-b border-slate-700/50">
          <span className="text-xs font-semibold text-slate-400 tracking-wider uppercase">{title}</span>
          <button onClick={copy} className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-200 transition-colors">
            {copied ? <><Check size={12} className="text-emerald-400" /><span className="text-emerald-400">Copied!</span></> : <><Copy size={12} /><span>Copy</span></>}
          </button>
        </div>
      )}
      <div className="overflow-auto bg-[#0d1424]" style={{ maxHeight }}>
        <pre
          className="p-4 text-xs font-mono leading-relaxed text-slate-300"
          dangerouslySetInnerHTML={{ __html: colorize(json) }}
        />
      </div>
    </div>
  );
}
