import { encode } from 'gpt-tokenizer/model/gpt-4o';

export function generateSystemMessageWithFiles(systemMessage: string, files?: { [key: string]: string }): string {
  if (files) {
    const fileDocuments = Object.entries(files).map(([fileName, fileContent]) => `
<file>
Filename: ${fileName}
Content:
${fileContent}
</file>
    `).join('');

    return `
${systemMessage}

<documents>
${fileDocuments}
</documents>
    `;
  }

  return systemMessage;
}


/**
 * Count tokens in the given text using Claude's tokenizer
 * @param text Text to count tokens for
 * @returns Number of tokens in the text
 */
export function countTokens(text: string): number {
  // Normalize text to NFKC form for consistent token counting
  try {
    const normalizedText = text.normalize('NFKC');
    return encode(normalizedText, {
      allowedSpecial: 'all'
    }).length;
  } catch (error) {
    console.error('Error counting tokens:', error);
    return 0;
  }
}
