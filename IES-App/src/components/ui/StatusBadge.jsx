import { CheckCircle2, Clock, AlertTriangle, XCircle, Radio, Eye } from 'lucide-react';

const STATUS_MAP = {
  disclosed:          { label: 'Disclosed',          cls: 'badge-green',  Icon: Eye },
  accepted:           { label: 'Accepted',           cls: 'badge-green',  Icon: CheckCircle2 },
  formally_submitted: { label: 'Under Review',       cls: 'badge-blue',   Icon: Radio },
  draft_validated:    { label: 'Draft Validated',    cls: 'badge-yellow', Icon: AlertTriangle },
  draft_submitted:    { label: 'Draft Submitted',    cls: 'badge-blue',   Icon: Clock },
  preparing:          { label: 'Preparing',          cls: 'badge-slate',  Icon: Clock },
  rejected:           { label: 'Rejected',           cls: 'badge-red',    Icon: XCircle },
};

export default function StatusBadge({ status }) {
  const { label, cls, Icon } = STATUS_MAP[status] || STATUS_MAP.preparing;
  return (
    <span className={cls}>
      <Icon size={11} />
      {label}
    </span>
  );
}
