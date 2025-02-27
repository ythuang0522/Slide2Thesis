# Slide2Thesis

Slide2Thesis is a tool that automatically generates a thesis document from a PDF presentation. It uses Google's Gemini API to extract, analyze, and transform presentation content into a structured academic thesis.

## Features

- Extract text and images from PDF presentations
- Classify presentation pages into logical sections
- Generate well-structured thesis chapters
- Add relevant citations from PubMed
- Include figure references
- Generate YAML metadata for thesis formatting
- Compile the final thesis as a PDF document

## Installation

1. Clone this repository:
```bash
git clone https://github.com/ythuang0522/Slide2Thesis.git
cd Slide2Thesis
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
conda install -c conda-forge pandoc
conda install tectonic
brew install pandoc-crossref
```

3. Set up environment variables:
Create a `.env` file with your API keys:
```
GEMINI_API_KEY=your_gemini_api_key
PUBMED_EMAIL=your_email@example.com
```

## Usage

Basic usage:
```bash
python main.py path/to/your/presentation.pdf
```

For specific steps:
```bash
# Extract text only
python main.py path/to/your/presentation.pdf --extract-text

# Generate chapters only
python main.py path/to/your/presentation.pdf --generate-chapters

# Add citations only
python main.py path/to/your/presentation.pdf --add-citations

# Compile the final thesis
python main.py path/to/your/presentation.pdf --compile
```

## Project Structure

- `main.py`: Main script orchestrating the thesis generation process
- `text_extractor.py`: Extracts text from PDF presentations
- `page_classifier.py`: Categorizes pages into logical sections
- `chapter_generator.py`: Generates thesis chapters
- `citation_generator.py`: Adds relevant citations
- `figure_generator.py`: Processes and references figures
- `yaml_metadata_generator.py`: Creates YAML metadata
- `thesis_compiler.py`: Compiles the final thesis document
- `gemini_api.py`: Wrapper for Google's Gemini API

## License

MIT

## Author

Yao-Ting Huang (@ythuang0522) 