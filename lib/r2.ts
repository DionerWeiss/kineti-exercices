import "server-only";
import {
  DeleteObjectCommand,
  GetObjectCommand,
  HeadObjectCommand,
  PutObjectCommand,
  S3Client,
} from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import { r2Env } from "@/lib/env";

let client: S3Client | null = null;

function r2() {
  client ??= new S3Client({
    region: "auto",
    endpoint: `https://${r2Env.accountId}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId: r2Env.accessKeyId,
      secretAccessKey: r2Env.secretAccessKey,
    },
    // R2 não aceita os checksums CRC padrão do SDK em URLs assinadas.
    requestChecksumCalculation: "WHEN_REQUIRED",
    responseChecksumValidation: "WHEN_REQUIRED",
  });
  return client;
}

/** URL para o navegador enviar o arquivo direto ao R2 (PUT), válida por 15 min. */
export function presignUpload(key: string, contentType: string) {
  return getSignedUrl(
    r2(),
    new PutObjectCommand({ Bucket: r2Env.bucket, Key: key, ContentType: contentType }),
    { expiresIn: 15 * 60 },
  );
}

/** URL para assistir ao vídeo: domínio público se houver, senão URL assinada de 1 h. */
export async function videoUrl(key: string) {
  const publicUrl = r2Env.publicUrl;
  if (publicUrl) {
    return `${publicUrl}/${key.split("/").map(encodeURIComponent).join("/")}`;
  }
  return getSignedUrl(r2(), new GetObjectCommand({ Bucket: r2Env.bucket, Key: key }), {
    expiresIn: 60 * 60,
  });
}

/** Metadados do objeto, ou null se ele não existir. */
export async function headObject(key: string) {
  try {
    const head = await r2().send(new HeadObjectCommand({ Bucket: r2Env.bucket, Key: key }));
    return { size: head.ContentLength ?? 0, contentType: head.ContentType ?? "" };
  } catch (error) {
    const status = (error as { $metadata?: { httpStatusCode?: number } }).$metadata?.httpStatusCode;
    if (status === 404) return null;
    throw error;
  }
}

export async function deleteObject(key: string) {
  await r2().send(new DeleteObjectCommand({ Bucket: r2Env.bucket, Key: key }));
}
