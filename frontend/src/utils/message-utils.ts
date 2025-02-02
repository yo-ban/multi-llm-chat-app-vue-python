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
