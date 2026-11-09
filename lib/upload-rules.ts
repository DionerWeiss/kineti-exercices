// Regras de upload compartilhadas entre o formulário (cliente) e as actions (servidor).

export const MAX_UPLOAD_BYTES = 1024 * 1024 * 1024; // 1 GB

export const VIDEO_EXTENSIONS: Record<string, string> = {
  "video/mp4": "mp4",
  "video/webm": "webm",
  "video/quicktime": "mov",
};

export const ACCEPTED_TYPES = Object.keys(VIDEO_EXTENSIONS);
