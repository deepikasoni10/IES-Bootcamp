import { useFilingStore } from '../../store/filingStore';
import { X, Upload, GitBranch, FileJson, Hash, Send, Award } from 'lucide-react';
import Step1Upload from './steps/Step1Upload';
import Step2Mapping from './steps/Step2Mapping';
import Step3Payload from './steps/Step3Payload';
import Step4HashValidate from './steps/Step4HashValidate';
import Step5DraftSubmit from './steps/Step5DraftSubmit';
import Step6FormalSubmit from './steps/Step6FormalSubmit';

const STEPS = [
  { label: 'Upload Data',    sub: 'CSV / Excel',      Icon: Upload },
  { label: 'Schema Map',    sub: 'Column mapping',    Icon: GitBranch },
  { label: 'Payload',       sub: 'DatasetPayload',    Icon: FileJson },
  { label: 'Hash & Validate',sub: 'SHA-256 + Schema', Icon: Hash },
  { label: 'Draft Submit',  sub: '/init → SERC',      Icon: Send },
  { label: 'Formal Submit', sub: '/confirm + VC',     Icon: Award },
];

const STEP_COMPONENTS = [Step1Upload, Step2Mapping, Step3Payload, Step4HashValidate, Step5DraftSubmit, Step6FormalSubmit];

export default function FilingWizard() {
  const { wizard, closeWizard } = useFilingStore();
  const { currentStep } = wizard;
  const StepComponent = STEP_COMPONENTS[currentStep];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-5xl bg-surface-800 border border-slate-700/50 rounded-2xl shadow-2xl flex flex-col max-h-[92vh] overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 flex-shrink-0">
          <div>
            <h2 className="text-base font-bold text-slate-100">New ARR Filing</h2>
            <p className="text-xs text-slate-500 mt-0.5">Maharashtra Electricity Regulatory Commission</p>
          </div>
          <button onClick={closeWizard} className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-700 transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* Step Progress */}
        <div className="px-6 py-4 border-b border-slate-800 flex-shrink-0">
          <div className="flex items-center gap-1">
            {STEPS.map(({ label, sub, Icon }, i) => (
              <div key={i} className="flex items-center flex-1 min-w-0">
                <div className="flex flex-col items-center gap-1 flex-shrink-0">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300 ${
                    i < currentStep  ? 'bg-emerald-600 text-white' :
                    i === currentStep? 'bg-blue-600 text-white ring-4 ring-blue-500/25' :
                                       'bg-surface-600 text-slate-500'
                  }`}>
                    {i < currentStep ? (
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    ) : (
                      <Icon size={14} />
                    )}
                  </div>
                  <div className={`text-center hidden sm:block ${i === currentStep ? 'text-blue-400' : i < currentStep ? 'text-emerald-400' : 'text-slate-600'}`}>
                    <div className="text-[10px] font-semibold leading-tight truncate max-w-[64px]">{label}</div>
                    <div className="text-[9px] leading-tight truncate max-w-[64px] opacity-70">{sub}</div>
                  </div>
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`h-px flex-1 mx-1 transition-all duration-500 ${i < currentStep ? 'bg-emerald-600' : 'bg-slate-700'}`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="flex-1 overflow-auto p-6">
          <div className="animate-slide-up">
            <StepComponent />
          </div>
        </div>

      </div>
    </div>
  );
}
