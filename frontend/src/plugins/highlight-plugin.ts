// src/plugins/highlight-plugin.ts
import hljs from 'highlight.js/lib/core';

// 言語のインポート
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import css from 'highlight.js/lib/languages/css';
import xml from 'highlight.js/lib/languages/xml';
import php from 'highlight.js/lib/languages/php';
import python from 'highlight.js/lib/languages/python';
import ruby from 'highlight.js/lib/languages/ruby';
import java from 'highlight.js/lib/languages/java';
import cpp from 'highlight.js/lib/languages/cpp';
import csharp from 'highlight.js/lib/languages/csharp';
import bash from 'highlight.js/lib/languages/bash';
import sql from 'highlight.js/lib/languages/sql';
import json from 'highlight.js/lib/languages/json';
import yaml from 'highlight.js/lib/languages/yaml';
import markdown from 'highlight.js/lib/languages/markdown';

// 言語の登録
hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('css', css);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('php', php);
hljs.registerLanguage('python', python);
hljs.registerLanguage('ruby', ruby);
hljs.registerLanguage('java', java);
hljs.registerLanguage('cpp', cpp);
hljs.registerLanguage('csharp', csharp);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('sql', sql);
hljs.registerLanguage('json', json);
hljs.registerLanguage('yaml', yaml);
hljs.registerLanguage('markdown', markdown);

// マークダウンでのコードブロックハイライト用ヘルパー関数
export function highlightCode(str: string, lang: string): string {
  if (lang && hljs.getLanguage(lang)) {
    try {
      const code = hljs.highlight(str, { language: lang }).value;
      return `<pre class="hljs"><div class="code-header"><span class="language">${lang}</span><button class="copy-button">Copy</button></div><code>${code}</code></pre>`;
    } catch (error) {
      console.error('Error highlighting code:', error);
    }
  }
  return `<pre class="hljs"><div class="code-header"><span class="language">Code</span><button class="copy-button">Copy</button></div><code>${str}</code></pre>`;
}

// ブラウザでのコードブロックハイライト用ディレクティブ
export function setupHighlightDirective(app: any) {
  app.directive('highlight', {
    mounted(el: HTMLElement) {
      const codeBlocks = el.querySelectorAll('pre code');
      codeBlocks.forEach((block) => {
        hljs.highlightElement(block as HTMLElement);
      });
    },
    updated(el: HTMLElement) {
      const codeBlocks = el.querySelectorAll('pre code');
      codeBlocks.forEach((block) => {
        hljs.highlightElement(block as HTMLElement);
      });
    }
  });
}

// コピーボタンの処理用イベントハンドラを設定
export function setupCopyButtonHandler() {
  const handleCopyButtonClick = (event: MouseEvent) => {
    const target = event.target as HTMLElement;
    if (target.classList.contains('copy-button')) {
      const codeElement = target.parentElement?.nextElementSibling;
      if (codeElement) {
        const code = codeElement.textContent || '';
        navigator.clipboard.writeText(code).then(() => {
          target.textContent = 'Copied!';
          setTimeout(() => {
            target.textContent = 'Copy';
          }, 10000);
        });
      }
    }
  };

  window.addEventListener('click', handleCopyButtonClick);
  return () => {
    window.removeEventListener('click', handleCopyButtonClick);
  };
}

// Vueプラグインとして登録
export default {
  install: (app: any) => {
    // グローバルプロパティとして登録
    app.config.globalProperties.$hljs = hljs;
    
    // ハイライトディレクティブを設定
    setupHighlightDirective(app);
    
    // コピーボタンハンドラは自動では設定せず、コンポーネントが必要に応じて呼び出す
    app.provide('setupCopyButtonHandler', setupCopyButtonHandler);
    app.provide('highlightCode', highlightCode);
  }
}; 