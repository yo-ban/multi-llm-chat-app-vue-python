import chardet
from io import BytesIO
from fastapi import UploadFile, HTTPException
from typing import Dict, Any

class FileHandler:
    """Handler for processing various file types and extracting text content"""
    
    @staticmethod
    async def handle_pdf(file: UploadFile) -> Dict[str, Any]:
        """
        Extract text from PDF files
        
        Args:
            file: Uploaded PDF file
            
        Returns:
            Dictionary containing extracted text
        """
        try:
            import pypdf

            content = await file.read()
            pdf = pypdf.PdfReader(BytesIO(content))
            text = ''
            for page in pdf.pages:
                text += page.extract_text()
            return {"text": text}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing PDF: {str(e)}")

    @staticmethod
    async def handle_html(file: UploadFile) -> Dict[str, Any]:
        """
        Extract text from HTML files
        
        Args:
            file: Uploaded HTML file
            
        Returns:
            Dictionary containing extracted text
        """
        try:
            from markdownify import markdownify as md
            content = await file.read()
            detected_encoding = chardet.detect(content)['encoding'] or "utf-8"
            html_text = content.decode(detected_encoding)
            text = md(html_text)
            return {"text": text}

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing HTML: {str(e)}")

    @staticmethod
    async def handle_markdown(file: UploadFile) -> Dict[str, Any]:
        """
        Extract text from Markdown files
        
        Args:
            file: Uploaded Markdown file
            
        Returns:
            Dictionary containing extracted text
        """
        try:
            content = await file.read()
            detected_encoding = chardet.detect(content)['encoding'] or "utf-8"
            text = content.decode(detected_encoding)
            return {"text": text}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing Markdown: {str(e)}")

    @staticmethod
    async def handle_jupyter(file: UploadFile) -> Dict[str, Any]:
        """
        Extract text from Jupyter notebook files
        
        Args:
            file: Uploaded Jupyter notebook file
            
        Returns:
            Dictionary containing extracted text
        """
        try:
            from nbconvert import MarkdownExporter
            content = await file.read()
            markdown_exporter = MarkdownExporter()
            notebook, _ = markdown_exporter.from_file(BytesIO(content))
            return {"text": notebook}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing Jupyter notebook: {str(e)}")

    @staticmethod
    async def handle_generic(file: UploadFile) -> Dict[str, Any]:
        """
        Extract text from generic files using unstructured
        
        Args:
            file: Uploaded file
            
        Returns:
            Dictionary containing extracted text
        """
        try:
            from unstructured.partition.auto import partition

            content = await file.read()
            detected_encoding = chardet.detect(content)['encoding']
            elements = partition(file=BytesIO(content), encoding=detected_encoding)
            text = '\n'.join([str(el) for el in elements])
            return {"text": text}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

    async def process_file(self, file: UploadFile) -> Dict[str, Any]:
        """
        Main entry point for processing files
        
        Args:
            file: Uploaded file
            
        Returns:
            Dictionary containing extracted text
        """
        try:
            file_type = file.content_type
            
            if file_type == 'application/pdf':
                return await self.handle_pdf(file)
            elif file_type == 'text/html':
                return await self.handle_html(file)
            elif file.filename.endswith(('.md', '.markdown')) or file_type == 'text/plain':
                return await self.handle_markdown(file)
            elif file.filename.endswith('.ipynb'):
                return await self.handle_jupyter(file)
            else:
                return await self.handle_generic(file)
                
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) 