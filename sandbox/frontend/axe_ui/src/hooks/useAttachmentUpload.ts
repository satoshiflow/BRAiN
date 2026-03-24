'use client';

import { useCallback, useMemo, useState } from 'react';
import { uploadAttachment } from '@/lib/api';

const MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024;
const ALLOWED_MIME_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/webp',
  'application/pdf',
  'text/plain',
]);

export type UploadStatus = 'uploading' | 'ready' | 'error';

export interface ChatAttachment {
  localId: string;
  attachmentId?: string;
  filename: string;
  mimeType: string;
  sizeBytes: number;
  previewUrl?: string;
  status: UploadStatus;
  error?: string;
}

const makeLocalId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
};

const toPreviewUrl = (file: File): string | undefined => {
  if (!file.type.startsWith('image/')) {
    return undefined;
  }
  return URL.createObjectURL(file);
};

export function useAttachmentUpload() {
  const [attachments, setAttachments] = useState<ChatAttachment[]>([]);

  const removeAttachment = useCallback((localId: string) => {
    setAttachments((prev) => {
      const found = prev.find((item) => item.localId === localId);
      if (found?.previewUrl) {
        URL.revokeObjectURL(found.previewUrl);
      }
      return prev.filter((item) => item.localId !== localId);
    });
  }, []);

  const clearAttachments = useCallback(() => {
    setAttachments((prev) => {
      prev.forEach((item) => {
        if (item.previewUrl) {
          URL.revokeObjectURL(item.previewUrl);
        }
      });
      return [];
    });
  }, []);

  const addFiles = useCallback(async (fileList: File[] | FileList) => {
    const files = Array.from(fileList);

    for (const file of files) {
      const localId = makeLocalId();
      const previewUrl = toPreviewUrl(file);

      if (!ALLOWED_MIME_TYPES.has(file.type)) {
        setAttachments((prev) => [
          ...prev,
          {
            localId,
            filename: file.name,
            mimeType: file.type || 'application/octet-stream',
            sizeBytes: file.size,
            previewUrl,
            status: 'error',
            error: 'Dateityp nicht erlaubt (nur Bild/PDF/TXT).',
          },
        ]);
        continue;
      }

      if (file.size > MAX_ATTACHMENT_SIZE_BYTES) {
        setAttachments((prev) => [
          ...prev,
          {
            localId,
            filename: file.name,
            mimeType: file.type,
            sizeBytes: file.size,
            previewUrl,
            status: 'error',
            error: 'Datei ist zu gross (max. 10MB).',
          },
        ]);
        continue;
      }

      setAttachments((prev) => [
        ...prev,
        {
          localId,
          filename: file.name,
          mimeType: file.type,
          sizeBytes: file.size,
          previewUrl,
          status: 'uploading',
        },
      ]);

      try {
        const response = await uploadAttachment(file);
        setAttachments((prev) =>
          prev.map((item) =>
            item.localId === localId
              ? {
                  ...item,
                  attachmentId: response.attachment_id,
                  status: 'ready',
                  mimeType: response.mime_type,
                  sizeBytes: response.size_bytes,
                  filename: response.filename,
                }
              : item
          )
        );
      } catch (error) {
        const message = error instanceof Error ? error.message : 'Upload fehlgeschlagen';
        setAttachments((prev) =>
          prev.map((item) =>
            item.localId === localId
              ? {
                  ...item,
                  status: 'error',
                  error: message,
                }
              : item
          )
        );
      }
    }
  }, []);

  const readyAttachmentIds = useMemo(
    () => attachments.filter((item) => item.status === 'ready' && item.attachmentId).map((item) => item.attachmentId as string),
    [attachments]
  );

  const isUploading = useMemo(
    () => attachments.some((item) => item.status === 'uploading'),
    [attachments]
  );

  return {
    attachments,
    addFiles,
    removeAttachment,
    clearAttachments,
    readyAttachmentIds,
    isUploading,
  };
}
