'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Camera, CameraOff, RefreshCcw, SwitchCamera, X } from 'lucide-react';

interface AdvancedCameraCaptureProps {
  open: boolean;
  onClose: () => void;
  onCapture: (file: File) => Promise<void> | void;
}

type FacingMode = 'user' | 'environment';

export function AdvancedCameraCapture({ open, onClose, onCapture }: AdvancedCameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [facingMode, setFacingMode] = useState<FacingMode>('environment');
  const [error, setError] = useState<string | null>(null);
  const [capturedDataUrl, setCapturedDataUrl] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  const canSwitchFacingMode = useMemo(() => true, []);

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const startStream = useCallback(async () => {
    try {
      setError(null);
      stopStream();

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode,
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
    } catch (streamError) {
      const message =
        streamError instanceof Error
          ? streamError.message
          : 'Kamera konnte nicht gestartet werden.';
      setError(message);
    }
  }, [facingMode, stopStream]);

  useEffect(() => {
    if (!open) {
      stopStream();
      setCapturedDataUrl(null);
      setError(null);
      return;
    }
    void startStream();

    return () => {
      stopStream();
    };
  }, [open, startStream, stopStream]);

  const handleTakePhoto = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    const width = video.videoWidth;
    const height = video.videoHeight;
    if (!width || !height) return;

    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d');
    if (!context) return;

    context.drawImage(video, 0, 0, width, height);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    setCapturedDataUrl(dataUrl);
    stopStream();
  };

  const handleRetake = async () => {
    setCapturedDataUrl(null);
    await startStream();
  };

  const handleConfirm = async () => {
    const canvas = canvasRef.current;
    if (!canvas || !capturedDataUrl) return;

    setIsBusy(true);
    canvas.toBlob(
      async (blob) => {
        if (!blob) {
          setError('Foto konnte nicht verarbeitet werden.');
          setIsBusy(false);
          return;
        }

        const file = new File([blob], `camera-${Date.now()}.jpg`, { type: 'image/jpeg' });
        try {
          await onCapture(file);
          onClose();
        } catch (captureError) {
          setError(captureError instanceof Error ? captureError.message : 'Upload fehlgeschlagen');
        } finally {
          setIsBusy(false);
        }
      },
      'image/jpeg',
      0.92
    );
  };

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-[12000] bg-black/80 flex items-center justify-center p-4">
      <div className="w-full max-w-3xl rounded-xl border border-slate-700 bg-slate-900 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-100">Foto machen</h2>
          <button onClick={onClose} type="button" className="p-1.5 text-slate-300 hover:text-white">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          <div className="aspect-video w-full rounded-lg border border-slate-700 bg-slate-950 overflow-hidden flex items-center justify-center">
            {capturedDataUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={capturedDataUrl} alt="Captured" className="w-full h-full object-contain" />
            ) : (
              <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
            )}
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <div className="flex flex-wrap gap-2 justify-end">
            {capturedDataUrl ? (
              <>
                <button
                  type="button"
                  onClick={() => void handleRetake()}
                  className="px-3 py-2 rounded-lg bg-slate-800 text-slate-100 hover:bg-slate-700 inline-flex items-center gap-2"
                >
                  <RefreshCcw className="w-4 h-4" />
                  Neu aufnehmen
                </button>
                <button
                  type="button"
                  disabled={isBusy}
                  onClick={() => void handleConfirm()}
                  className="px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50"
                >
                  {isBusy ? 'Speichere...' : 'Foto verwenden'}
                </button>
              </>
            ) : (
              <>
                {canSwitchFacingMode && (
                  <button
                    type="button"
                    onClick={() => setFacingMode((prev) => (prev === 'environment' ? 'user' : 'environment'))}
                    className="px-3 py-2 rounded-lg bg-slate-800 text-slate-100 hover:bg-slate-700 inline-flex items-center gap-2"
                  >
                    <SwitchCamera className="w-4 h-4" />
                    Kamera wechseln
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleTakePhoto}
                  className="px-3 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-500 inline-flex items-center gap-2"
                >
                  <Camera className="w-4 h-4" />
                  Aufnehmen
                </button>
              </>
            )}

            <button
              type="button"
              onClick={onClose}
              className="px-3 py-2 rounded-lg bg-slate-800 text-slate-100 hover:bg-slate-700 inline-flex items-center gap-2"
            >
              <CameraOff className="w-4 h-4" />
              Schliessen
            </button>
          </div>
        </div>
      </div>
      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
