const encoder = new TextEncoder();

function toHex(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  return Array.from(bytes)
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export function buildSignatureInput(timestamp: string, requestId: string, payloadJson: string): string {
  return `${timestamp}.${requestId}.${payloadJson}`;
}

export async function createHmacSha256Signature(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signatureBuffer = await crypto.subtle.sign("HMAC", key, encoder.encode(message));
  return toHex(signatureBuffer);
}

export function isTimestampInReplayWindow(timestamp: string, replayWindowMs: number, now = Date.now()): boolean {
  const parsed = Date.parse(timestamp);
  if (Number.isNaN(parsed)) {
    return false;
  }
  return Math.abs(now - parsed) <= replayWindowMs;
}
