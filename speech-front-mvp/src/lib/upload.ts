/**
 * 上传录音文件到后端
 * POST /api/upload_audio
 */

export interface UploadResponse {
  upload_id: string;
  saved_path: string;
}

export async function uploadAudio(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch("/api/upload_audio", {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const errorText = await res.text().catch(() => "未知错误");
    throw new Error(`上传失败：${res.status} ${res.statusText} - ${errorText}`);
  }

  const data = await res.json();
  return data as UploadResponse;
}
