# Bibliography Extraction Tool

A powerful Streamlit-based application that extracts and organizes bibliography information from various document formats including PDFs, images, Word documents, and PowerPoint presentations.

## Features

- 📄 **Multi-Format Support**: Extract bibliography data from PDF, DOCX, PPTX, and image files
- 🔍 **Smart Text Extraction**: Uses OCR for images and PyMuPDF for PDFs
- 🤖 **NLP-Powered**: Leverages spaCy for advanced text processing and entity recognition
- 📊 **Data Export**: Export extracted bibliography to multiple formats
- 🎨 **User-Friendly Interface**: Clean and intuitive Streamlit UI
- ⚡ **Fast Processing**: Optimized extraction algorithms for quick results

## Tech Stack

- **Frontend**: Streamlit
- **Backend**: Python 3.8+
- **NLP**: spaCy
- **Document Processing**: PyMuPDF, python-docx, python-pptx, Pillow
- **Data Analysis**: Pandas (which pulls in NumPy and setuptools automatically)
- **OCR**: Tesseract

## Installation

### Prerequisites
- Python 3.8 or higher
- Tesseract OCR (for image processing)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Bibliography_extraction.git
   cd Bibliography_extraction
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   # On Windows:
   .\.venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

4. **Install Tesseract** (Required for OCR)
   - **Windows**: Download installer from [tesseract-ocr/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
   - **macOS**: `brew install tesseract`
   - **Linux**: `sudo apt-get install tesseract-ocr`

## Usage

### Running Locally

```bash
streamlit run app.py
```

The application will open in your default browser at `http://localhost:8501`

### Using the Application

1. Upload your document (PDF, image, DOCX, or PPTX)
2. The app will automatically extract bibliography information
3. Review the extracted data
4. Export results in your preferred format

## Project Structure

```
Bibliography_extraction/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── requirements.in        # Pip-compile source file
├── packages.txt          # System packages for deployment
├── .streamlit/
│   └── config.toml       # Streamlit configuration
├── assets/               # Static assets and images
└── README.md            # This file
```

## Deployment

### Deploy to Streamlit Cloud (recommended)

1. **Push to GitHub** (see below)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Select your repository and `app.py`
5. Click **Deploy**

> The previous Vercel and Heroku instructions have been removed: this project is now optimized for Streamlit Cloud, which handles Python apps and system packages more gracefully.

## GitHub Setup

1. **Initialize git repository** (if not already done)
   ```bash
   git init
   ```

2. **Add all files**
   ```bash
   git add .
   ```

3. **Create first commit**
   ```bash
   git commit -m "Initial commit: Bibliography extraction tool"
   ```

4. **Add remote repository**
   ```bash
   git remote add origin https://github.com/yourusername/Bibliography_extraction.git
   ```

5. **Push to GitHub**
   ```bash
   git branch -M main
   git push -u origin main
   ```

## Configuration

### Streamlit Settings
Edit `.streamlit/config.toml` to customize:
- Page layout
- Theme (light/dark)
- Maximum upload file size
- Session state timeout

### Environment Variables
Create a `.env` file for sensitive configurations:
```
TESSERACT_PATH=/path/to/tesseract
OPENAI_API_KEY=your_key_here  # If using OpenAI
```

## API Reference

### extract_bibliography_info()
Extracts bibliography metadata from text using regex patterns.

**Parameters:**
- `text` (str): Input text to extract from

**Returns:**
- `dict`: Contains 'title', 'author', 'year' fields

### simple_summarize()
Generates a simple summary of the text.

**Parameters:**
- `text` (str): Text to summarize

**Returns:**
- `str`: Summarized text

## Troubleshooting

### Tesseract Not Found
Ensure Tesseract is installed and the path is correctly configured in your environment or `.env` file.

### Memory Issues with Large Documents
Process documents in smaller chunks or increase system memory allocation.

### spaCy Model Download
If the `en_core_web_sm` model fails to download:
```bash
python -m spacy download en_core_web_sm
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, email your-email@example.com or open an issue on GitHub.

## Acknowledgments

- [Streamlit](https://streamlit.io) - Web app framework
- [spaCy](https://spacy.io) - NLP library
- [PyMuPDF](https://pymupdf.readthedocs.io) - PDF processing
- [python-pptx](https://python-pptx.readthedocs.io) - PowerPoint handling
- [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) - OCR engine

---

**Last Updated**: February 2026

Made with ❤️ for document processing enthusiasts
