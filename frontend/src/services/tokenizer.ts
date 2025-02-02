import { Tiktoken } from 'tiktoken/lite';

import claude from '@/assets/claude.json';

export function countTokens(text: string): number {
  const tokenizer = getTokenizer();
  const encoded = tokenizer.encode(text.normalize('NFKC'), 'all');
  tokenizer.free();
  return encoded.length;
}

export function getTokenizer(): Tiktoken {
  return new Tiktoken(claude.bpe_ranks, claude.special_tokens, claude.pat_str);
}
