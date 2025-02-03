import { encode } from 'gpt-tokenizer/model/gpt-4o';

/**
 * Count tokens in the given text using Claude's tokenizer
 * @param text Text to count tokens for
 * @returns Number of tokens in the text
 */
export function countTokens(text: string): number {
  // Normalize text to NFKC form for consistent token counting
  const normalizedText = text.normalize('NFKC');
  return encode(normalizedText).length;
}

// Note: getTokenizer function is removed as it's no longer needed with gpt-tokenizer
