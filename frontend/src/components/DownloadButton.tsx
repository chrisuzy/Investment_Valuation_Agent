interface DownloadButtonProps {
  sessionId: string | null;
  sheetName: string;
}

export default function DownloadButton({ sessionId, sheetName }: DownloadButtonProps) {
  if (!sessionId) return null;

  const handleDownload = () => {
    window.open(`/api/valuation/${sessionId}/export/${sheetName}`, '_blank');
  };

  return (
    <button
      onClick={handleDownload}
      className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50"
      title="Download as Excel"
    >
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      Download .xlsx
    </button>
  );
}
