import { fileService } from '@/services/api/file-service';

/**
 * ファイルの拡張子を取得する
 * @param filename ファイル名
 * @returns 拡張子（ドットなし）
 */
export function getFileExtension(filename: string): string {
  return filename.slice((filename.lastIndexOf('.') - 1 >>> 0) + 2);
}

/**
 * ファイルサイズを人間が読みやすい形式にフォーマットする
 * @param bytes バイト数
 * @returns フォーマットされたサイズ文字列（例: "2.5 MB"）
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * ファイルが特定のMIMEタイプに一致するかチェックする
 * @param file チェックするファイル
 * @param mimeTypes 許可するMIMEタイプの配列
 * @returns 一致する場合はtrue
 */
export function isFileTypeAllowed(file: File, mimeTypes: string[]): boolean {
  return mimeTypes.includes(file.type);
}

/**
 * @deprecated このメソッドは互換性のために残されています。代わりに fileService.extractTextFromFile を使用してください。
 * ファイルからテキストを抽出する - サービス層への委譲
 * @param file 抽出するファイル
 * @returns 抽出されたテキスト
 */
export const extractTextFromFile = async (file: File): Promise<string> => {
  // サービス層に処理を委譲
  return fileService.extractTextFromFile(file);
};
