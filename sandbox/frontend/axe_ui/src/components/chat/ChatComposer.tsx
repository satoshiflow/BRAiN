'use client';

import { useRef } from 'react';
import { Camera, ImagePlus, Send } from 'lucide-react';

interface ChatComposerProps {
  value: string;
  loading: boolean;
  uploading: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
  onFilesSelected: (files: FileList) => Promise<void> | void;
  onOpenCamera: () => void;
}

export function ChatComposer({
  value,
  loading,
  uploading,
  onChange,
  onSend,
  onFilesSelected,
  onOpenCamera,
}: ChatComposerProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  return (
    <div className="border-t border-slate-800 p-4 bg-slate-950">
      <div className="flex flex-wrap gap-2 mb-3">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading || uploading}
          className="px-3 py-2 text-sm bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-100 rounded-lg border border-slate-700 inline-flex items-center gap-2"
        >
          <ImagePlus className="w-4 h-4" />
          Bild laden
        </button>
        <button
          type="button"
          onClick={onOpenCamera}
          disabled={loading || uploading}
          className="px-3 py-2 text-sm bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-100 rounded-lg border border-slate-700 inline-flex items-center gap-2"
        >
          <Camera className="w-4 h-4" />
          Foto machen
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        multiple
        accept="image/jpeg,image/png,image/webp,application/pdf,text/plain"
        onChange={(event) => {
          if (event.target.files && event.target.files.length > 0) {
            void onFilesSelected(event.target.files);
            event.target.value = '';
          }
        }}
      />

      <div className="flex items-end gap-3">
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          disabled={loading}
          rows={2}
          className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 resize-none"
        />
        <button
          type="button"
          onClick={onSend}
          disabled={loading || uploading || !value.trim()}
          className="px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:cursor-not-allowed text-white rounded-lg transition-colors inline-flex items-center gap-2"
        >
          <Send className="w-4 h-4" />
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
      {uploading && <p className="text-xs text-blue-300 mt-2">Datei wird hochgeladen...</p>}
    </div>
  );
}
