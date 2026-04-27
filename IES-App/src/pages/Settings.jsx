import { useState } from 'react';
import { Shield, Globe, Key, Bell, Save, CheckCircle2, RefreshCw, Wifi } from 'lucide-react';
import Header from '../components/layout/Header';
import { DISCOM_INFO } from '../data/mockData';

function Section({ title, icon: Icon, children }) {
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-800 bg-slate-800/40">
        <Icon size={16} className="text-blue-400" />
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

function Field({ label, value, mono, editable, onChange, type = 'text', hint }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-semibold text-slate-400">{label}</label>
      {editable ? (
        <input type={type} value={value} onChange={e => onChange?.(e.target.value)} className="input text-sm" />
      ) : (
        <div className={`px-4 py-2.5 rounded-lg bg-slate-800/60 text-sm border border-slate-700/50 ${mono ? 'font-mono text-slate-300' : 'text-slate-300'}`}>
          {value}
        </div>
      )}
      {hint && <p className="text-xs text-slate-600">{hint}</p>}
    </div>
  );
}

export default function Settings() {
  const [saved, setSaved] = useState(false);
  const [bapUrl, setBapUrl] = useState('https://infosys-bap.sandbox.ies/callback');
  const [domain, setDomain] = useState('ies:regulatory');
  const [notifyEmail, setNotifyEmail] = useState('rahul.sharma@infosys.com');

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="animate-fade-in">
      <Header title="Settings" subtitle="DISCOM configuration, credentials, and network settings" />

      <div className="p-6 space-y-5 max-w-3xl">

        {/* DISCOM Identity */}
        <Section title="DISCOM Identity" icon={Shield}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="DISCOM Name"      value={DISCOM_INFO.name}         mono={false} />
            <Field label="Short Name"       value={DISCOM_INFO.short}        mono={false} />
            <Field label="Participant ID"   value={DISCOM_INFO.id}           mono />
            <Field label="DID"              value={DISCOM_INFO.did}          mono />
            <Field label="License Number"   value={DISCOM_INFO.licenseNumber} mono />
            <Field label="Jurisdiction"     value={DISCOM_INFO.jurisdiction}  mono={false} />
          </div>
          <div className="mt-4 flex items-center gap-2 p-3 rounded-lg bg-emerald-500/8 border border-emerald-500/20 text-xs text-emerald-400">
            <CheckCircle2 size={13} />
            Registered in DeDi directory · Credential issued {new Date(DISCOM_INFO.registeredAt).toLocaleDateString('en-IN')}
          </div>
        </Section>

        {/* Network / Beckn */}
        <Section title="Beckn Network Configuration" icon={Globe}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="BAP Callback URL"   value={bapUrl}   editable onChange={setBapUrl}
              hint="URL where SERC sends async responses (/on_init, /on_confirm, /on_status)" />
            <Field label="Beckn Domain"        value={domain}   editable onChange={setDomain}
              hint="IES domain identifier for routing" />
            <Field label="BAP ID"              value="infosys-discom-bap.sandbox.ies" mono />
            <Field label="BPP ID (Mock SERC)"  value="mock-serc.sandbox.ies"          mono />
            <Field label="Gateway URL"         value="https://gateway.sandbox.ies"    mono />
            <Field label="Registry URL"        value="https://registry.sandbox.ies"   mono />
          </div>
          <div className="mt-4 flex gap-2">
            <button className="btn-secondary text-xs gap-2">
              <Wifi size={13} /> Test ONIX Connection
            </button>
            <div className="flex items-center gap-1.5 text-xs text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Connected
            </div>
          </div>
        </Section>

        {/* Credentials */}
        <Section title="Verifiable Credential" icon={Key}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Credential Status"   value="Active · Expires 2027-04-10" />
            <Field label="Signature Algorithm" value="Ed25519Signature2020" mono />
            <Field label="Issuer"              value="did:ies:credential-service" mono />
            <Field label="Verification Method" value="did:ies:credential-service#key-1" mono />
          </div>
          <div className="mt-4 flex gap-3">
            <button className="btn-secondary text-xs">
              <RefreshCw size={13} /> Renew Credential
            </button>
            <button className="btn-ghost text-xs">
              <Key size={13} /> Rotate Keys
            </button>
          </div>
        </Section>

        {/* Notifications */}
        <Section title="Notifications" icon={Bell}>
          <div className="space-y-4">
            <Field label="Notification Email" value={notifyEmail} editable onChange={setNotifyEmail} type="email" />
            <div className="space-y-3">
              {[
                { label: 'Draft validation report received',      checked: true },
                { label: 'Formal filing receipt issued',          checked: true },
                { label: 'Filing publicly disclosed on DeDi',     checked: true },
                { label: 'Filing rejected by SERC',               checked: true },
                { label: 'Credential approaching expiry (30 days)', checked: false },
              ].map(({ label, checked }) => (
                <label key={label} className="flex items-center gap-3 cursor-pointer group">
                  <div className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${checked ? 'bg-blue-600 border-blue-600' : 'border-slate-600 group-hover:border-slate-400'}`}>
                    {checked && <CheckCircle2 size={10} className="text-white" />}
                  </div>
                  <span className="text-sm text-slate-300">{label}</span>
                </label>
              ))}
            </div>
          </div>
        </Section>

        {/* Save */}
        <div className="flex justify-end">
          <button onClick={handleSave} className="btn-primary">
            {saved ? <><CheckCircle2 size={15} /> Saved!</> : <><Save size={15} /> Save Settings</>}
          </button>
        </div>

      </div>
    </div>
  );
}
