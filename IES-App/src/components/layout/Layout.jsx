import Sidebar from './Sidebar';
import FilingWizard from '../filing/FilingWizard';
import { useFilingStore } from '../../store/filingStore';

export default function Layout({ children }) {
  const { wizard } = useFilingStore();

  return (
    <div className="flex h-screen overflow-hidden bg-surface-900">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-auto bg-grid">
          {children}
        </div>
      </main>
      {wizard.active && <FilingWizard />}
    </div>
  );
}
