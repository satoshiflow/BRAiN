'use client';

import { FileText, Image as ImageIcon, Loader2, Trash2, AlertTriangle } from 'lucide-react';
import type { ChatAttachment } from '@/src/hooks/useAttachmentUpload';

interface AttachmentTrayProps {
  attachments: ChatAttachment[];
  onRemove: (localId: string) => void;
}

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export function AttachmentTray({ attachments, onRemove }: AttachmentTrayProps) {
  if (attachments.length === 0) {
    return null;
  }

  return (
    <div className="border-t border-slate-800 p-3 bg-slate-900/60">
      <div className="flex flex-wrap gap-2">
        {attachments.map((attachment) => {
          const isImage = attachment.mimeType.startsWith('image/');

          return (
            <div
              key={attachment.localId}
              className="w-56 rounded-lg border border-slate-700 bg-slate-850 p-2"
            >
              <div className="flex items-start gap-2">
                <div className="w-12 h-12 shrink-0 rounded bg-slate-800 overflow-hidden flex items-center justify-center">
                  {isImage && attachment.previewUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={attachment.previewUrl} alt={attachment.filename} className="w-full h-full object-cover" />
                  ) : isImage ? (
                    <ImageIcon className="w-5 h-5 text-slate-400" />
                  ) : (
                    <FileText className="w-5 h-5 text-slate-400" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-100 truncate">{attachment.filename}</p>
                  <p className="text-[11px] text-slate-400">{formatBytes(attachment.sizeBytes)}</p>
                  <div className="mt-1 text-[11px]">
                    {attachment.status === 'uploading' && (
                      <span className="inline-flex items-center gap-1 text-blue-400">
                        <Loader2 className="w-3 h-3 animate-spin" /> Uploading
                      </span>
                    )}
                    {attachment.status === 'ready' && (
                      <span className="text-green-400">Ready</span>
                    )}
                    {attachment.status === 'error' && (
                      <span className="inline-flex items-center gap-1 text-red-400" title={attachment.error}>
                        <AlertTriangle className="w-3 h-3" /> Failed
                      </span>
                    )}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => onRemove(attachment.localId)}
                  className="p-1 text-slate-400 hover:text-red-400"
                  aria-label="Remove attachment"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>

              {attachment.status === 'error' && attachment.error && (
                <p className="mt-2 text-[11px] text-red-400 line-clamp-2">{attachment.error}</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
